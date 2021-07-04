#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-16
# modified: 2021-04-22
#

import asyncio
import random
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.orient import Orientation
from core.event import Event, Group
from core.subscriber import Subscriber
from mock.motor import Motor

# ..............................................................................
class InfraredSubscriber(Subscriber):
    CLASS_NAME = 'infrared'
    '''
    A subscriber to infrared events.

    :param name:         the subscriber name (for logging)
    :param message_bus:  the message bus
    :param color:        the color for messages
    :param level:        the logging level 
    '''
    def __init__(self, message_bus, motors, color=Fore.GREEN, level=Level.INFO):
        Subscriber.__init__(self, InfraredSubscriber.CLASS_NAME, message_bus=message_bus, color=color, suppressed=False, enabled=False, level=level)
        self._motors = motors
        self.add_events(Event.by_group(Group.INFRARED))
        self._log.info('ready.')

    # ..........................................................................
    async def _arbitrate_message(self, message):
        '''
        Pass the message on to the Arbitrator and acknowledge that it has been
        sent (by setting a flag in the message).
        '''
        await self._message_bus.arbitrate(message.payload)
        # increment sent acknowledgement count
        message.acknowledge_sent()
        self._log.info(self._color + Style.NORMAL + '🐱 arbitrated payload for event {}; value: {}'.format(message.payload.event.name, message.payload.value))

    # ..........................................................................
    async def process_message(self, message):
        '''
        Process the message.

        :param message:  the message to process.
        '''
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
        _event = message.event
        self._log.info('🐱 pre-processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.description) + Style.RESET_ALL)
        if Event.is_infrared_event(_event):
            self._motors.dispatch_infrared_event(message.payload)
        else:
            self._log.warning('unrecognised infrared event on message {}'.format(message.name) + ''.format(message.event.description))
        await super().process_message(message)
        self._log.debug('🐱 post-processing message {}'.format(message.name))

#EOF
