#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-07-15
# modified: 2021-07-15
#
#   A test of the motors.
#

import sys, time, traceback
import pytest
import numpy
from colorama import init, Fore, Style
init()

from core.config_loader import ConfigLoader
from core.logger import Logger, Level
from core.message_bus import MessageBus
from core.orient import Orientation

from hardware.i2c_scanner import I2CScanner
from hardware.motor_configurer import MotorConfigurer

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def motor_test():

    _message_bus = None
    try:

        _level = Level.INFO
        _log = Logger("motor-test", _level)
        _log.info('configuring motor test...')
        # read YAML configuration
        _config = ConfigLoader().configure()
        _message_bus = MessageBus(_config, _level)
        _i2c_scanner = I2CScanner(_config, _level)

        # add motor controller
        _motor_configurer = MotorConfigurer(_config, _message_bus, _i2c_scanner, level=Level.WARN)
        _motors = _motor_configurer.get_motors()

        if _motors:
            _motors.enable()

        _port_motor = _motors.get_motor(Orientation.PORT)
        _stbd_motor = _motors.get_motor(Orientation.STBD)

        _neg = -0.85
        _zero = 0.0
        _max = 0.85
        _step = 0.2

        _log.info(' ---------------------------------- ')

        for _power in numpy.arange(_zero, _max, _step, float):
            _log.info('setting motor power: {:<4.2f}'.format(_power))
            _port_motor.set_motor_power(_power)
            time.sleep(0.01)

        _log.info(' ---------------------------------- ')

        for _power in numpy.arange(_max, _zero, -1 * _step, float):
            _log.info('setting motor power: {:<4.2f}'.format(_power))
            _port_motor.set_motor_power(_power)
            time.sleep(0.01)

#       _log.info(' ---------------------------------- ')

#       for _power in numpy.arange(_zero, _neg, -1 * _step, float):
#           _log.info('setting motor power: {:<4.2f}'.format(_power))
#           _port_motor.set_motor_power(_power)
#           time.sleep(0.01)

#       _log.info(' ---------------------------------- ')

#       for _power in numpy.arange(_neg, _zero, 0.1, float):
#           _log.info('setting motor power: {:<4.2f}'.format(_power))
#           _port_motor.set_motor_power(_power)
#           time.sleep(0.01)

#       _log.info(' ---------------------------------- ')

#       _port_motor.set_motor_power(_power)
#       time.sleep(0.5)

#       _port_motor.set_motor_power(_power)
#       time.sleep(0.5)

#       _port_motor.set_motor_power(_power)
#       time.sleep(0.5)

        # start message bus loop...
#       _message_bus.enable()

    finally:
        if _message_bus:
            _message_bus.close()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():
    motor_test()

if __name__ == "__main__":
    main()

#EOF
