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
from core.speed import Direction
from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from hardware.i2c_scanner import I2CScanner, DeviceNotFound
from hardware.motor_configurer import MotorConfigurer
from hardware.motor_controller import MotorController
from hardware.motor import Motor

#from behave.travel import Travel

_log = Logger('test', Level.INFO)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def key_callback(event):
    _log.info('callback on event: {}'.format(event))

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_motors():

    _errcode = -1
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

        _motor_ctrl = MotorController(_config, _message_bus, _motor_configurer, level=_level)
        _motor_ctrl.enable()

        _log.info('starting test...')

        _log.info(Fore.MAGENTA + 'configuring travel...')
#       _travel = Travel(_config, _motor_configurer, Level.INFO)
#       _log.info(Fore.MAGENTA + 'enabling travel...')
#       _travel.enable()

        _log.info(Fore.MAGENTA + 'starting travel...')
        _distance_cm = 10

        # move ahead .........
        _result = _motor_ctrl.travel(Direction.ASTERN, _distance_cm, True)
        _log.info(Fore.MAGENTA + 'travel complete, returned: {} '.format(_result))

        # move astern ........
        _result = _motor_ctrl.travel(Direction.AHEAD, _distance_cm, True)
        _log.info(Fore.MAGENTA + 'travel complete, returned: {} '.format(_result))

#       # wait up to 7 seconds until stopped .................
#       _is_stopped = _motor_ctrl.wait_til_stopped()
#       _log.info(Fore.RED   + '🙆 RETURNED FROM WAIT.')
#       _count = 0
#       while _count < 7 and not _motor_ctrl.stopped:
#           _log.info(Fore.RED   + '🙆 alive? [{:d}]; waiting...')
#           _count += 1
#           time.sleep(1.0)

        time.sleep(2.0)

        # closing .................
        _motor_ctrl.close()
        _message_bus.close()

        _log.info('test complete.')
#       _travel.disable()
        _errcode = 0

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
        _errcode = 1
    except DeviceNotFound as e:
        _log.error('no potentiometer found, exiting.')
        _errcode = 1
    except Exception as e:
        print(Fore.RED + 'EXCEPTION' + Style.RESET_ALL)
        _log.error('{} encountered, exiting: {}'.format(type(e), e))
        _errcode = 1
    finally:
        _log.info(Fore.MAGENTA + 'finally error code: {:d}'.format(_errcode))
        sys.exit(_errcode)
        _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
        _log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():
    test_motors()

if __name__== "__main__":
    main()

#EOF
