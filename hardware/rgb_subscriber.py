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
init(autoreset=True)

from core.logger import Logger, Level
from core.orient import Orientation
from hardware.i2c_scanner import I2CScanner
from hardware.color import Color
from core.event import Event, Group
from core.subscriber import Subscriber
from hardware.motor_controller import MotorController
#from hardware.rgbmatrix import RgbMatrix, DisplayType
try:
    from rgbmatrix5x5 import RGBMatrix5x5
except ImportError:
    from mock.rgbmatrix5x5 import MockRGBMatrix5x5 as RGBMatrix5x5
#   print(Fore.RED + 'This script requires the rgbmatrix5x5 module. Some features will be disabled.\n'
#           + 'Install with: sudo pip3 install rgbmatrix5x5')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class RgbSubscriber(Subscriber):
    CLASS_NAME = 'rgb'
    '''
    A subscriber to RGB display events.

    :param config:       the application configuration
    :param message_bus:  the message bus
    :param level:        the logging level
    '''
    def __init__(self, config, message_bus, level=Level.INFO):
        Subscriber.__init__(self, RgbSubscriber.CLASS_NAME, config, message_bus=message_bus, suppressed=False, enabled=False, level=level)

        _i2c_scanner = I2CScanner(config, Level.WARN)
        if _i2c_scanner.has_address([0x74]):
            self._stbd_rgbmatrix = RGBMatrix5x5(address=0x74)
            self._stbd_rgbmatrix.set_brightness(0.8)
            self._stbd_rgbmatrix.set_clear_on_exit()
            self._height = self._stbd_rgbmatrix.height
            self._width  = self._stbd_rgbmatrix.width
        else:
            self._stbd_rgbmatrix = None
            self._stbd_rgbmatrix = RGBMatrix5x5(address=0x74)
            self._height = 5
            self._width  = 5
            self._log.warning('test ignored: no rgbmatrix displays found.')
        self.add_event(Event.RGB)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _arbitrate_message(self, message):
        '''
        Pass the message on to the Arbitrator and acknowledge that it has been
        sent (by setting a flag in the message).
        '''
        await self._message_bus.arbitrate(message.payload)
        # increment sent acknowledgement count
#       self._log.debug('acknowledging message {}; with payload value: {}'.format(message.name, message.payload.value))
        message.acknowledge_sent()
        self._log.info('arbitrated message ' + Fore.WHITE + '{} '.format(message.name)
                + Fore.CYAN + 'for event \'{}\' with value: '.format(message.event.label)
                + Fore.YELLOW + '{}'.format(message.payload.value))

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
        if _event.num == Event.RGB.num:
            _value = message.value
            if isinstance(_value, tuple):
                self._set_rgb_color(*_value)
            elif isinstance(_value, list):
                self._set_rgb_colors(*_value)
            elif isinstance(_value, Color):
                self._set_color(_value)
            else:
                raise TypeError('unrecognised message value: {}'.format(type(_value)))
        else:
            self._log.warning('unrecognised RGB event on message {}'.format(message.name) + ''.format(message.event.label))
        await Subscriber.process_message(self, message)
        self._log.debug('post-processing message {}'.format(message.name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _clear(self, show=True):
        '''
        Clears the RGB Matrix by setting its color to black.
        '''
        if self._stbd_rgbmatrix:
            self._set_color(Color.BLACK, show)
        else:
            self._log.info('no rgb matrix available.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_color(self, color, show=True):
        if self._stbd_rgbmatrix:
            self._stbd_rgbmatrix.set_all(color.red, color.green, color.blue)
            if show:
                self._stbd_rgbmatrix.show()
        else:
            self._log.info('no rgb matrix available.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_rgb_colors(self, port_color, stbd_color, show=True):
        '''
        Either sets the port and starboard colors to the provided values
        (as either a tuple or Color), or if there is only a single starboard
        display, divide that display in half.
        '''
        self._log.info('set hues:  port {}; stbd: {}'.format(port_color, stbd_color))
        rows = 5
        for y in range(0, rows):
            if isinstance(port_color, Color):
                self._stbd_rgbmatrix.set_pixel(y, 3, port_color.red, port_color.green, port_color.blue)
                self._stbd_rgbmatrix.set_pixel(y, 4, port_color.red, port_color.green, port_color.blue)
            else:
                self._stbd_rgbmatrix.set_pixel(y, 3, port_color[0], port_color[1], port_color[2])
                self._stbd_rgbmatrix.set_pixel(y, 4, port_color[0], port_color[1], port_color[2])
        for y in range(0, rows):
            if isinstance(stbd_color, Color):
                self._stbd_rgbmatrix.set_pixel(y, 0, stbd_color.red, stbd_color.green, stbd_color.blue)
                self._stbd_rgbmatrix.set_pixel(y, 1, stbd_color.red, stbd_color.green, stbd_color.blue)
            else:
                self._stbd_rgbmatrix.set_pixel(y, 0, stbd_color[0], stbd_color[1], stbd_color[2])
                self._stbd_rgbmatrix.set_pixel(y, 1, stbd_color[0], stbd_color[1], stbd_color[2])
        if show:
            self._stbd_rgbmatrix.show()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_rgb_color(self, red, green, blue, show=True):
        '''
        Sets the RGB Matrix color to the values provided for red, green and blue.
        '''
        if self._stbd_rgbmatrix:
            self._stbd_rgbmatrix.set_all(red, green, blue)
            if show:
                self._stbd_rgbmatrix.show()
        else:
            self._log.info('no rgb matrix available.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        if self.enabled:
            Subscriber.disable(self)
            self._clear(True)
        else:
            self._log.warning('rgb subscriber already disabled.')

#EOF
