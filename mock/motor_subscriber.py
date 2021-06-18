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
class MotorSubscriber(Subscriber):
    '''
    A mocked dual motor controller with encoders.

    :param name:         the subscriber name (for logging)
    :param message_bus:  the message bus
    :param color:        the color for messages
    :param level:        the logging level 
    '''
    def __init__(self, name, message_bus, motors, color=Fore.MAGENTA, level=Level.INFO):
        super().__init__(name, message_bus, color, level)
        self._motors = motors
        self.events = [ Event.VELOCITY, Event.THETA, Event.EVEN,
                Event.PORT_VELOCITY, Event.PORT_THETA, Event.STBD_VELOCITY, Event.STBD_THETA,
                Event.INCREASE_PORT_VELOCITY, Event.DECREASE_PORT_VELOCITY,
                Event.INCREASE_STBD_VELOCITY, Event.DECREASE_STBD_VELOCITY,
                Event.INCREASE_PORT_THETA, Event.DECREASE_PORT_THETA,
                Event.INCREASE_STBD_THETA, Event.DECREASE_STBD_THETA,
                Event.TURN_AHEAD_PORT, Event.TURN_TO_PORT, Event.TURN_ASTERN_PORT, Event.SPIN_PORT,
                Event.SPIN_STBD, Event.TURN_ASTERN_STBD, Event.TURN_TO_STBD, Event.TURN_AHEAD_STBD,
                Event.FULL_ASTERN, Event.HALF_ASTERN, Event.SLOW_ASTERN, Event.DEAD_SLOW_ASTERN,
                Event.DEAD_SLOW_AHEAD, Event.SLOW_AHEAD, Event.HALF_AHEAD, Event.FULL_AHEAD,  
                Event.DECREASE_VELOCITY, Event.INCREASE_VELOCITY, Event.HALT, Event.STOP, Event.BRAKE ]
        self._log.info('motor subscriber ready.')

    # ..........................................................................
    async def _arbitrate_message(self, message):
        '''
        Pass the message on to the Arbitrator and acknowledge that it has been
        sent (by setting a flag in the message).
        '''
#       if self._message_bus.verbose:
#           self._log.info(self._color + Style.DIM + 'arbitrating payload for event {}; value: {}'.format(message.payload.event.name, message.payload.value))
        await self._message_bus.arbitrate(message.payload)
        # increment sent acknowledgement count
        message.acknowledge_sent()
#       if self._message_bus.verbose:
        self._log.info(self._color + Style.NORMAL + 'arbitrated payload for event {}; value: {}'.format(message.payload.event.name, message.payload.value))

    # ..........................................................................
    async def process_message(self, message):
        '''
        Process the message.

        :param message:  the message to process.
        '''
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
        _event = message.event
        self._log.info('pre-processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.description) + Style.RESET_ALL)
        if _event.group is Group.STOP:
            self._motors.dispatch_stop_event(_event)
        elif _event.group is Group.VELOCITY:
            self._motors.dispatch_velocity_event(message.payload)
        elif _event.group is Group.THETA:
            self._motors.dispatch_theta_event(_event)
        elif _event.group is Group.CHADBURN:
            self._motors.dispatch_chadburn_event(_event)
        else:
            self._log.warning('unrecognised message {}'.format(message.name) + ''.format(message.event.description))
        await super().process_message(message)
        self._log.debug('post-processing message {}'.format(message.name))

#EOF
