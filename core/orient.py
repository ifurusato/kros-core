#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2021-04-22
#
# A collection of navigation/orientation-related enums.
#

from enum import Enum

# ..............................................................................
class Orientation(Enum):
    NONE  = ( 0, "none", "none")
    BOTH  = ( 1, "both", "both")
    PORT  = ( 2, "port", "port")
    CNTR  = ( 3, "center", "cntr")
    STBD  = ( 4, "starboard", "stbd")
    PORT_SIDE = ( 5, "port-side", "psid") # only used with infrareds
    STBD_SIDE = ( 6, "stbd-side", "ssid") # only used with infrareds

    # ignore the first param since it's already set by __new__
    def __init__(self, num, name, label):
        self._name = name
        self._label = label

    # this makes sure the name is read-only
    @property
    def name(self):
        return self._name

    # this makes sure the label is read-only
    @property
    def label(self):
        return self._label

# ..............................................................................
class Direction(Enum):
#   FORWARD = 0
#   REVERSE = 1
    AHEAD   = 0
    ASTERN  = 1

# ..............................................................................
class Rotation(Enum):
    COUNTER_CLOCKWISE = 0
    CLOCKWISE         = 1

# ..............................................................................
class Speed(Enum):
    STOP          = ( 1, "stop",  0.0 )
    DEAD_SLOW     = ( 2, "dead slow", 20.0 )
    SLOW          = ( 3, "slow", 30.0 )
    HALF          = ( 4, "half speed", 50.0 )
    TWO_THIRDS    = ( 5, "two third speed", 66.7 )
    THREE_QUARTER = ( 6, "three quarter speed", 75.0 )
    FULL          = ( 7, "full speed", 90.0 )
    EMERGENCY     = ( 8, "emergency speed", 100.0 )
    MAXIMUM       = ( 9, "maximum speed", 100.000001 )

    # ignore the first param since it's already set by __new__
    def __init__(self, num, label, value):
        self._label = label
        self._value = value

    @property
    def label(self):
        return self._label

    @property
    def value(self):
        return self._value

    @staticmethod
    def get_slower_than(speed):
        '''
        Provided a value between 0-100, return the next lower Speed.
        '''
        if speed < Speed.DEAD_SLOW.value:
            return Speed.STOP
        elif speed < Speed.SLOW.value:
            return Speed.DEAD_SLOW
        elif speed < Speed.HALF.value:
            return Speed.SLOW
        elif speed < Speed.TWO_THIRDS.value:
            return Speed.HALF
        elif speed < Speed.THREE_QUARTER.value:
            return Speed.TWO_THIRDS
        elif speed < Speed.FULL.value:
            return Speed.THREE_QUARTER
        else:
            return Speed.FULL

# ..............................................................................
class Cardinal(Enum):
    NORTH     = ( 0, 'north' )
    NORTHEAST = ( 1, 'north-east' )
    EAST      = ( 2, 'east' )
    SOUTHEAST = ( 3, 'south-east' )
    SOUTH     = ( 4, 'south' )
    SOUTHWEST = ( 5, 'south-west' )
    WEST      = ( 6, 'west' )
    NORTHWEST = ( 7, 'north-west' )

    # ignore the first param since it's already set by __new__
    def __init__(self, num, display):
        self._display = display

    @property
    def display(self):
        return self._display

    @staticmethod
    def get_heading_from_degrees(degrees):
        '''
        Provided a heading in degrees return an enumerated cardinal direction.
        '''
        _value = round((degrees / 45.0) + 0.5)
        _array = [ Cardinal.NORTH, Cardinal.NORTHEAST, Cardinal.EAST, Cardinal.SOUTHEAST, Cardinal.SOUTH, Cardinal.SOUTHWEST, Cardinal.WEST, Cardinal.NORTHWEST ]
        return _array[(_value % 8)];

    @staticmethod
    def get_heading_from_degrees_old(degrees):
        '''
        Provided a heading in degrees return an enumerated cardinal direction.
        '''
        if 0 <= degrees <= 67.5:
            return Cardinal.NORTHEAST
        elif 67.5  <= degrees <= 112.5:
            return Cardinal.EAST
        elif degrees > 337.25 or degrees < 22.5:
            return Cardinal.NORTH
        elif 292.5 <= degrees <= 337.25:
            return Cardinal.NORTHWEST
        elif 247.5 <= degrees <= 292.5:
            return Cardinal.WEST
        elif 202.5 <= degrees <= 247.5:
            return Cardinal.SOUTHWEST
        elif 157.5 <= degrees <= 202.5:
            return Cardinal.SOUTH
        elif 112.5 <= degrees <= 157.5:
            return Cardinal.SOUTHEAST

    @staticmethod
    def get_color_for_direction(value):
        if value is Cardinal.NORTH:
            return Color.BLUE
        elif value is Cardinal.NORTHEAST:
            return Color.MAGENTA
        elif value is Cardinal.EAST:
            return Color.FUCHSIA
        elif value is Cardinal.SOUTHEAST:
            return Color.RED
        elif value is Cardinal.SOUTH:
            return Color.YELLOW
        elif value is Cardinal.SOUTHWEST:
            return Color.GREEN
        elif value is Cardinal.WEST:
            return Color.LIGHT_BLUE
        elif value is Cardinal.NORTHWEST:
            return Color.CYAN
        else:
            return Color.BLACK

#EOF
