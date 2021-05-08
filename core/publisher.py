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
from core.message import Message
from core.event import Event

# Publisher ....................................................................
class Publisher(object):

    RANDOM_EVENTS = [
            Event.DECREASE_SPEED, Event.INCREASE_SPEED, Event.INFRARED_PORT_SIDE, Event.BRAKE,
            Event.BUMPER_STBD, Event.INFRARED_CNTR, Event.SNIFF, Event.INFRARED_STBD,
            Event.INFRARED_STBD_SIDE, Event.HALT, Event.STOP, Event.ROAM,
            Event.INFRARED_PORT, Event.NOOP, Event.BUMPER_CNTR, Event.BUMPER_PORT,
            Event.SHUTDOWN, Event.AHEAD, Event.ASTERN, Event.ROAM, Event.SNIFF
        ]

    '''
    Eventually this will be an abstract class.
    '''
    def __init__(self, name, message_bus, message_factory, level=Level.INFO):
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
        self._message_bus = message_bus
        if message_factory is None:
            raise ValueError('null message factory argument.')
        self._message_factory = message_factory
        self._enabled    = False # by default
        self._suppressed = False # by default
        self._closed     = False
        self._log.info(Fore.BLACK + 'ready.')

    # ..........................................................................
    @property
    def name(self):
        return self._name

    # ................................................................
    async def publish(self):
        '''
        Begins publication of messages. The MessageBus itself calls this function
        as part of its asynchronous loop; it shouldn't be called by anyone except
        the MessageBus.
        '''
        if self._enabled:
            self._log.warning('publish cycle already started.')
            return
        self._enabled = True
        while self._enabled:
            _event = self._get_random_event()
            _message = self._message_factory.get_message(_event, _event.description)
            # publish the message
            self._message_bus.publish_message(_message)
            self._log.info(Fore.WHITE + Style.BRIGHT + '{} PUBLISHED message: {} (event: {})'.format(self.name, _message, _event.description))
            # simulate randomness of publishing messages
#           await asyncio.sleep(random.random())
#           self._log.debug(Fore.BLACK + Style.BRIGHT + 'after await sleep.')

    # ..........................................................................
    def _get_random_event(self):
        '''
        Returns one of the randomly-assigned event types.
        '''
        return Publisher.RANDOM_EVENTS[random.randint(0, len(Publisher.RANDOM_EVENTS)-1)]

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    def enable(self):
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
        Enable or disable capturing characters. Upon starting the loop the
        suppress flag is set False, but can be enabled or disabled as
        necessary without halting the thread.

        Future feature: not currently functional.
        '''
        self._suppressed = mode
        if self.suppressed:
            self._log.info('publishing suppressed.')
        else:
            self._log.info('publishing unsuppressed.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._enabled = False
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def close(self):
        '''
        Permanently close and disable the message bus.
        '''
        if not self._closed:
            self.disable()
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.debug('already closed.')

#EOF
