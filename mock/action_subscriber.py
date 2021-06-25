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
from mock.roam import Roam

# ..............................................................................
class ActionSubscriber(Subscriber):
    '''
    A subscriber for high-level actions (behaviours).

    :param name:         the subscriber name (for logging)
    :param message_bus:  the message bus
    :param color:        the color for messages
    :param level:        the logging level 
    '''
    def __init__(self, config, message_bus, motors, color=Fore.MAGENTA, level=Level.INFO):
        super().__init__('action', message_bus, color, level)
        if config is None:
            raise ValueError('null configuration argument.')
        self._config = config
        self._roam = Roam(config, message_bus, motors, level)
        self._motors = motors
        self.events = [ Event.ROAM, Event.SNIFF ]
        self._log.info('action subscriber ready.')

    # ..........................................................................
    async def _arbitrate_message(self, message):
        '''
        Pass the message on to the Arbitrator and acknowledge that it has been
        sent (by setting a flag in the message).
        '''
        await self._message_bus.arbitrate(message.payload)
        # increment sent acknowledgement count
        message.acknowledge_sent()
#       if self._message_bus.verbose:
        self._log.info(self._color + Style.NORMAL + 'arbitrated payload for event {}; value: {}'.format(message.payload.event.name, message.payload.value))

    # ..........................................................................
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        self._roam.start()
        super().start()

    # ..........................................................................
    def enable(self):
        super().enable()
        self._roam.enable()
        self._log.info('🌞 enabled.')

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
        if _event is Event.ROAM:
            self._log.info(Fore.YELLOW + 'ROAM: message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.description) + Style.RESET_ALL)
            if self._roam.enabled:
                self._roam.disable()
            else:
                self._roam.enable()
#           self._behaviour_handler.dispatch_roam_event(_event)
        elif _event is Event.SNIFF:
            self._log.info(Fore.YELLOW + 'SNIFF: message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.description) + Style.RESET_ALL)
        else:
            self._log.warning('unrecognised message {}'.format(message.name) + ''.format(message.event.description))
        await super().process_message(message)
        self._log.debug('post-processing message {}'.format(message.name))

#EOF
