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
from abc import ABC, abstractmethod
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.fsm import FiniteStateMachine
from core.rate import Rate

# ...............................................................
class Behaviour(ABC, Component, FiniteStateMachine):
    '''
    An abstract class providing the basis for a looped behaviour
    that executes a callback every loop.

    :param name:           the name of this behaviour
    :param loop_freq_hz:   the loop frequency in Hertz
    :param callback:       the optional callback function (can be added later)
    :param level:          the optional log level
    '''
    def __init__(self, name, loop_freq_hz, callback, level=Level.INFO):
        self._log = Logger('beh:{}'.format(name), level)
        Component.__init__(self, self._log)
        FiniteStateMachine.__init__(self, self._log, name)
        self._name         = name
        self._loop_freq_hz = loop_freq_hz
        self._rate         = Rate(self._loop_freq_hz)
        if isinstance(self._rate, int):
            self._log.info('loop frequency: {:d}Hz'.format(self._loop_freq_hz))
        else:
            self._log.info('loop frequency: {:5.2f}Hz'.format(self._loop_freq_hz))
        self._callbacks    = []
        self._thread       = None
        self._suppressed   = False
        if callback:
            self.add_callback(callback)
        self._log.info('ready.')

    # ..........................................................................
    @abstractmethod
    def start(self):
        '''
        The necessary state machine call to start the behaviour, which performs
        any initialisations of active sub-components, etc.
        Whereas Subscribers are enabled upon starting, Behaviours are not.
        '''
        super().start()
        #self.enable()

    # ..........................................................................
    def add_callback(self, callback):
        self._callbacks.append(callback)

    # ..........................................................................
    @abstractmethod
    def event(self):
        '''
        Should be implemented as a @property.
        '''
        raise Exception('required method not implemented.')

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
        The behaviour loop, which loops while the f_is_enabled flag is True.
        calling the execute() and _callback methods while the behaviour is
        not suppressed. 
        '''
        while f_is_enabled():
            for _callback in self._callbacks:
                if not self.suppressed:
                    self._log.info('executing loop method...')
                    self.execute()
                    self._log.info('executing callback...')
                    _callback()
                else:
                    self._log.info('{} behaviour suppressed.'.format(self.name))
            self._rate.wait()
        self._log.info('exited loop.')

    # ..........................................................................
    @abstractmethod
    def execute(self):
        '''
        The method called upon each loop iteration. This does nothing in this
        abstract class and is meant to be extended by subclasses.
        '''
        self._log.info('loop execute.')

    # ..........................................................................
    @property
    def suppressed(self):
        '''
        Return True if the behaviour is suppressed.
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
    def enable(self):
        '''
        The necessary state machine call to enable the behaviour.
        '''
        self._log.info('enabling loop...')
        if not self.closed:
            if not self.enabled:
                # if we haven't started the thread yet, do so now...
                if self._thread is None:
                    super().enable()
                    self._thread = Thread(name=self.name + '_loop', target=Behaviour._loop, args=[self, lambda: self.enabled], daemon=True)
                    self._thread.start()
                    self._log.info('loop enabled.')
                else:
                    self._log.warning('cannot enable loop: thread already exists.')

    # ..........................................................................
    def disable(self):
        '''
        The state machine call to disable the behaviour.
        '''
        if self.enabled:
            super().disable()
            self._thread = None

#EOF
