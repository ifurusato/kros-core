#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-16
# modified: 2021-10-31
#

import asyncio
import random
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event, Group
from core.orientation import Orientation
from core.subscriber import Subscriber
from hardware.motor_controller import MotorController

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MotorSubscriber(Subscriber):
    '''
    Subscribes to motor-related events, passing stop, chadburn, velocity
    and theta directives to the motor controller.

    :param name:         the subscriber name (for logging)
    :param config:       the application configuration
    :param message_bus:  the message bus
    :param level:        the logging level
    '''
    def __init__(self, config, message_bus, motor_ctrl, level=Level.INFO):
        Subscriber.__init__(self, 'motor', config, message_bus, suppressed=False, enabled=False, level=level)
        if not isinstance(motor_ctrl, MotorController):
            raise ValueError('wrong type for motor_ctrl argument: {}'.format(type(motor_ctrl)))
        self._motor_ctrl = motor_ctrl
        self.add_events(Event.by_groups([Group.STOP, Group.VELOCITY, Group.THETA, Group.CHADBURN]))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _arbitrate_message(self, message):
        '''
        Pass the message on to the Arbitrator and acknowledge that it has been
        sent (by setting a flag in the message).
        '''
        await self._message_bus.arbitrate(message.payload)
        # increment sent acknowledgement count
        message.acknowledge_sent()
#       if self._message_bus.verbose:
#       self._log.debug('arbitrated payload for event {}; value: {}'.format(message.payload.event.name, message.payload.value))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def process_message(self, message):
        '''
        Process the message.

        :param message:  the message to process.
        '''
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected.')
        _event = message.event
        self._log.debug('processing message with event: {}...'.format(_event.label))

        # STOP and CHADBURN events need no further processing
        if _event.group is Group.STOP:
            self._log.info('dispatching STOP event message...')
            self._motor_ctrl.dispatch_stop_event(message.payload)
        elif _event.group is Group.CHADBURN:
            self._log.info('dispatching CHADBURN event message...')
            self._motor_ctrl.dispatch_chadburn_event(message.payload)
        elif _event.group is Group.VELOCITY:
            self._log.info('dispatching VELOCITY event message...')
            self._motor_ctrl.dispatch_velocity_event(message.payload)
        elif _event.group is Group.THETA:
            self._log.info('dispatching THETA event message...')
            self._motor_ctrl.dispatch_theta_event(message.payload)
        else:
            self._log.warning('unrecognised message {}'.format(message.name) + ''.format(message.event.label))
        await Subscriber.process_message(self, message)
#       self._log.debug('post-processing message {}'.format(message.name))

#EOF
