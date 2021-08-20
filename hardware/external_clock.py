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
        self.__callbacks   = []
        self._modulo       = 10
        self._counter      = itertools.count()
        self._millis       = lambda: int(round(time.time() * 1000))
        self._start_time   = self._millis()
        self._last_tick    = 0
        _pin = _cfg.get('pin')
        self._log.info('🍏 establishing callback on pin {:d}.'.format(_pin))
        self._pi.set_mode(gpio=_pin, mode=pigpio.INPUT) # GPIO 12 as input
#       self._int_callback = self._pi.callback(_pin, pigpio.EITHER_EDGE, self.callback_method if callback is None else callback)
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

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   @property
#   def modulo(self):
#       return self._modulo

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _callback_method(self, gpio, level, tick):
        if self.enabled:
            _count = next(self._counter)
            if _count % self._modulo == 0.0:
                _now = self._millis()
                for callback in self.__callbacks:
                    callback()
#                   callback(gpio, level, tick)
                _elapsed = _now - self._start_time
                self._start_time = _now
                _ticks = tick - self._last_tick
                self._last_tick = tick
#               print(Fore.YELLOW + 'callback; gpio: {}; level: {}; {} ticks; {:6.3f}ms elapsed.'.format(gpio, level, _ticks, _elapsed) + Style.RESET_ALL)
        else:
            print(Fore.BLUE + Style.DIM + 'callback: {:6.3f}ms elapsed; drifting off into the aether...' + Style.RESET_ALL)

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
