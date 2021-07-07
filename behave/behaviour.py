#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-07-06
#

from abc import ABC, abstractmethod
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.subscriber import Subscriber
from behave.behaviour_manager import BehaviourManager

# ...............................................................
class Behaviour(ABC, Subscriber):
    '''
    An abstract class providing the basis for a behaviour which
    executes a callback method every loop, implemented using the
    Ticker class, which is managed from the BehaviourManager.
    The loop callback is registered during class construction.

    :param name:             the name of this behaviour
    :param config:           the application configuration
    :param message_bus:      the message bus
    :param message_factory:  the message factory
    :param level:            the optional log level
    '''
    def __init__(self, name, config, message_bus, message_factory, level=Level.INFO):
        self._log = Logger('beh:{}'.format(name), level)
        Subscriber.__init__(self, name, config, message_bus, suppressed=True, enabled=False, level=Level.INFO)
        if isinstance(message_factory, MessageFactory):
            self._message_factory = message_factory
        else:
            raise ValueError('expected MessageFactory, not {}.'.format(type(message_factory)))
        # register this behaviour with behaviour manager
        _behaviour_manager = message_bus.get_subscriber(BehaviourManager.CLASS_NAME)
        if _behaviour_manager:
            _behaviour_manager._register_behaviour(self)
        else:
            self._log.warning('no behaviour manager found: {} operating as subscriber only.'.format(self.name))
        self._log.info('ready.')

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
        '''
        self._log.info('start.')
        Subscriber.start(self)

    # ..........................................................................
    async def process_message(self, message):
        '''
        Overrides the method in Subscriber.
        '''
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
        _event = message.payload.event
        self._log.info(self._color + Style.NORMAL + '👿 processing message {}; with event '.format(message.name) + Fore.YELLOW + ' {}'.format(_event.description))
        # indicate that this subscriber has processed the message
        message.process(self)
        # now process message...
        if not self.suppressed:
            # is this still valid for a Behaviour?
            self._log.info('👿 calling execute() method on event {}...'.format(_event.description))
            self.execute(message)
            self._log.info('👿 called execute() method on event {}...'.format(_event.description))
        else:
            self._log.info(Style.DIM + '👿 {} behaviour suppressed.'.format(self.name))
        self._log.info('👿 processed message {}'.format(message.name))

    # ..........................................................................
    @abstractmethod
    def trigger_event(self):
        '''
        This returns the event used to trigger (toggle enable/disable) the
        behaviour manually; it may be enabled or disabled through other 
        means. The method should be implemented as a @property.
        '''
        raise NotImplementedError('trigger_event() must be implemented in subclasses.')

    # ..........................................................................
    @abstractmethod
    def callback(self):
        '''
        The method called upon each loop iteration. This does nothing in this
        abstract class and is meant to be extended by subclasses. It is up to
        subclasses to suppress the results of this method when the behaviour
        is suppressed as the Ticker will faithfully call it upon each loop
        iteration.

        :param message:  an optional Message passed along by the message bus
        '''
        raise NotImplementedError('callback() must be implemented in subclasses.')

    # ..........................................................................
    @abstractmethod
    def execute(self, message):
        '''
        The method called by process_message(). This does nothing in this
        abstract class and is meant to be extended by subclasses. It is not
        called when the behaviour is suppressed.

        :param message:  the Message passed along by the message bus
        '''
        raise NotImplementedError('execute() must be implemented in subclasses.')

    # ..........................................................................
    def enable(self):
        '''
        The necessary state machine call to enable the behaviour.
        '''
        if not self.closed:
            if not self.enabled:
                Subscriber.enable(self)
                self._log.info('enabled behaviour {}'.format(self.name))

    # ..........................................................................
    def disable(self):
        '''
        The state machine call to disable the behaviour.
        '''
        if self.enabled:
            Subscriber.disable(self)
            self._log.info('disabled behaviour {}'.format(self.name))

#EOF
