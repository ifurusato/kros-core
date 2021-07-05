#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-06-26
#

from abc import ABC, abstractmethod
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event
from core.subscriber import Subscriber
from behave.behaviour import Behaviour

# ...............................................................
class Idle(Behaviour):
    '''
    Implements a idle behaviour.

    :param name:            the name of this behaviour
    :param config:          the application configuration
    :param message_bus:     the asynchronous message bus
    :param message_factory: the factory for messages
    :param motors:          the motor controller
    :param level:           the optional log level
    '''
    def __init__(self, config, message_bus, message_factory, motors, level=Level.INFO):
        Behaviour.__init__(self, 'idle', config, message_bus, message_factory, self._idle_callback, level)
        cfg = self._config['kros'].get('idle')
        self._idle_threshold_sec = cfg.get('idle_threshold_sec') # int value
        self._log.info('idle threshold: {:d} sec.'.format(self._idle_threshold_sec))
        self._motors = motors
        self.add_event(Event.IDLE)
        self._log.info('ready.')

    # ..........................................................................
    @property
    def event(self):
        return Event.IDLE

    # ..........................................................................
    def _idle_callback(self):
        self._log.info('🌜 idle callback.')

#   # ..........................................................................
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        super().start()

    # ..........................................................................
    @property
    def name(self):
        return 'idle'

    # ..........................................................................
    def execute(self):
        '''
        The method called upon each loop iteration. This does nothing in this
        abstract class and is meant to be extended by subclasses.
        '''
        _timestamp = self._message_bus.last_message_timestamp
        if _timestamp is None:
            self._log.info('🌜 idle loop execute; no previous messages.')
        else:
            _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
            if ( _elapsed_ms / 1000.0 ) > self._idle_threshold_sec:
                self._log.info('🍒 idle loop execute; {}'.format(Subscriber.get_formatted_time('message age:', _elapsed_ms)) 
                        + Fore.YELLOW + ' type: {}'.format(type(_elapsed_ms)))
            else:
                self._log.info('🌜 idle loop execute; {}'.format(Subscriber.get_formatted_time('message age:', _elapsed_ms)) 
                        + Fore.YELLOW + ' type: {}'.format(type(_elapsed_ms)))

#EOF
