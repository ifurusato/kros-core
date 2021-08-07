#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-10-05
# modified: 2021-08-07
#
# Tests the port and starboard motors for directly by setting their power, from
# a digital potentiometer, without the intermediaries of velocity, slew, or PID
# controllers.
#

import pytest
import sys, numpy, time, traceback
from datetime import datetime as dt
from math import isclose
from colorama import init, Fore, Style
init()

from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.orient import Orientation
from core.rate import Rate
from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from hardware.i2c_scanner import I2CScanner
from hardware.motor_configurer import MotorConfigurer
from hardware.motor import Motor
from hardware.digital_pot import DigitalPotentiometer, DeviceNotFound

_log = Logger('test', Level.INFO)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_motors():

    _start_time = dt.now()

    try:

        # read YAML configuration
        _level = Level.INFO
        _loader = ConfigLoader(_level)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _log.info('creating message bus...')
        _message_bus = MessageBus(_config, _level)
        _log.info('creating message factory...')
        _message_factory = MessageFactory(_message_bus, _level)

        _i2c_scanner = I2CScanner(_config, _level)

        # add motor controller
        _motor_configurer = MotorConfigurer(_config, _message_bus, _i2c_scanner, motors_enabled=True, level=_level)
        _port_motor = _motor_configurer.get_motor(Orientation.PORT)
        _stbd_motor = _motor_configurer.get_motor(Orientation.STBD)

        _port_motor.enable()
        _stbd_motor.enable()

        # configure digital potentiometer for motor speed
        _pot = DigitalPotentiometer(_config, _level)
        _pot.set_output_limits(-0.90, 0.90)
        _pot.set_output_limits(-0.90, 0.90)

#       sys.exit(0)
        _last_scaled_value = 0.0
        _log.info('starting test...')
        _hz = 10
        _rate = Rate(_hz, Level.ERROR)
        while True:
            _scaled_value = _pot.get_scaled_value(False)
            if _scaled_value != _last_scaled_value: # if not the same as last time
                # math.isclose(3, 15, abs_tol=0.03 * 255) # 3% on a 0-255 scale
                if isclose(_scaled_value, 0.0, abs_tol=0.05):
                    _pot.set_black()
                    _port_motor.set_motor_power(0.0)
                    _stbd_motor.set_motor_power(0.0)
                    _log.info(Fore.BLACK + 'scaled value: {:9.6f}'.format(_scaled_value))
                else:
                    _pot.set_rgb(_pot.value)
                    _port_motor.set_motor_power(_scaled_value)
                    _stbd_motor.set_motor_power(_scaled_value)
                    _log.info(Fore.YELLOW + 'scaled value: {:9.6f}'.format(_scaled_value))
            _last_scaled_value = _scaled_value
            _rate.wait()

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
    except DeviceNotFound as e:
        _log.error('no potentiometer found, exiting.')
    except Exception as e:
        _log.error('{} encountered, exiting: {}'.format(type(e), e))
    finally:
#       if _port_motor != None:
#           _port_motor.set_motor_power(0.0)
#       if _stbd_motor != None:
#           _stbd_motor.set_motor_power(0.0)
        pass

    _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
    _log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():
    try:
        test_motors()
    except Exception as e:
        print(Fore.RED + 'error in motor test: {}'.format(e) + Style.RESET_ALL)
        traceback.print_exc(file=sys.stdout)
    finally:
        pass

if __name__== "__main__":
    main()

#EOF
