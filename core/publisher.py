#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2021-03-17
#

import asyncio
import random
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.fsm import FiniteStateMachine
from core.message_bus import MessageBus
from core.message_factory import MessageFactory

# Publisher ....................................................................
class Publisher(Component, FiniteStateMachine):
    '''
    Extends FiniteStateMachine as a message/event publisher to the message bus.
    '''
    def __init__(self, name, message_bus, message_factory, level=Level.INFO):
        '''
        :param name:             the unique name for the publisher
        :param message_bus:      the asynchronous message bus
        :param message_factory:  the factory for messages
        :param level:            the logging level
        '''
        super().__init__(name)
        if message_bus is None:
            raise ValueError('null message bus argument.')
        elif isinstance(message_bus, MessageBus):
            self._message_bus = message_bus
        else:
            raise ValueError('unrecognised message bus argument: {}'.format(type(message_bus)))
        if message_factory is None:
            raise ValueError('null message factory argument.')
        elif isinstance(message_factory, MessageFactory):
            self._message_factory = message_factory
        else:
            raise ValueError('unrecognised message factory argument: {}'.format(type(message_bus)))
        self._log = Logger('pub:{}'.format(name), level)
        Component.__init__(self, self._log, suppressed=False, enabled=False)
        FiniteStateMachine.__init__(self, self._log, name)
        self._name       = name
        self._message_bus.register_publisher(self)
        self._log.info('ready.')

    # ..........................................................................
    def set_log_level(self, level):
        self._log.level = level

    # ..........................................................................
    @property
    def name(self):
        return self._name

    # ..........................................................................
    @property
    def message_bus(self):
        return self._message_bus

    # ................................................................
    async def publish(self, message):
        '''
        Asynchronously publishes the message to the message bus.
        This is preferred to calling the message bus directly.
        '''
#       self._log.debug(Fore.WHITE + '{} publishing message: {} (event: {})'.format(self.name, message.name, message.event.description))
        await self._message_bus.publish_message(message)
        await asyncio.sleep(0.05)
        self._log.debug(Fore.WHITE + '{} published message: {} (event: {})'.format(self.name, message.name, message.event.description))

    # ..........................................................................
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        super().start()

    # ..........................................................................
    def __eq__(self, obj):
        return isinstance(obj, Publisher) and obj.name == self.name

#EOF
