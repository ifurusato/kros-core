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
from core.fsm import FiniteStateMachine
from core.message import Message
from core.event import Event
from core.message_bus import MessageBus
from core.message_factory import MessageFactory

# Publisher ....................................................................
class Publisher(FiniteStateMachine):
    '''
    Extends FiniteStateMachine as an event publisher.

    Eventually this will be an abstract class.
    '''
    def __init__(self, name, message_bus, message_factory, level=Level.INFO):
        super().__init__(name)
        '''
        Simulates a publisher of messages.

        :param name:             the unique name for the publisher
        :param message_bus:      the asynchronous message bus
        :param message_factory:  the factory for messages
        :param level:            the logging level
        '''
        self._log = Logger('pub-{}'.format(name), level)
        self._name = name
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
        self._enabled    = False # by default
        self._suppressed = False # by default
        self._closed     = False
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
        self._log.info(Fore.WHITE + '{} publishing message: {} (event: {})'.format(self.name, message.name, message.event.description))
        await self._message_bus.publish_message(message)
        await asyncio.sleep(0.05)
        self._log.info(Fore.WHITE + '{} published message: {} (event: {})'.format(self.name, message.name, message.event.description))

    # ..........................................................................
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        super().start()

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    def enable(self):
        '''
        The necessary state machine call to enable the publisher.
        '''
        super().enable()
        if not self._closed:
            if self._enabled:
                self._log.warning('already enabled.')
            else:
                self._enabled = True
                self._log.info('enabled.')
        else:
            self._log.warning('cannot enable: already closed.')

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
    def disable(self):
        '''
        The state machine call to disable the publisher.
        '''
        super().disable()
        if self._enabled:
            self._enabled = False
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def close(self):
        '''
        The state machine call to permanently disable and close
        the publisher.
        '''
        if not self._closed:
            self.disable()
            super().close()
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.debug('already closed.')

    # ..........................................................................
    def __eq__(self, obj):
        return isinstance(obj, Publisher) and obj.name == self.name

#EOF
