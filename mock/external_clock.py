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

import itertools
from threading import Thread
import os, sys, signal, time
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.rate import Rate

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MockExternalClock(Component):
    '''
    This is a mock of the hardware external clock and accurate timing is
    neither guaranteed nor expected.

    Sets up a falling-edge callback on a GPIO pin, whose toggle is generated
    by a thread. When supplied by a callback the method will be triggered. 

    There is also a second "slow" callback that is triggered at a lower rate,
    with a modulo value meant to trigger roughly at 1Hz.

    :param config:     The application configuration.
    :param callback:   the optional callback method. 
    :param level:      the logging level.
    '''
    def __init__(self, config, callback=None, level=Level.INFO):
        self._log = Logger('mock-ext-clock', level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        if config is None:
            raise ValueError('no configuration provided.')
        _cfg = config['kros'].get('hardware').get('external_clock')
        self._loop_thread     = None
        self._loop_enabled    = False

        # set up loop Rate
        self._loop_delay_hz   = 20 #_cfg.get('loop_delay_hz')     # main loop delay
        self._loop_delay_sec  = 1 / self._loop_delay_hz 
        self._log.info('loop delay:\t{}Hz ({:4.2f}s)'.format(self._loop_delay_hz, self._loop_delay_sec))
        self._rate            = Rate(self._loop_delay_hz, Level.ERROR)

        self.__callbacks      = []
        self.__slow_callbacks = []
        self._modulo          = 1
        self._slow_modulo     = 20 # 100: every 10 ticks 2Hz; 200: 1Hz; 
        self._counter         = itertools.count()
        self._millis          = lambda: int(round(time.time() * 1000))
        self._last_time       = self._millis()
        self._last_slow_time  = self._millis()
        self._pin = _cfg.get('pin')
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'ext-clock'

     # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Component.enable(self)
        if self.enabled:
            if not self.loop_is_running:
                self.start_loop()
        else:
            self._log.warning('unable to enable mocked external clock.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def loop_is_running(self):
        '''
        Returns true if using an external clock or if the loop thread is alive.
        '''
        return ( self._loop_enabled and self._loop_thread != None and self._loop_thread.is_alive() )

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def start_loop(self):
        '''
        Start the loop Thread.
        '''
        self._log.info('start mocked external clock loop...')
        if not self.enabled:
            raise Exception('not enabled.')
        if self.loop_is_running:
            self._log.warning('loop already running.')
        elif self._loop_thread is None:
            self._loop_enabled = True
            _is_daemon = False
            self._loop_thread = Thread(name='ext_clock_loop', target=ExternalClock._loop, args=[self, lambda: self._loop_enabled], daemon=_is_daemon)
            self._loop_thread.start()
            self._log.info('loop enabled.')
        else:
            raise Exception('cannot enable loop: thread already exists.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def stop_loop(self):
        '''
        Stop the loop.
        '''
        if self.loop_is_running:
            self._loop_enabled = False
            self._loop_thread  = None
            self._log.info('loop disabled.')
        else:
            self._log.warning('already disabled.')

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

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _loop(self, f_is_enabled):
        '''
        The motors loop, which executes while the flag argument lambda is True.
        '''
        if self.enabled:
            self._log.info('loop start.')
            try:
                while f_is_enabled():
                    # add execute any callbacks here...
                    _count = next(self._counter)
                    if _count % self._modulo == 0.0:
                        _now = self._millis()
                        for callback in self.__callbacks:
                            callback()
                        if _count % self._slow_modulo == 0.0:
                            for callback in self.__slow_callbacks:
                                callback()
                        _elapsed = _now - self._last_time
                        self._last_time = _now
                    self._rate.wait()
            except Exception as e:
                self._log.error('error in loop: {}\n{}'.format(e, traceback.format_exc()))
            finally:
                self._log.info(Fore.GREEN + 'exited motor control loop.')
        else:
            self._log.warning('external clock disabled: {:5.2f}ms elapsed.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        if self.enabled:
            self._log.info('disabling...')
            self.stop_loop() # stop loop thread
            Component.disable(self)
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        Component.close(self)
        self._log.info('closed.')

#EOF
