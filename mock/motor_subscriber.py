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
from core.event import Event
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
    def __init__(self, name, message_bus, color=Fore.MAGENTA, level=Level.INFO):
        super().__init__(name, message_bus, color, level)
        self.events = [ Event.PORT_VELOCITY, Event.STBD_VELOCITY, 
                Event.PORT_THETA, Event.STBD_THETA,
                Event.DECREASE_SPEED, Event.INCREASE_SPEED, Event.HALT, Event.STOP, Event.BRAKE ]
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
#           self._log.info(self._color + Style.DIM + 'arbitrated payload for event {}; value: {}'.format(message.payload.event.name, message.payload.value))

#EOF
