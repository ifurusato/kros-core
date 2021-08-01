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
    for _speed in Speed:
        _log.info(Fore.BLUE + 'velocity: \'{}\'; astern: {};\tahead: {}'.format(_speed.velocity, _speed.astern, _speed.ahead))
    Speed.configure(_config)
    for _speed in Speed:
        _log.info(Fore.GREEN + 'velocity: \'{}\'; astern: {};\tahead: {}'.format(_speed.velocity, _speed.astern, _speed.ahead))

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

    for _velocity in _velocities:
        _log.info(Fore.YELLOW + 'velocity: {:>7.2f}'.format(_velocity))

    print('\n')

    for _power in _powers:
        _log.info(Fore.YELLOW + 'power: {:>7.2f}'.format(_power))
   
    print('\n .............................')

    for _speed in Speed:
        _log.info(Fore.BLUE + 'SPEED: \'{}\';{}astern: {};\tahead: {}'.format(_speed.label, (' ' * max(0, (22 - len(_speed.label)))), 
                _speed.astern, _speed.ahead))
    Speed.configure(_config)
    for _speed in Speed:
        _log.info(Fore.GREEN + 'SPEED: \'{}\';{}astern: {};\tahead: {}'.format(_speed.label, (' ' * max(0, (22 - len(_speed.label)))), 
                _speed.astern, _speed.ahead))


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
