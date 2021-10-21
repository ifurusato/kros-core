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
from hardware.motor_controller import MotorController

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class InfraredSubscriber(Subscriber):

    CLASS_NAME = 'infrared'

    '''
    A subscriber to infrared events.

    :param config:       the application configuration
    :param message_bus:  the message bus
    :param motor_ctrl:   the motor controller
    :param level:        the logging level
    '''
    def __init__(self, config, message_bus, motor_ctrl, level=Level.INFO):
        Subscriber.__init__(self, InfraredSubscriber.CLASS_NAME, config, message_bus=message_bus, suppressed=False, enabled=False, level=level)
        if not isinstance(motor_ctrl, MotorController):
            raise ValueError('wrong type for motor_ctrl argument: {}'.format(type(motor_ctrl)))
        self._motor_ctrl = motor_ctrl
        self.add_events(Event.by_group(Group.INFRARED))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _arbitrate_message(self, message):
        '''
        Pass the message on to the Arbitrator and acknowledge that it has been
        sent (by setting a flag in the message).
        '''
        await self._message_bus.arbitrate(message.payload)
        # increment sent acknowledgement count
#       self._log.info('acknowledging message {}; with payload value: {:5.2f}cm'.format(message.name, message.payload.value))
        message.acknowledge_sent()
        self._log.info('arbitrated message:    ' + Fore.WHITE + '{}'.format(message.name) 
                + Fore.CYAN + ' with payload for event: {}; value: {:5.2f}cm'.format(message.payload.event.label, message.payload.value))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def process_message(self, message):
        '''
        Process the message.

        :param message:  the message to process.
        '''
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
        _event = message.event
        self._log.info('🌞 pre-processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.label))
        if Event.is_infrared_event(_event):
            self._motor_ctrl.dispatch_infrared_event(message.payload)
        else:
            self._log.warning('unrecognised infrared event on message {}'.format(message.name) + ''.format(message.event.label))
        await Subscriber.process_message(self, message)
        self._log.info('post-processing message {}'.format(message.name))

#EOF
