#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-05
# modified: 2020-10-18
#
# This is a test class that interprets the signals arriving from the 8BitDo N30
# Pro Gamepad, a paired Bluetooth device. This differs from GamepadDemo in that
# it simply displays the Gamepad output signals. No motors, video, etc.
#

import sys, itertools, threading # TEMP
from colorama import init, Fore, Style
init()

from core.config_loader import ConfigLoader
from core.logger import Logger, Level
from core.message import Message
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.publisher import Publisher

from mock.gamepad import Gamepad

# ..............................................................................
class GamepadPublisher(Publisher):

    def __init__(self, config, message_bus, message_factory, level=Level.INFO):
        super().__init__('gamepad', message_bus, message_factory, level)
        if config is None:
            raise ValueError('no configuration provided.')
        if message_bus is None:
            raise ValueError('null message bus argument.')
        elif isinstance(message_bus, MessageBus):
            self._message_bus = message_bus
        else:
            raise ValueError('unrecognised message bus argument: {}'.format(type(message_bus)))
        if message_factory is None:
            raise ValueError('null message factory argument.')
        elif isinstance(message_factory, MessageFactory):
            self._message_factory = message_factory
        else:
            raise ValueError('unrecognised message factory argument: {}'.format(type(message_bus)))
        # attempt to find the gamepad
        self._gamepad = Gamepad(config, self._message_bus, self._message_factory, Level.INFO)
        self._enabled = False
        self._counter = itertools.count()
        self._log.info('connecting gamepad...')
        self._gamepad_enabled = True
        self._connect_gamepad()
#       self._gamepad.connect()
        self._log.info('ready.')

    # ..........................................................................
    def _connect_gamepad(self):
        if not self._gamepad_enabled:
            self._log.info('gamepad disabled.')
            return
        if self._gamepad is None:
            self._log.info('creating gamepad...')
            try:
                self._gamepad = Gamepad(self._config, self._queue, Level.INFO)
            except GamepadConnectException as e:
                self._log.error('unable to connect to gamepad: {}'.format(e))
                self._gamepad = None
                self._gamepad_enabled = False
                self._log.info('gamepad unavailable.')
                return
        if self._gamepad is not None:
            self._log.info(Fore.YELLOW + 'enabling gamepad...')
            self._gamepad.enable()
            _count = 0
            while not self._gamepad.has_connection():
                _count += 1
                if _count == 1:
                    self._log.info(Fore.YELLOW + 'connecting to gamepad...')
                else:
                    self._log.info(Fore.YELLOW + 'gamepad not connected; re-trying... [{:d}]'.format(_count))
                self._gamepad.connect()
                time.sleep(0.5)
                if self._gamepad.has_connection() or _count > 5:
                    break

    # ..........................................................................
    def has_connected_gamepad(self):
        return self._gamepad is not None and self._gamepad.has_connection()

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
        self._log.info('start loop:\t' + Fore.YELLOW + 'type Ctrl-C or the \"q\" key to exit sensor loop, the \"?\" key for help.')
        print('\n')
        while self._enabled:
            try:
                # see if any sensor (key) has been activated
                _count = next(self._counter)
                self._log.info('[{:03d}] loop.'.format(_count))

                await self.gamepad_callback()

                # otherwise handle as event
#               _event = self.get_event_for_char(och)
                if _event is not none:
                    self._log.info('[{:03d}] "{}" ({}) pressed; publishing message for event: {}'.format(_count, ch, och, _event))
                    _message = self._message_factory.get_message(_event, True)
                    await self._message_bus.publish_message(_message)
                    if self._exit_on_complete and self.all_triggered:
                        self._log.info('[{:03d}] complete.'.format(_count))
                        self.disable()
    #               elif self._message_bus.verbose:
    #                   self.waiting_for_message()
                else:
                    self._log.info('[{:03d}] unmapped key "{}" ({}) pressed.'.format(_count, ch, och))
    #           await asyncio.sleep(0.1)
    #           await asyncio.sleep(random.random())
            except keyboardinterrupt:
                self._log.info('caught ctrl-c, exiting...')
                self._enabled = false

        pass

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if self._enabled:
            self._log.warning('already enabled.')
            return
        self._log.info('enabling...')
        self._gamepad.enable()
        self._gamepad.start_gamepad_loop(self.gamepad_callback)
        self._enabled = True
        self._log.info('enabled.')

    # ..........................................................................
    def gamepad_callback(self, event):
        self._log.info(Fore.YELLOW + 'gamepad callback for event: {}'.format(event))

    # ..........................................................................
    def get_thread_position(self, thread):
        frame = sys._current_frames().get(thread.ident, None)
        if frame:
            return frame.f_code.co_filename, frame.f_code.co_name, frame.f_code.co_firstlineno

    # ..........................................................................
    def disable(self):
        if not self._enabled:
            self._log.warning('already disabled.')
            return
        self._log.info('disabling...')
        self._enabled = False
        self._gamepad.disable()
        self._log.info('disabled.')

    # ..........................................................................
    def _close_demo_callback(self):
        self._log.info(Fore.MAGENTA + 'close demo callback...')
#       self._queue.disable()
        self.disable()
        self.close()

    # ..........................................................................
    def close(self):
        if self._enabled:
            self.disable()
        self._log.info('closing...')
        self._gamepad.close()
        self._log.info('closed.')

# EOF
