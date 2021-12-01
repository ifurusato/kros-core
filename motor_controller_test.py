#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-10-05
# modified: 2021-07-17
#
# Tests the port and starboard motors via the MotorController class, by setting
# the target velocity using a digital potentiometer. Depending on the application
# configuration this will enable/disable the slew controller, PID controller, and
# jerk limiter. When the PID controller is disabled the Motor class uses an
# interpolated velocity algorithm to convert velocity to motor power.
#

import pytest
import sys, numpy, time, traceback
from datetime import datetime as dt
from math import isclose
from colorama import init, Fore, Style
init()

from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.message import Payload
from core.event import Event
from core.orientation import Orientation
from core.direction import Direction
from core.speed import Speed
from core.rate import Rate
from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from hardware.i2c_scanner import I2CScanner, DeviceNotFound
from hardware.motor_configurer import MotorConfigurer
from hardware.motor import Motor
from hardware.motor_controller import MotorController
from hardware.analog_pot import AnalogPotentiometer
from hardware.digital_pot import DigitalPotentiometer

_log = Logger('test', Level.INFO)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def assertResult(result, event, orientation, direction, port_velocity, stbd_velocity):
    '''
    Assert the expected values of the result.
    '''
    global g_test_count
    g_test_count += 1
    # return ( _event, _value, _orientation, _direction, _port_target_velocity, _stbd_target_velocity )
    _log.info(Fore.GREEN + '\nasserted result:\n    event:\t{}\n    value:\t{}\n    orient:\t{}\n    direction:\t{}\n    port tvel:\t{}\n    stbd tvel:\t{}'.format(*result))
    assert result[0] is event, 'expected event {} not {}'.format(event.label, result[0])
    assert result[2] is orientation, 'expected orientation {} not {}'.format(orientation.label, result[2])
    if direction:
        assert result[3] is direction, 'expected direction {} not {}'.format(direction.label, result[3])
    if port_velocity:
        assert result[4] == port_velocity, 'expected port velocity {} not {}'.format(port_velocity, result[4])
    else:
        assert result[4] is None, 'expected null port velocity'
    if stbd_velocity:
        assert result[5] == stbd_velocity, 'expected starboard velocity {} not {}'.format(stbd_velocity, result[5])
    else:
        assert result[5] is None, 'expected null starboard velocity'
  
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_motors():
    global g_test_count
    g_test_count = 0

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

        # add motor controller
        _i2c_scanner = I2CScanner(_config, _level)
        _motor_configurer = MotorConfigurer(_config, _message_bus, _i2c_scanner, motors_enabled=True, level=_level)
        _port_motor = _motor_configurer.get_motor(Orientation.PORT)
        _stbd_motor = _motor_configurer.get_motor(Orientation.STBD)

        _motor_ctrl = MotorController(_config, _message_bus, _motor_configurer, level=_level)
        _motor_ctrl.enable()

        # test all velocity directives .............................................................

        # VELOCITY               = ( 200, "velocity",               100, Group.VELOCITY ) # with value
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.VELOCITY, (Direction.AHEAD, Speed.SLOW))),
                Event.VELOCITY, Orientation.CNTR, Direction.AHEAD, 30.0, 30.0)
        # PORT_VELOCITY          = ( 201, "port velocity",          100, Group.VELOCITY ) # with value
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.PORT_VELOCITY, (Direction.ASTERN, Speed.HALF))),
                Event.PORT_VELOCITY, Orientation.PORT, Direction.ASTERN, -50.0, None)
        # STBD_VELOCITY          = ( 202, "stbd velocity",          100, Group.VELOCITY ) # with value
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.STBD_VELOCITY, (Direction.ASTERN, Speed.ONE_THIRD))),
                Event.STBD_VELOCITY, Orientation.STBD, Direction.ASTERN, None, -40.0)

        # VELOCITY               = ( 200, "velocity",               100, Group.VELOCITY ) # with value
        # using single positive float for CNTR
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.VELOCITY, 30.0)),
                Event.VELOCITY, Orientation.CNTR, Direction.AHEAD, 30.0, 30.0)
        # using single negative float for CNTR
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.VELOCITY, -42.0)),
                Event.VELOCITY, Orientation.CNTR, Direction.ASTERN, -42.0, -42.0)
        # using int for PORT, STBD
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.VELOCITY, 27)),
                Event.VELOCITY, Orientation.CNTR, Direction.AHEAD, 27.0, 27.0)
        # using tuple float for PORT, STBD
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.VELOCITY, (30.0, 40.0))),
                Event.VELOCITY, Orientation.CNTR, Direction.AHEAD, 30.0, 40.0)
        # using tuple float for PORT, STBD, with CLOCKWISE
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.VELOCITY, (40.0, -30.0))),
                Event.VELOCITY, Orientation.CNTR, Direction.CLOCKWISE, 40.0, -30.0)

        # PORT_VELOCITY          = ( 201, "port velocity",          100, Group.VELOCITY ) # with value
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.PORT_VELOCITY, (Direction.ASTERN, Speed.HALF))),
                Event.PORT_VELOCITY, Orientation.PORT, Direction.ASTERN, -50.0, None)
        # STBD_VELOCITY          = ( 202, "stbd velocity",          100, Group.VELOCITY ) # with value
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.STBD_VELOCITY, (Direction.ASTERN, Speed.ONE_THIRD))),
                Event.STBD_VELOCITY, Orientation.STBD, Direction.ASTERN, None, -40.0)

        # payload with tuple
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.VELOCITY, (57.0, 41.0))),
                Event.VELOCITY, Orientation.CNTR, Direction.AHEAD, 57.0, 41.0)
        # payload with float
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.PORT_VELOCITY, 51.0)),
                Event.PORT_VELOCITY, Orientation.PORT, Direction.UNKNOWN, 51.0, None)
        # with int
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.PORT_VELOCITY, 56)),
                Event.PORT_VELOCITY, Orientation.PORT, Direction.UNKNOWN, 56.0, None)

        # DECREASE_VELOCITY      = ( 203, "decrease velocity",      100, Group.VELOCITY ) # step change
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.DECREASE_VELOCITY, None)),
                Event.DECREASE_VELOCITY, Orientation.CNTR, None, -5.0, -5.0)
        # INCREASE_VELOCITY      = ( 204, "increase velocity",      100, Group.VELOCITY ) # step change
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.INCREASE_VELOCITY, None)),
                Event.INCREASE_VELOCITY, Orientation.CNTR, None, 5.0, 5.0)
        # DECREASE_PORT_VELOCITY = ( 205, "decrease port velocity", 100, Group.VELOCITY ) # step change
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.DECREASE_PORT_VELOCITY, None)),
                Event.DECREASE_PORT_VELOCITY, Orientation.PORT, None, -5.0, None)
        # INCREASE_PORT_VELOCITY = ( 206, "increase port velocity", 100, Group.VELOCITY ) # step change
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.INCREASE_PORT_VELOCITY, None)),
                Event.INCREASE_PORT_VELOCITY, Orientation.PORT, None, 5.0, None)
        # DECREASE_STBD_VELOCITY = ( 207, "decrease stbd velocity", 100, Group.VELOCITY ) # step change
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.DECREASE_STBD_VELOCITY, None)),
                Event.DECREASE_STBD_VELOCITY, Orientation.STBD, None, None, -5.0)
        # INCREASE_STBD_VELOCITY = ( 208, "increase stbd velocity", 100, Group.VELOCITY ) # step change
        assertResult(_motor_ctrl.dispatch_velocity_event(Payload(Event.INCREASE_STBD_VELOCITY, None)),
                Event.INCREASE_STBD_VELOCITY, Orientation.STBD, None, None, 5.0)

        _log.info(Fore.YELLOW + 'executed {:d} tests.'.format(g_test_count))

        # test motor control .......................................................................
        _active_test = False
        if _active_test:

            # configure digital potentiometer for motor speed
            _dpot = DigitalPotentiometer(_config, level=_level)
#           _dpot.set_output_limits(-0.80, 0.80)
    
            # configure analog potentiometer for PID controller tuning
#           _cfg = [ 0, 330, 0.0, 1.0 ]
#           _apot = AnalogPotentiometer(_config, in_min=_cfg[0], in_max=_cfg[1], out_min=_cfg[2], out_max=_cfg[3], level=Level.INFO)
    
            _anlg_scaled_value = 0.0
            _last_scaled_value = 0.0
            _log.info('starting test...')
            _hz = 10
            _rate = Rate(_hz, Level.ERROR)
            while True:
                _port_motor.update_target_velocity()
                _stbd_motor.update_target_velocity()
#               _anlg_scaled_value = _apot.get_scaled_value()
                _dgtl_scaled_value = _dpot.get_scaled_value(False)
                if _dgtl_scaled_value != _last_scaled_value: # if not the same as last time
                    # math.isclose(3, 15, abs_tol=0.03 * 255) # 3% on a 0-255 scale
                    if isclose(_dgtl_scaled_value, 0.0, abs_tol=0.05 * 90):
                        _dpot.set_black()
#                       _motor_ctrl.set_motor_velocity(Orientation.PORT, 0.0)
#                       _motor_ctrl.set_motor_velocity(Orientation.STBD, 0.0)
                        _port_motor.target_velocity = 0.0
                        _stbd_motor.target_velocity = 0.0
                        _log.info(Fore.BLACK + Style.DIM + 'digital value: {:9.6f} (ZERO); analog: {:5.2f}'.format(_dgtl_scaled_value, _anlg_scaled_value))
                    else:
                        _dpot.set_rgb(_dpot.value)
#                       _motor_ctrl.set_motor_velocity(Orientation.PORT, _dgtl_scaled_value)
#                       _motor_ctrl.set_motor_velocity(Orientation.STBD, _dgtl_scaled_value)
                        _port_motor.target_velocity = _dgtl_scaled_value
                        _stbd_motor.target_velocity = _dgtl_scaled_value
                        _log.info(Fore.BLACK + Style.BRIGHT + 'digital value: {:9.6f}; analog: {:5.2f}'.format(_dgtl_scaled_value, _anlg_scaled_value))
                _last_scaled_value = _dgtl_scaled_value
                _rate.wait()
    
        _log.info('disabling motor controller...')
        _motor_ctrl.disable()
        _log.info('closing...')

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
    except DeviceNotFound as e:
        _log.error('no potentiometer found, exiting.')
        sys.exit(1)
    except Exception as e:
        _log.error('{} encountered, exiting: {}'.format(type(e), e))
        sys.exit(1)
    finally:
        _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
        _log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))
        sys.exit(0)

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
