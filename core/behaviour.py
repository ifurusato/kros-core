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

from abc import ABC, abstractmethod
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.subscriber import Subscriber
from core.behaviour_manager import BehaviourManager

# ...............................................................
class Behaviour(ABC, Subscriber):
    '''
    An abstract class providing the basis for a looped behaviour
    that executes a callback every loop. This is implemented as a
    Subscriber to the two clock events, CLOCK_TICK and CLOCK_TOCK,
    and execution relies upon reception of these events from the
    message bus.

    :param name:             the name of this behaviour
    :param config:           the application configuration
    :param message_bus:      the message bus
    :param message_factory:  the message factory
    :param callback:         the optional callback function (can be added later)
    :param level:            the optional log level
    '''
    def __init__(self, name, config, message_bus, message_factory, callback, level=Level.INFO):
        self._log = Logger('beh:{}'.format(name), level)
        Subscriber.__init__(self, name, message_bus, suppressed=True, enabled=False, level=Level.INFO)
        self._name            = name
        self._config          = config
        if isinstance(message_bus, MessageBus):
            self._message_bus = message_bus
        else:
            raise ValueError('expected MessageBus, not {}.'.format(type(message_bus)))
        if isinstance(message_factory, MessageFactory):
            self._message_factory = message_factory
        else:
            raise ValueError('expected MessageFactory, not {}.'.format(type(message_factory)))
        self._callbacks       = []
        if callback:
            self.add_callback(callback)
        # add default subscriptions for a Behaviour
        self.add_event(Event.CLOCK_TICK)
        self.add_event(Event.CLOCK_TOCK)
        # register this behaviour with behaviour manager
        _beh_mgr = message_bus.get_subscriber(BehaviourManager.CLASS_NAME)
        _beh_mgr.register_behaviour(self)
        self._log.info('🔘 ready.')

    # ..........................................................................
    @property
    def name(self):
        return self._name

    # ..........................................................................
    @property
    def config(self):
        return self._config

    # ..........................................................................
    @property
    def message_bus(self):
        return self._message_bus

    # ..........................................................................
    @property
    def message_factory(self):
        return self._message_factory

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
    async def process_message(self, message):
        self._log.debug(self._color + Style.DIM + 'processing message {}'.format(message.name))
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
        # indicate that this subscriber has processed the message
        message.process(self)
        # now process message...
        if not self.suppressed:
            self._log.info('👿 not suppressed.')
            _event = message.payload.event
            if Event.is_clock_event(_event):
                self._log.info('👿 executing loop method on event {}...'.format(_event.description))
                self.execute(message)
                self._log.info('👿 executing callbacks...')
                for _callback in self._callbacks:
                    self._log.info('👿 executing callback...')
                    _callback()
            else:
                self._log.info('👿 processed other message {}'.format(message.name))
        else:
            self._log.debug('{} behaviour suppressed.'.format(self.name))
        self._log.debug('👿 processed message {}'.format(message.name))

    # ..........................................................................
    @abstractmethod
    def execute(self, message):
        '''
        The method called upon each loop iteration. This does nothing in this
        abstract class and is meant to be extended by subclasses. It is not
        called when the behaviour is suppressed.

        :param message:  an optional Message passed along by the message bus
        '''
        self._log.info('loop execute.')

    # ..........................................................................
    def enable(self):
        '''
        The necessary state machine call to enable the behaviour.
        '''
        if not self.closed:
            if not self.enabled:
                super().enable()
                self._log.info('enabled behaviour {}'.format(self.name))

    # ..........................................................................
    def disable(self):
        '''
        The state machine call to disable the behaviour.
        '''
        if self.enabled:
            super().disable()
            self._log.info('disabled behaviour {}'.format(self.name))

#EOF
