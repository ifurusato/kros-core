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
#from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event
from core.subscriber import Subscriber

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ClockSubscriber(Subscriber):
    '''
    A subscriber to clock events.

    :param config:       the application configuration
    :param name:         the unique name for this clock subscriber
    :param message_bus:  the message bus
    :param level:        the logging level
    '''
    def __init__(self, config, name, message_bus, callback, level=Level.INFO):
        Subscriber.__init__(self, name, config, message_bus=message_bus, suppressed=False, enabled=False, level=level)
        self._callback = callback
        _cfg = config['kros'].get('subscriber').get('clock')
        self.add_event(Event.TICK)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _arbitrate_message(self, message):
        '''
        Not currently used in this class.
        '''
        self._log.info(Fore.YELLOW + '😝 arbitrate message...')
        await self._message_bus.arbitrate(message.payload)
        # increment sent acknowledgement count
        message.acknowledge_sent()
        self._log.info('arbitrated payload for event {}; value: {}'.format(message.payload.event.name, message.payload.value))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def process_message(self, message):
        '''
        Process the message.

        :param message:  the message to process.
        '''
#       self._log.info(Fore.YELLOW + '😝 process message...')
        if self.enabled:
#           if message.gcd:
#               raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
            _event = message.event
#           self._log.info('pre-processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.label))
            if _event is Event.TICK:
                if self._callback:
#                   self._log.info(Fore.YELLOW + '😝 clock tick, executing callback...')
                    self._callback()
                else:
                    self._log.warning('😝 no callback registered.')
            else:
                print('😝 event: {}'.format(_event))
                raise Exception('unrecognised event on message {}'.format(message.name) + ''.format(message.event.label))
        else:
            self._log.warning('disabled: ignoring dispatch.')
        # we don't need to dispose of this singleton message

#EOF
