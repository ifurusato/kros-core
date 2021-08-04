#}!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-07-29
# modified: 2021-08-02
#
# A collection of Enums related to Direction and Speed, as well as various
# static utility supporting methods.
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
    def value(self):
        raise Exception('can\'t call value directly.')

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
    def __str__(self):
        return 'Speed.{}:{}v={:d};\t{:5.2f}->{:5.2f}.'.format(self.name, (' ' * max(0, (16 - len(self.name)))),
                self._velocity, self._astern, self._ahead)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def from_string(value):
        for s in Speed:
            if value.upper() == s.name:
                return s
        raise NotImplementedError

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def get_proportional_power(velocity):
        '''
        Returns the proportional (interpolated) power corresponding to the velocity
        argument. This linear interpolates first across the x axis (velocity, 
        ranging from -100 to +100), then linear interpolates across the y axis 
        (power, ranging from -1.0 to +1.0) to obtain the power value.

        The returned value is limited by the positive and negative range expressed
        in the YAML configuration. 
        '''
        _x_range = Speed.xrange(velocity) # returns the bounding two Speeds
        _s0 = _x_range[0]
        _s1 = _x_range[1]
        # percentage of way that v is along _s0.velocity to _s1.velocity is: _s0 + velocity / ( _v1 - _v0 )
        if _s0.velocity == _s1.velocity:
            _pp = Speed.lerp( _s0.ahead , _s1.ahead, 1.0 )
            if velocity < 0:
                _pp *= -1
#           _log.info(Fore.RED + 'v={};\tX range: ({} to {});          \t\t'.format(velocity, _s0.ahead, _s1.ahead) + Fore.YELLOW + 'power: {:5.2f}'.format(_pp))
        else:
            if velocity < 0:
                _pc = ( (-1 * _s0.velocity) - velocity ) / ( _s1.velocity - _s0.velocity )
            else:
                _pc = ( velocity - _s0.velocity ) / ( _s1.velocity - _s0.velocity )
            _xt = Speed.lerp(_s0.velocity, _s1.velocity, _pc)
            _pp = Speed.lerp( _s0.ahead , _s1.ahead, _pc )
            if velocity < 0:
                _pp *= -1
#           _log.info(Fore.GREEN + 'v={};\tX range: ({} to {}); xt: {:5.2f}; {:.0%}   \t'.format(velocity, _s0.ahead, _s1.ahead, _xt, _pc) + Fore.YELLOW + 'power: {:5.2f}'.format(_pp))
        return _pp

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def lerp(v0: float, v1: float, t: float) -> float:
        return (1 - t) * v0 + t * v1
    
    @staticmethod
    def inv_lerp(a: float, b: float, v: float) -> float:
        return (v - a) / (b - a)
    
    @staticmethod
    def remap(i_min: float, imax: float, o_min: float, o_max: float, v: float) -> float:
        return lerp(o_min, o_max, inv_lerp(i_min, imax, v))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def xrange(x):
#       print('x {}'.format(x))
        if abs(x) >= Speed.MAXIMUM.velocity:
            return [ Speed.MAXIMUM, Speed.MAXIMUM ]
        r = []
        if x < 0:
            x *= -1
#           print('-? {}'.format(x))
            for s in Speed:
                # counting up from zero, first time we're less than value use that as our high value
#               print(Fore.BLACK+'-sa x: {}; s: {}'.format(x, s)+Style.RESET_ALL)
                if x <= s.velocity:
#                   print('-a {}'.format(s))
                    r.append(s)
                    break
            for s in reversed(Speed):
                # counting down from max, first time we're greater than v use that as our low value
#               print(Fore.BLACK+'-sb {}'.format(s)+Style.RESET_ALL)
                if x >= s.velocity:
#                   print('-b x: {}; s: {}'.format(x, s))
                    r.append(s)
                    break
        else:
#           print('+? {}'.format(x))
            for s in reversed(Speed):
#               print(Fore.BLACK+'+sa {}'.format(s)+Style.RESET_ALL)
                if x >= s.velocity:
#                   print('+a {}'.format(s))
                    r.append(s)
                    break
            for s in Speed:
#               print(Fore.BLACK+'+sb {}'.format(s)+Style.RESET_ALL)
                if x <= s.velocity:
#                   print('+b {}'.format(s))
                    r.append(s)
                    break
        if len(r) == 1:
            raise Exception('only 1: speed: {}'.format(r))
        return r

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
