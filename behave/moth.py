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
class Moth(Behaviour):
    '''
    Implements a moth or anti-moth behaviour.

    :param name:            the name of this behaviour
    :param config:          the application configuration
    :param message_bus:     the asynchronous message bus
    :param message_factory: the factory for messages
    :param motors:          the motor controller
    :param level:           the optional log level
    '''
    def __init__(self, config, message_bus, message_factory, motors, level=Level.INFO):
        Behaviour.__init__(self, 'moth', config, message_bus, message_factory, self._moth_callback, level)
        cfg = self._config['kros'].get('moth')
        self._anti_moth = cfg.get('anti_moth')
        self._log.info('anti-moth: {}'.format(self._anti_moth))
        self._motors = motors
        self._log.info('ready.')

    # ..........................................................................
    @property
    def event(self):
        return Event.MOTH

    # ..........................................................................
    def _moth_callback(self):
        self._log.info('🍀 moth callback.')

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
        return 'moth'

    # ..........................................................................
    def execute(self):
        '''
        The method called upon each loop iteration. This does nothing in this
        abstract class and is meant to be extended by subclasses.
        '''
        _timestamp = self._message_bus.last_message_timestamp
        if _timestamp is None:
            self._log.info('🍀 moth loop execute; no previous messages.')
        else:
            _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
            self._log.info('🍀 moth loop execute; {}'.format(Subscriber.get_formatted_time('message age:', _elapsed_ms)))

#EOF
