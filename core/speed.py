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
from colorama import init, Fore, Style
init()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Direction(Enum):
    AHEAD   = 0
    ASTERN  = 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Speed(Enum):
    '''
    Provides an enumeration of both ahead (forward) and astern (reverse)
    Chadburn-style speeds, as corresponding to an abstract velocity.

    The default values for astern and ahead are set to zero; these much be
    set from the YAML application configuration via the configure() method.
    '''
    #                    label             velocity  astern  ahead
    STOP          = ( 1, "stop",                  0,    0.0,   0.0 )
    DEAD_SLOW     = ( 2, "dead slow",            20,    0.0,   0.0 )
    SLOW          = ( 3, "slow",                 30,    0.0,   0.0 )
    HALF          = ( 4, "half speed",           50,    0.0,   0.0 )
    TWO_THIRDS    = ( 5, "two thirds speed",     67,    0.0,   0.0 )
    THREE_QUARTER = ( 6, "three quarter speed",  75,    0.0,   0.0 )
    FULL          = ( 7, "full speed",           90,    0.0,   0.0 )
    MAXIMUM       = ( 9, "maximum speed",       100,    0.0,   0.0 )

    # ignore the first param since it's already set by __new__
    def __init__(self, num, label, velocity, astern, ahead):
        self._label    = label
        self._velocity = velocity
        self._astern   = astern
        self._ahead    = ahead

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def label(self):
        return self._label

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def velocity(self):
        return self._velocity

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def astern(self):
        return self._astern

    @astern.setter
    def astern(self, astern):
        self._astern = astern

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def ahead(self):
        return self._ahead

    @ahead.setter
    def ahead(self, ahead):
        self._ahead = ahead

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def from_string(value):
        for s in Speed:
            if value.upper() == s.name:
                return s
        raise NotImplementedError

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def configure(config):
        '''
        A static method that imports astern and ahead values from the provided
        YAML-sourced configuration.

        This imports from 'kros:motor:speed'
        '''
        _entries = config['kros'].get('motor').get('speed')
        _astern_speeds = _entries.get('astern')
        _ahead_speeds  = _entries.get('ahead')
        for _speed in Speed:
            _speed_enum = Speed.from_string(_speed.name)
            _speed_enum.astern = _astern_speeds.get(_speed_enum.name)
            _speed_enum.ahead  = _ahead_speeds.get(_speed_enum.name)

#EOF
