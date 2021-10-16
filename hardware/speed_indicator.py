#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-10-13
# modified: 2021-10-13
#

import colorsys
from math import isclose
from colorama import init, Fore, Style
init()

from core.logger import Level, Logger
from core.component import Component
from core.event import Event
from core.ranger import Ranger
from core.speed import Speed
from hardware.color import Color
from core.queue_publisher import QueuePublisher

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class SpeedIndicator(Component):
    '''
    Coordinates RGB messages sent to displays indicating speed of motors.

    :param config:           application configuration
    :param orientation:      used only for the logger label
    :param level:            the logging Level
    '''
    def __init__(self, queue_publisher, port_motor, stbd_motor, level=Level.INFO):
        self._log = Logger('speed-ind', level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        self._queue_publisher = queue_publisher
        self._message_factory = queue_publisher.message_factory
        self._ranger          = Ranger(0.0, 255.0, 0.0, 360.0)
        self._port_motor      = port_motor
        self._stbd_motor      = stbd_motor
        self._port_value      = None
        self._stbd_value      = None
        self._port_hue        = Color.BLACK
        self._stbd_hue        = Color.BLACK
        self._port_motor.add_indicator_callback(self.indicate_port_speed)
        self._stbd_motor.add_indicator_callback(self.indicate_stbd_speed)
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def indicate_port_speed(self, value):
#       self._log.info(Fore.RED + 'indicate port velocity: {}'.format(value))
        if value != self._port_value:
            self._port_hue = self._get_rgb_from_fixed_colors(value)
            self._log.debug('😈 convert port velocity: {} to hue: {}'.format(value, self._port_hue))
            self._queue_publisher.put(self._message_factory.create_message(Event.RGB, [self._port_hue, self._stbd_hue]))
        self._port_value = value

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def indicate_stbd_speed(self, value):
#       self._log.info(Fore.GREEN + 'indicate stbd velocity: {}'.format(value))
        if value != self._stbd_value:
            self._stbd_hue = self._get_rgb_from_fixed_colors(value)
            self._log.debug('😈 convert stbd velocity: {} to hue: {}'.format(value, self._stbd_hue))
            self._queue_publisher.put(self._message_factory.create_message(Event.RGB, [self._port_hue, self._stbd_hue]))
        self._stbd_value = value

    # ..........................................................................
    def _get_rgb_from_fixed_colors(self, value):
        '''
        Converts the value via a simple table using fixed colors.
        '''
        # if value < -1.0 * Speed.MAXIMUM.velocity:
        if   value <= -1.0 * Speed.FULL.velocity:
            return Color.PURPLE
        elif value <= -1.0 * Speed.THREE_QUARTER.velocity:
            return Color.VIOLET
        elif value <= -1.0 * Speed.TWO_THIRDS.velocity:
            return Color.BLUE_VIOLET
        elif value <= -1.0 * Speed.HALF.velocity:
            return Color.BLUE
        elif value <= -1.0 * Speed.ONE_THIRD.velocity:
            return Color.SKY_BLUE
        elif value <= -1.0 * Speed.SLOW.velocity:
            return Color.CYAN
        elif value <= -1.0 * Speed.DEAD_SLOW.velocity:
            return Color.TURQUOISE
        elif value < -1.0 * Speed.STOP.velocity - 5.0:
            return Color.DARK_TURQUOISE
        elif isclose(value, 0.0, abs_tol=0.03 * 100):
#           return Color.VERY_DARK_GREY
            return Color.BLACK
        elif value <= Speed.DEAD_SLOW.velocity - 5.0:
            return Color.DARK_GREEN
        elif value <= Speed.DEAD_SLOW.velocity:
            return Color.GREEN
        elif value <= Speed.SLOW.velocity:
            return Color.YELLOW_GREEN
        elif value <= Speed.ONE_THIRD.velocity:
            return Color.YELLOW
        elif value <= Speed.HALF.velocity:
            return Color.ORANGE
        elif value <= Speed.TWO_THIRDS.velocity:
            return Color.TANGERINE
        elif value <= Speed.THREE_QUARTER.velocity:
            return Color.RED
        elif value <= Speed.FULL.velocity:
            return Color.FUCHSIA
        elif value <= Speed.MAXIMUM.velocity:
            return Color.MAGENTA

    # ..........................................................................
    def _get_rgb_from_conversion(self, value):
        '''
        Converts a hue value into an RGB value and displays it on the heading portion of the pixels.

        The hue value should be in degrees from 0-360, as colors on a color wheel.
        If the value goes negative it's expected that the 181-360 degree values are simply
        negated, so we convert the argument accordingly.

        This hasn't been debugged to provide good values, so we're using a different conversion
        algorithm currently.
        '''
        hue = self._ranger.convert(value)
        if hue < 0:
            hue = 360.0 - hue
        _offset = 0
        if hue < 0:
            r, g, b = [ Color.VERY_DARK_GREY.red, Color.VERY_DARK_GREY.green, Color.VERY_DARK_GREY.blue ]
        else:
            h = ((hue + _offset) % 360) / 360.0
            r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0)]
        return ( r, g, b )

#EOF
