#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-10-05
# modified: 2021-02-07
#
# Tests the port and starboard motors for encoder ticks. This includes a quick
# and dirty velocity to power converter to convert a rotary encoder output to
# motor power.
#

import pytest
import sys, numpy, time, traceback
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from core.i2c_scanner import I2CScanner
from mock.motor import Motor
from mock.motor_configurer import MotorConfigurer

# settings ................

_log = Logger('test', Level.INFO)

# ..............................................................................
@pytest.mark.unit
def test_velocity_to_power_conversion():
    # velocity to power conversion test:
    for v in numpy.arange(0.0, 60.0, 2.0):
        p = Motor.velocity_to_power(v)
        _log.info('velocity: {:5.2f};'.format(v) + Fore.YELLOW + ' power: {:5.2f};'.format(p))

# ..............................................................................
def callback_method_A(value):
    global action_A
    action_A = not action_A
    _log.info('callback method fired;\t' + Fore.YELLOW + 'action A: {}'.format(action_A))

# ..............................................................................
def callback_method_B(value):
    global action_B
    action_B = not action_B
    _log.info('callback method fired;\t' + Fore.YELLOW + 'action B: {}'.format(action_B))

# ..............................................................................
@pytest.mark.unit
def test_motors():

    _start_time = dt.now()

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
    
        _log.info('creating message factory...')
        _message_factory = MessageFactory(Level.INFO)
        _log.info('creating message bus...')
        _message_bus = MessageBus(Level.WARN)

        _i2c_scanner = I2CScanner(_config, Level.WARN)

        # add motor controller
        _motor_configurer = MotorConfigurer(_config, _message_bus, _i2c_scanner, enable_mock=False, level=Level.INFO)
        _motors = _motor_configurer.get_motors()

        _motors.enable()
    

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
    except Exception as e:
        _log.error('error: {}'.format(e))
    finally:
#       if _port_motor != None:
#           _port_motor.set_motor_power(0.0)
#       if _stbd_motor != None:
#           _stbd_motor.set_motor_power(0.0)
        pass

    _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
    _log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))

# ..............................................................................
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
