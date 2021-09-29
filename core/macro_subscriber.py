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
from core.macro_publisher import MacroPublisher

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MacroSubscriber(Subscriber):

    CLASS_NAME = 'macro'

    '''
    A subscriber to macro events. This receives MACRO events and queues
    the script from the MacroPublisher's script library for execution.

    :param config:            the application configuration
    :param message_bus:       the message bus
    :param macro_publisher:   the macro publisher/processor
    :param level:             the logging level
    '''
    def __init__(self, config, message_bus, macro_publisher, level=Level.INFO):
        Subscriber.__init__(self, MacroSubscriber.CLASS_NAME, config, message_bus=message_bus, suppressed=False, enabled=False, level=level)
        if not isinstance(macro_publisher, MacroPublisher):
            raise ValueError('wrong type for macro_publisher argument: {}'.format(type(macro_publisher)))
        self._macro_pub = macro_publisher
        self.add_events(Event.by_group(Group.MACRO))

#   async def _arbitrate_message(self, message):
#       '''
#       Pass the message on to the Arbitrator and acknowledge that it has been
#       sent (by setting a flag in the message).
#       '''
#       await self._message_bus.arbitrate(message.payload)
#       # increment sent acknowledgement count
#       self._log.info('acknowledging message {}; with payload value: {:5.2f}cm'.format(message.name, message.payload.value))
#       message.acknowledge_sent()
#       self._log.info('arbitrated message:    ' + Fore.WHITE + '{}'.format(message.name) 
#               + Fore.CYAN + ' with payload for event: {}; value: {:5.2f}cm'.format(message.payload.event.label, message.payload.value))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def process_message(self, message):
        '''
        Process the message.

        :param message:  the message to process.
        '''
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
        _event = message.event
        self._log.debug('pre-processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.label))
        if _event == Event.MACRO:
            self._macro_pub.queue_event(message.payload)
        else:
            self._log.warning('unrecognised infrared event on message {}'.format(message.name) + ''.format(message.event.label))
        await Subscriber.process_message(self, message)
        self._log.debug('post-processing message {}'.format(message.name))

#EOF
