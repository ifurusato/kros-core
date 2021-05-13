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
#from threading import Thread
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
    def __init__(self, message_bus, message_factory, level=Level.INFO):
        super().__init__('flood', message_bus, message_factory, level)
        self._counter  = itertools.count()
#       _loop_freq_hz  = 20
#       self._ticker = Ticker(_loop_freq_hz, self._publish_message, Level.INFO)
        self.enable()
        self._log.info('ready.')

    def enable(self):
        super().enable()
        print('🍎 sent enable message...')
        if not self.enabled:
            print('🍎 enabled.')
        else:
            print('🍎 disabled.')
    # ................................................................
    async def publish(self):
        '''
        Begins publication of messages. The MessageBus itself calls this function
        as part of its asynchronous loop; it shouldn't be called by anyone except
        the MessageBus.
        '''
#       if self._enabled:
#           self._log.warning('publish cycle already started.')
#           return
        if not self._enabled:
            print('🍎🍎 was not enabled.')
            self.enable()
        self._log.info('start loop:\t' + Fore.YELLOW + 'type Ctrl-C or the \"q\" key to exit sensor loop, the \"?\" key for help.')
        print('\n')
        self._log.info(Fore.YELLOW + 'publish enabled? {}'.format(self._enabled))

        print('🍎🍎 creating task...')
#       asyncio.create_task(self._publish_loop(self._message_bus, lambda: self.enabled), name='publish-loop')
#       self._message_bus.loop.create_task(self._publish_loop(self._message_bus, lambda: self.enabled), name='publish-loop')
        print('🍎🍎 created task.')
#       self._thread = Thread(name='loop', target=FloodPublisher._publish_loop, args=[self, self._message_bus, lambda: self.enabled], daemon=True)
#       self._thread.start()

#       asyncio.create_task(self._start_publish_loop(self._message_bus), name='publish-loop')

#           if not self.suppressed:
#               await self._publish message()
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

        while self.enabled:
            _count = next(self._counter)
            self._log.info(Fore.BLUE + '[{:03d}] A1. loop.'.format(_count))
            # otherwise handle as event
            _event = self._get_random_event()
         
            self._log.info('[{:03d}] publishing message for event: {}'.format(_count, _event))
            _message = self._message_factory.get_message(_event, True)
            await self._message_bus.publish_message(_message)
            await asyncio.sleep(0.1)
#           await asyncio.sleep(random.random())
        self._log.info('publish() END.')

    async def _publish_loop(self, message_bus, f_is_enabled):
        print('🍏 _start_publish_loop() BEGIN.')
        self._log.info('_start_publish_loop() BEGIN.')
        _loop_freq_hz  = 20
#       asyncio.create_task(self._publish_message(self._message_bus), name='publish-loop')
#       self._ticker = Ticker(_loop_freq_hz, self._publish_message, Level.INFO)
#       self._ticker.enable()
        while f_is_enabled():
            _count = next(self._counter)
            self._log.info(Fore.BLUE + '[{:03d}] A1. loop...'.format(_count))
#           await self._publish_message(message_bus)
#           self._log.info(Fore.BLUE + '[{:03d}] A2. loop...'.format(_count))
#           await asyncio.sleep(0.1)
            time.sleep(1.0)
        self._log.info('_start_publish_loop() END.')

    async def _publish_message(self):
        # 🍈 🍅 🍋 🍐 🍓 🍥 🥝 🥚 🥧 🧀 
        self._log.info('tick: publish message...')
        _event = self._get_random_event()
#       _event = FloodPublisher.RANDOM_EVENTS[random.randint(1,len(FloodPublisher.RANDOM_EVENTS)) - 1]
#       self._log.info('🍎 publishing message for event: {}'.format(_event))
        print('🍎 generating message for event: {}'.format(_event))
        _message = self._message_factory.get_message(_event, True)
        print('🍎 publishing message: {}'.format(_message.name))
        await self.message_bus.publish_message(_message)
#       self._log.info(Style.BRIGHT + 'publishing message: {}'.format(message.name) + Style.NORMAL + ' (_event: {}; age: {:d}ms);'.format(message.event, message.age))
#       asyncio.create_task(self._message_bus.queue.put(_message), name='publish-message-{}'.format(_message.name))
        await asyncio.sleep(0.05)
#       self._log.info('🍏 published message for event: {}'.format(event))
        print('🍏 published message {} for event: {}'.format(_message.name, _message.event.description))

#EOF
