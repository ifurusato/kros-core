#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-07-07
#

from threading import Thread
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.rate import Rate

# ...............................................................
class Ticker(Component):
    '''
    A simple threaded clock that executes callbacks every loop.
    One or more subscribers can be added to the callback list.

    :param loop_freq_hz:   the loop frequency in Hertz
    :param level:          the optional log level
    '''
    def __init__(self, config, level=Level.INFO):
        self._log = Logger("clock", level)
        Component.__init__(self, self._log, suppressed=False, enabled=False)
        if config is None:
            raise ValueError('no configuration provided.')
        self._config = config
        cfg = self._config['kros'].get('ticker')
        self._loop_freq_hz = cfg.get('loop_freq_hz')
        self._rate         = Rate(self._loop_freq_hz)
        self._log.info('tick frequency: {:d}Hz'.format(self._loop_freq_hz))
        self._callbacks    = []
        self._thread       = None
        self._log.info('ticker ready.')

    # ..........................................................................
    def add_callback(self, callback):
        self._callbacks.append(callback)

    # ..........................................................................
    def name(self):
        return 'ticker'

    # ..........................................................................
    @property
    def freq_hz(self):
        return self._loop_freq_hz

    # ..........................................................................
    def _loop(self, f_is_enabled):
        '''
        The clock loop, which executes while the f_is_enabled flag is True.
        '''
        while f_is_enabled():
            for callback in self._callbacks:
                self._log.debug('executing callback...')
                callback()
            self._rate.wait()
        self._log.info('exited clock loop.')

    # ..........................................................................
    def enable(self):
        if not self.closed:
            if self.enabled:
                self._log.warning('clock already enabled.')
            else:
                # if we haven't started the thread yet, do so now...
                if self._thread is None:
                    Component.enable(self)
                    self._thread = Thread(name='clock', target=Ticker._loop, args=[self, lambda: self.enabled], daemon=True)
                    self._thread.start()
                    self._log.info('clock enabled.')
                else:
                    self._log.warning('cannot enable clock: thread already exists.')
        else:
            self._log.warning('cannot enable clock: already closed.')

    # ..........................................................................
    def disable(self):
        if self.enabled:
            Component.disable(self)
            self._thread = None
            self._log.info('clock disabled.')
        else:
            self._log.warning('already disabled.')

#EOF
