#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2020-11-06
#
# A mock publisher that generates random messages, publishing them to the
# message bus.
#

import sys, time, itertools, psutil, random
from threading import Thread
import asyncio
from pathlib import Path
from colorama import init, Fore, Style
init()

from core.event import Event
from core.message_factory import MessageFactory
from core.logger import Logger, Level
from core.ticker import Ticker
from core.publisher import Publisher

# ...............................................................
class FloodPublisher(Publisher):

    '''
    A mock publisher than randomly generates messages, publishing
    them to the message bus.
    '''
    def __init__(self, name, message_bus, message_factory, level=Level.INFO):
        super().__init__(name, message_bus, message_factory, level)
        self._log = Logger("flood", level)
#       self._message_bus = message_bus
#       self._message_factory = message_factory
#       self._enabled  = False
#       self._closed   = False
        _loop_freq_hz  = 20
        self._ticker   = Ticker(_loop_freq_hz, self._callback, Level.INFO)
        self._counter  = itertools.count()
        self._log.info('ready.')

#   # ..........................................................................
#   @property
#   def name(self):
#       return 'flood'

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
        self._ticker.enable()
        self._log.info('start loop:\t' + Fore.YELLOW + 'type Ctrl-C or the \"q\" key to exit sensor loop, the \"?\" key for help.')
        print('\n')
        self._log.warning(Fore.YELLOW + 'publish enabled? {}'.format(self._enabled))

        while self._enabled:
            _count = next(self._counter)
            self._log.info(Fore.BLUE + '[{:03d}] A1. loop.'.format(_count))
#           if not self.suppressed:
#               await self._publish_message()
#               _event = FloodPublisher.RANDOM_EVENTS[random.randint(1,len(FloodPublisher.RANDOM_EVENTS)) - 1]
#               _event = self._get_random_event()
#               print('🍎 generating message for event: {}'.format(_event))
#               _message = self._message_factory.get_message(_event, True)
#               print('🍎 publishing message: {}'.format(_message.name))
#               await self._message_bus.publish_message(_message)
#               self._message_bus.publish_message(_message)
#               self._log.info(Fore.BLUE + '[{:03d}] A2. loop.'.format(_count))
#               print('🍏 [{:03d}]published message {} for event: {}'.format(_count, _message.name, _message.event.description))
#           else:
#               self._log.info(Fore.BLUE + '[{:03d}] B1. loop.'.format(_count))
#               await asyncio.sleep(0.1)
#               self._log.info(Fore.BLUE + '[{:03d}] B2. loop.'.format(_count))
#           await asyncio.sleep(0.1)
#           await asyncio.sleep(random.random())
#           time.sleep(0.1)

            # otherwise handle as event
            _event = self._get_random_event()
            if _event is not None:
                self._log.info('[{:03d}] publishing message for event: {}'.format(_count, _event))
                _message = self._message_factory.get_message(_event, True)
                await self._message_bus.publish_message(_message)
            else:
                self._log.info('[{:03d}] no publication.'.format(_count))
            await asyncio.sleep(0.1)
#           await asyncio.sleep(random.random())

    def _callback(self):
        self._log.info('tick.')

    async def _publish_message(self):
        # 🍈 🍅 🍋 🍐 🍓 🍥 🥝 🥚 🥧 🧀 
        _event = self._get_random_event()
#       _event = FloodPublisher.RANDOM_EVENTS[random.randint(1,len(FloodPublisher.RANDOM_EVENTS)) - 1]
#       self._log.info('🍎 publishing message for event: {}'.format(_event))
        print('🍎 generating message for event: {}'.format(_event))
        _message = self._message_factory.get_message(_event, True)
        print('🍎 publishing message: {}'.format(_message.name))
        await self._message_bus.publish_message(_message)
#       self._log.info(Style.BRIGHT + 'publishing message: {}'.format(message.name) + Style.NORMAL + ' (_event: {}; age: {:d}ms);'.format(message.event, message.age))
#       asyncio.create_task(self._message_bus.queue.put(_message), name='publish-message-{}'.format(_message.name))
        await asyncio.sleep(0.05)
#       self._log.info('🍏 published message for event: {}'.format(event))
        print('🍏 published message {} for event: {}'.format(_message.name, _message.event.description))

#EOF
