#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-06-04
# modified: 2021-06-06
#
# This class interprets the signals arriving from the 8BitDo N30 Pro Gamepad,
# a paired Bluetooth device. This differs from GamepadDemo in that it simply
# displays the Gamepad output signals. No motors, video, etc.
#

import random
import asyncio
from colorama import init, Fore, Style
init()

from core.event import Event
from core.logger import Logger, Level
from core.rate import Rate

# ...............................................................
class MockGamepad(object):
    def __init__(self, message_bus, message_factory, level=Level.INFO):
        self._message_bus = message_bus
        self._message_factory = message_factory
        self._level   = level
        self._log     = Logger("mock-gp", level)
        self._enabled = False
        self._closed  = False
        _loop_freq_hz = 1
        self._rate = Rate(_loop_freq_hz)
        self._log.info('ready.')

    # ..........................................................................
    def enable(self):
        if self._enabled:
            self._log.info('already enabled.')
        else:
            self._enabled = True
            self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        self._enabled = False

    # ..........................................................................
    async def _get_messages(self):
        '''
        Mocks one or more messages being returned by a Gamepad.
        '''
        await asyncio.sleep(2.0 * random.random())
        self._log.info('🤙 get_messages called.')
        _messages = []
        _messages.append(self._message_factory.create_message(Event.INFRARED_PORT, self._get_random_distance()))
        _messages.append(self._message_factory.create_message(Event.INFRARED_CNTR, self._get_random_distance()))
        _messages.append(self._message_factory.create_message(Event.INFRARED_STBD, self._get_random_distance()))
        return _messages

    def _get_random_distance(self):
        return random.triangular(20.0, 100.0, 70.0)

    # ..........................................................................
    def start_gamepad_loop(self, callback):
        '''
        This is the method to call to actually start the loop.

        The arguments to the callback method include the event.
        '''
        self._log.info(Fore.YELLOW + '🎱 start gamepad loop...')
        if not self._enabled:
            self._log.error('attempt to start gamepad event loop while disabled.')
        elif not self._closed:
            if not self._enabled:
                self._enabled = True
                self._log.info('enabled.')
            else:
                self._log.warning('already enabled.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    async def _gamepad_loop(self, callback, f_is_enabled):
        '''
        The mocked Gamepad loop.
        '''
        self._log.info('starting event loop with enabled argument: {}...'.format(f_is_enabled()))
        __enabled = True
        try:
            while __enabled and f_is_enabled():
                self._log.info('START gamepad loop.')
                self._log.info(Fore.BLUE + 'gamepad enabled: {}; f_is_enabled: {}'.format(__enabled, f_is_enabled()))
                _messages = await self._get_messages()
                for _message in _messages:
                    await callback(_message)
                    # in the original we receive evdev InputDevice events, not messages
#                   self._handleEvent(_event)
                    self._handleMessage(_message)
                if not f_is_enabled():
                    self._log.info('breaking from event loop.')
                    break
                self._rate.wait()
                self._log.info('END gamepad loop with enabled argument: {}...'.format(f_is_enabled()))

        except KeyboardInterrupt:
            self._log.info('caught Ctrl-C, exiting...')
            __enabled = False
        except Exception as e:
            self._log.error('gamepad device error: {}'.format(e))
            __enabled = False
        except OSError as e:
            self._log.error(Gamepad._NOT_AVAILABLE_ERROR + ' [lost connection to gamepad]')
            __enabled = False
        finally:
            '''
            Note that closing the InputDevice is a bit tricky, and we're currently
            masking an exception that's always thrown. As there is no data loss on
            a gamepad event loop being closed suddenly this is not an issue.
            '''
#           try:
#               self._log.info('😨 closing gamepad device...')
#               if self._gamepad:
#                   self._gamepad.close()
#               self._log.info(Fore.YELLOW + '😨 gamepad device closed.')
#           except Exception as e:
#               self._log.info('😨 error closing gamepad device: {}'.format(e))
#           finally:
#               __enabled = False
#               self._gamepad_closed = True
            pass

        self._log.info('exited event loop.')

    # ..........................................................................
    def _handleMessage(self, message):
        '''
        Note that the parameter in the original lass is an evdev InputDevice
        event, not one of our Events. In the mocked version we receive a Message
        so no conversion is necessary.
        '''
        self._log.info('❄️  handle message:' + Fore.WHITE + ' {}; event: {}'.format(message.name, message.event.label))
        return message

#EOF
