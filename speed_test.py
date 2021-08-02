#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019-2021 by Murray Altheim. All rights reserved. This file is part
# of the K-Series Robot Operating System (KROS) project, released under the MIT
# License. Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-14
# modified: 2021-07-20
#

import pytest
import sys, itertools, traceback
import numpy
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from core.speed import Speed

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_speed():

    _log = Logger("test-speed", Level.INFO)

    # read YAML configuration
    _config = ConfigLoader().configure()
#   _speeds = _config['kros'].get('motor').get('speed')
#   for _speed in Speed:
#       _log.info(Fore.BLUE + 'velocity: \'{}\'; astern: {};\tahead: {}'.format(_speed.velocity, _speed.astern, _speed.ahead))
    Speed.configure(_config)
#   for _speed in Speed:
#       _log.info(Fore.GREEN + 'velocity: \'{}\'; astern: {};\tahead: {}'.format(_speed.velocity, _speed.astern, _speed.ahead))

#   _log.info(Fore.YELLOW + 'lerp-1: {}'.format( lerp(0, 100, 0.5) ))

#   _start = Speed.DEAD_SLOW.ahead
#   _end   = Speed.SLOW.ahead
#   _log.info(Fore.YELLOW + 'lerp-1: {}'.format( lerp(_start, _end, 0.5) ))

    print('\n')
    print('\n')

#   _powers = []
#   for _speed in reversed(Speed):
#       if _speed.astern != 0.0:
#           _powers.append(_speed.astern)
#   for _speed in Speed:
#       _powers.append(_speed.ahead)

    _velocities, _powers = populate_power_range()

#   for _velocity in _velocities:
#       _log.info(Fore.YELLOW + 'velocity: {:>7.2f}'.format(_velocity))
#   print('\n')
#   for _power in _powers:
#       _log.info(Fore.YELLOW + 'power: {:>7.2f}'.format(_power))
   
    print('\n .............................')

#   for _speed in reversed(Speed):
#       _log.info(Fore.BLUE + 'SPEED: \'{}\';{}velocity: {}; astern: {}'.format(_speed.label,
#               (' ' * max(0, (22 - len(_speed.label)))), _speed.velocity, _speed.astern))
#   for _speed in Speed:
#       _log.info(Fore.GREEN + 'SPEED: \'{}\';{}velocity: {}; ahead: {}'.format(_speed.label,
#               (' ' * max(0, (22 - len(_speed.label)))), _speed.velocity, _speed.ahead))

    '''
    Okay, now we have the velocity points on the x axis, though they're not evenly spaced.
    For any given velocity we can determine where on the x axis we are (between which two
    points) and interpolate the x coordinate. We can then determine the two points on the
    Y axis that we're between and interpolate there as well.
    '''

#   print_range(-200)
#   print_range(-100)
#   print_range(-80)
#   print_range(-69)
#   print_range(-63)
#   print_range(-50)
#   print_range(0)
#   print_range(50)
#   print_range(63)
#   print_range(69)
#   print_range(80)
#   print_range(100)
#   print_range(200)
#   sys.exit(0)

    for _v in numpy.arange(-100.0, 10.0, 1.0, float):
        _log.info('\nv: {}'.format(_v))
        _x_range = Speed.xrange(_v)
        if len(_x_range) < 2:
            raise Exception('not 2.')
        _x0 = _x_range[0]
        _x1 = _x_range[1]
#       print('x0: {} x1: {}'.format(_x0,_x1))
        _log.info(Fore.YELLOW + '...for velocity: {};\tx0={}; x1={}'.format(_v, _x0.velocity, _x1.velocity))

    sys.exit(0)

    # so, our input value for velocity is 40
#   _v = 33.0
    for _v in numpy.arange(-100.0, 100.0, 1.0, float):
        _log.info('\nv: {}'.format(_v))
        _x_range = Speed.xrange(_v)
        _log.info(Fore.YELLOW + '...for velocity: {}'.format(_v))
    
        _x0 = _x_range[0]
        _x1 = _x_range[1]
        # percentage of way that v is along _x0.velocity to _x1.velocity is:    _x0 + _v / ( _v1 - _v0 )
        _log.info(Fore.BLUE + 'X range: {} ({}) to {} ({})'.format(_x0, _x0.velocity, _x1, _x1.velocity))
        if _x0.velocity == _x1.velocity:
            _pp = lerp( _x0.ahead , _x1.ahead, 1.0 ) # proportional (interpolated) power
            _log.info(Fore.RED + 'X range: {} ({}) to {} ({}); power: {:5.2f}'.format(_x0, _x0.ahead, _x1, _x1.ahead, _pp ))
        else:
            _pc = ( _v - _x0.velocity ) / ( _x1.velocity - _x0.velocity )
            _xt = lerp(_x0.velocity, _x1.velocity, _pc)
            _log.info(Fore.YELLOW + 'X range: {} ({}) to {} ({}); xt: {}; {:.0%}'.format(_x0, _x0.velocity, _x1, _x1.velocity, _xt, _pc))
    
            _pp = lerp( _x0.ahead , _x1.ahead, _pc ) # proportional (interpolated) power
            _log.info(Fore.MAGENTA + 'X range: {} ({}) to {} ({}); xt: {}; power: {:5.2f}'.format(_x0, _x0.ahead, _x1, _x1.ahead, _xt, _pp ))

#   astern:
#       MAXIMUM:           -90.1     -100
#       FULL:              -70.1     -90
#       THREE_QUARTER:     -60.1     -75
#       TWO_THIRDS:        -50.1     -67
#       HALF:              -40.1     -50
#       SLOW:              -30.1     -30
#       DEAD_SLOW:         -20.1     -20
#       STOP:                0.0       0
#   ahead:
#       STOP:                0.0       0
#       DEAD_SLOW:          20.0      20
#       SLOW:               30.0      30
#       HALF:               40.0      50
#       TWO_THIRDS:         50.0      67
#       THREE_QUARTER:      60.0      75
#       FULL:               70.0      90
#       MAXIMUM:            90.0     100

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   _min =  -1.0
#   _max =   1.0
#   _step =  0.2
#   _log.info('ramp up!   ..............................')
#   for _value in numpy.arange(_min, _max, _step, float):
#       _log.info('+ VALUE: {:<5.2f}'.format(_value))
#   print('')
#   _log.info('ramp down!   ............................')
#   for _value in numpy.arange(_max, _min, -1 * _step, float):
#       _log.info('- VALUE: {:<5.2f}'.format(_value))
#   print('')

    # print(lerp(0, 100, 0.5))
    # print(lerp(0, 100, 0.5))
    # print(inv_lerp(0, 100, 50)) # 0.5

    # lerp is the one you would need, plug in the start, stop and the 
    # percentage in between (as float from 0 to 1)
    #
    # https://docs.scipy.org/doc/scipy/reference/tutorial/interpolate.html

#   sys.exit(0)

    _log.info('complete.')

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

def print_range(x):
    _range = Speed.xrange(x)
    print(Fore.BLUE + '{}:'.format(x) 
            + Fore.YELLOW + '\t{} -> {}  '.format(_range[0].velocity, _range[1].velocity) 
            + Fore.GREEN + '\t{}'.format(_range[0]) 
            + Fore.BLACK + '\tto:  ' 
            + Fore.GREEN + '{}'.format(_range[1]) + Style.RESET_ALL)

def populate_power_range():
    _velocities = []
    _powers   = []
    for _speed in reversed(Speed):
        if _speed.astern != 0.0:
            _velocities.append(-1 * _speed.velocity)
            _powers.append(_speed.astern)
    for _speed in Speed:
        _velocities.append(_speed.velocity)
        _powers.append(_speed.ahead)
    return _velocities, _powers

def lerp(v0: float, v1: float, t: float) -> float:
    return (1 - t) * v0 + t * v1

def inv_lerp(a: float, b: float, v: float) -> float:
    return (v - a) / (b - a)

def remap(i_min: float, imax: float, o_min: float, o_max: float, v: float) -> float:
    return lerp(o_min, o_max, inv_lerp(i_min, imax, v))

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():
    try:
        test_speed()
    except KeyboardInterrupt:
        print('Ctrl-C caught: test interrupted.')
    except Exception as e:
        print(Fore.RED + 'Error in test: {} / {}'.format(e, traceback.format_exc()) + Style.RESET_ALL)
    finally:
        pass

if __name__ == "__main__":
    main()

#EOF
