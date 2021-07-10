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
from core.util import Util
from core.subscriber import Subscriber
from behave.behaviour import Behaviour

# ...............................................................
class Sniff(Behaviour):
    '''
    Implements a sniffing behaviour, whatever that is.

    :param name:            the name of this behaviour
    :param config:          the application configuration
    :param message_bus:     the asynchronous message bus
    :param message_factory: the factory for messages
    :param motors:          the motor controller
    :param level:           the optional log level
    '''
    def __init__(self, config, message_bus, message_factory, motors, level=Level.INFO):
        Behaviour.__init__(self, 'sniff', config, message_bus, message_factory, level)
        self._motors = motors
        self._log.info('ready.')

    # ..........................................................................
    @property
    def trigger_event(self):
        '''
        This returns the event used to enable/disable the behaviour manually.
        '''
        return Event.SNIFF

    # ..........................................................................
    def callback(self):
        self._log.info('🌺 sniff callback.')

#   # ..........................................................................
#   def start(self):
#       '''
#       The necessary state machine call to start the publisher, which performs
#       any initialisations of active sub-components, etc.
#       '''
#       Behaviour.start(self)

    # ..........................................................................
    @property
    def name(self):
        return 'sniff'

    # ..........................................................................
    def execute(self):
        '''
        The method called upon each loop iteration. This does nothing in this
        abstract class and is meant to be extended by subclasses.
        '''
        _timestamp = self._message_bus.last_message_timestamp
        if _timestamp is None:
            self._log.info('🌺 sniff loop execute; no previous messages.')
        else:
            _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
            self._log.info('🌺 sniff loop execute; {}'.format(Util.get_formatted_time('message age:', _elapsed_ms)))

#EOF
