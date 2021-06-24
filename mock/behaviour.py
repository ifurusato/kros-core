#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2020-11-06
#
# A simple thread-based loop that calls a callback on a regular basis. The loop
# frequency and callback function are passed as constructor arguments.
#

from threading import Thread
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.fsm import FiniteStateMachine
from core.rate import Rate

# ...............................................................
class Behaviour(FiniteStateMachine):
    __NAME = 'roam'
    '''
    A simple threaded loop that executes a callback every loop.
    One or more subscribers can be added to the callback list.

    :param name:           the name of this behaviour
    :param loop_freq_hz:   the loop frequency in Hertz
    :param callback:       the optional callback function (can be added later)
    :param level:          the optional log level
    '''
    def __init__(self, name, loop_freq_hz, callback, level=Level.INFO):
        super().__init__(name)
        self._name = name
        self._log = Logger('behave-{}'.format(name), level)
        self._loop_freq_hz = loop_freq_hz
        self._rate         = Rate(self._loop_freq_hz)
        self._log.info('tick frequency: {:d}Hz'.format(self._loop_freq_hz))
        self._callbacks    = []
        self._thread       = None
        self._suppressed   = False
        self._enabled      = False
        self._closed       = False
        if callback:
            self.add_callback(callback)
        self._log.info('ready.')

    # ..........................................................................
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        super().start()

    # ..........................................................................
    def add_callback(self, callback):
        self._callbacks.append(callback)

    # ..........................................................................
    @property
    def name(self):
        return self._name

    # ..........................................................................
    @property
    def freq_hz(self):
        return self._loop_freq_hz

    # ..........................................................................
    def _loop(self, f_is_enabled):
        '''
        The behaviour loop, which executes while the f_is_enabled flag is True.
        '''
        while f_is_enabled():
            for callback in self._callbacks:
                self._log.debug('executing callback...')
                callback()
            self._rate.wait()
        self._log.info('exited loop.')

    # ..........................................................................
    @property
    def suppressed(self):
        '''
        Return True if the publisher is suppressed.
        '''
        return self._suppressed

    def suppress(self, mode):
        '''
        Initially the suppress flag is set False, but can be enabled
        or disabled as necessary without halting the thread.
        '''
        self._suppressed = mode
        if self.suppressed:
            self._log.info('publishing suppressed.')
        else:
            self._log.info('publishing unsuppressed.')

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        '''
        The necessary state machine call to enable the publisher.
        '''
        super().enable()
        self._log.info('enabling loop...')
        if not self._closed:
            if self._enabled:
                self._log.warning('already enabled.')
            else:
                # if we haven't started the thread yet, do so now...
                if self._thread is None:
                    self._enabled = True
                    self._thread = Thread(name=self.name + '_loop', target=Behaviour._loop, args=[self, lambda: self.enabled], daemon=True)
                    self._thread.start()
                    self._log.info('loop enabled.')
                else:
                    self._log.warning('cannot enable loop: thread already exists.')
        else:
            self._log.warning('cannot enable loop: already closed.')

    # ..........................................................................
    def disable(self):
        '''
        The state machine call to disable the publisher.
        '''
        if self._enabled:
            super().disable()
            self._enabled = False
            self._thread = None
            self._log.info('loop disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def close(self):
        if not self._closed:
            if self._enabled:
                self.disable()
            super().close()
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.warning('already closed.')

#EOF
