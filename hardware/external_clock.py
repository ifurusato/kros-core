#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# author:   Murray Altheim
# created:  2021-08-19
# modified: 2021-08-19
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#

import pigpio
import itertools
import os, sys, signal, time
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ExternalClock(Component):
    '''
    Sets up a falling-edge callback on a GPIO pin, whose toggle is generated
    by an external source. When supplied by a callback the method will be 
    triggered. 

    There is also a second "slow" callback that is triggered at a lower rate,
    with a modulo value meant to trigger roughly at 1Hz.

    Make sure to call close() when finished to free up the Pi resources.

    :param config:     The application configuration.
    :param callback:   the optional callback method. 
    :param level:      the logging level.
    '''
    def __init__(self, config, callback=None, level=Level.INFO):
        self._log = Logger('ext-clock', level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        self._pi = pigpio.pi()
        if not self._pi.connected:
            raise Exception('unable to establish connection to Pi.')
        if config is None:
            raise ValueError('no configuration provided.')
        _cfg = config['kros'].get('hardware').get('external_clock')
        self.__callbacks      = []
        self.__slow_callbacks = []
        self._modulo          = 10
        self._slow_modulo     = 200 # 100: every 10 ticks 2Hz; 200: 1Hz; 
        self._counter         = itertools.count()
        self._millis          = lambda: int(round(time.time() * 1000))
        self._last_time      = self._millis()
        self._last_slow_time = self._millis()
        _pin = _cfg.get('pin')
        self._log.info('establishing callback on pin {:d}.'.format(_pin))
        self._pi.set_mode(gpio=_pin, mode=pigpio.INPUT) # GPIO 12 as input
        self._int_callback = self._pi.callback(_pin, pigpio.EITHER_EDGE, self._callback_method)
        if callback:
            self.add_callback(callback)
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'ext-clock'

     # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_callback(self, callback):
        '''     
        Adds a callback to those triggered by clock ticks.
        ''' 
        self.__callbacks.append(callback)

     # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_slow_callback(self, callback):
        '''     
        Adds a 'slow' callback to those triggered by clock ticks. This is
        triggered at a slower (modulo) rate than the normal callback.
        ''' 
        self.__slow_callbacks.append(callback)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _callback_method(self, gpio, level, tick):
        if self.enabled:
            _count = next(self._counter)
            if _count % self._modulo == 0.0:
                _now = self._millis()
                for callback in self.__callbacks:
                    callback()
                if _count % self._slow_modulo == 0.0:
                    for callback in self.__slow_callbacks:
                        callback()
                    _slow_elapsed = _now - self._last_slow_time
                    self._last_slow_time = _now
#                   self._log.info(Fore.MAGENTA + 'slow tick: {:6.3f}s elapsed.'.format(_slow_elapsed / 1000.0))
                _elapsed = _now - self._last_time
                self._last_time = _now
        else:
            self._log.warning('external clock disabled: {:6.3f}ms elapsed.')
            pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        try:
            if self._int_callback:
                self._int_callback.cancel()
            if self._pi:
                self._pi.stop()
        except Exception as e:
            self._log.error('error closing pigpio: {}'.format(e))
        Component.close(self)
        self._log.info('closed.')

#EOF