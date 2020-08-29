#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

# Import library functions we need
import os, sys, signal, time, traceback
from threading import Thread
from fractions import Fraction
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: sudo pip3 install numpy")

from lib.devnull import DevNull
from lib.enums import Rotation, Direction, Speed, Velocity, SlewRate, Orientation
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.motor import Motor
from lib.motors import Motors
from lib.filewriter import FileWriter

_port_motor = None
_stbd_motor = None

def quit():
    if _port_motor:
        _port_motor.halt()
    if _stbd_motor:
        _stbd_motor.halt()
    Motor.cancel()
    sys.stderr = DevNull()
    print('exit.')
    sys.exit(0)

# exception handler ........................................................
def signal_handler(signal, frame):
    print('Ctrl-C caught: exiting...')
    quit()

def get_forward_steps():
    _rotations = 5
    _forward_steps_per_rotation = 494
    _forward_steps = _forward_steps_per_rotation * _rotations
    return _forward_steps

def _spin(motors, rotation, f_is_enabled):
    print('motors spin {}.'.format(rotation))

    _port_motor = motors.get_motor(Orientation.PORT)
    _port_pid   = _port_motor.get_pid_controller()
    _stbd_motor = motors.get_motor(Orientation.STBD)
    _stbd_pid   = _stbd_motor.get_pid_controller()

    _forward_steps = get_forward_steps()
    if rotation is Rotation.CLOCKWISE:
        _tp = Thread(target=_port_pid.step_to, args=(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps, f_is_enabled))
        _ts = Thread(target=_stbd_pid.step_to, args=(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps, f_is_enabled))
#           self._port_pid.step_to(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps, f_is_enabled)
#           self._stbd_pid.step_to(Velocity.TWO_THIRDS, Direction.REVERSE, SlewRate.SLOW, _forward_steps, f_is_enabled)
    else: # COUNTER_CLOCKWISE 
        _tp = Thread(target=_port_pid.step_to, args=(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps, f_is_enabled))
        _ts = Thread(target=_stbd_pid.step_to, args=(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps, f_is_enabled))
#           self._port_pid.step_to(Velocity.TWO_THIRDS, Direction.REVERSE, SlewRate.SLOW, _forward_steps, f_is_enabled)
#           self._stbd_pid.step_to(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps, f_is_enabled)
    _tp.start()
    _ts.start()
    _tp.join()
    _ts.join()
#       self.print_current_power_levels()
    print('complete: motors spin {}.'.format(rotation))

def is_calibrated_trigger():
    time.sleep(5.0)
    return True

# ..............................................................................
def main():
    '''
         494 encoder steps per rotation (maybe 493)
         218mm wheel circumference
         1 wheel rotation = 218mm
         2262 steps per meter
         2262 steps per second = 1 m/sec
         2262 steps per second = 100 cm/sec

         Notes:
         1 rotation = 218mm = 493 steps
    '''
    try:

#       signal.signal(signal.SIGINT, signal_handler)

        _wheel_circumference_mm = 218
        _forward_steps_per_rotation = 494
        _forward_steps = get_forward_steps()

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _motors = Motors(_config, None, None, Level.INFO)
        # disable port motor ............................
        _port_motor = _motors.get_motor(Orientation.PORT)
        _port_motor.set_motor_power(0.0)

        _stbd_motor = _motors.get_motor(Orientation.STBD)

        _spin(_motors, Rotation.CLOCKWISE, lambda: not is_calibrated_trigger() ) 

#       _pid = _stbd_motor.get_pid_controller()

#       _filewriter = FileWriter(_config, 'pid', Level.INFO)
#       _pid.set_filewriter(_filewriter)

#       _rotations = 5
#       _forward_steps = _forward_steps_per_rotation * _rotations
#       print(Fore.YELLOW + Style.BRIGHT + 'starting forward motor test for steps: {:d}.'.format(_forward_steps) + Style.RESET_ALL)
#       _pid.step_to(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps)

#       _rotations = 3
#       _forward_steps = _forward_steps_per_rotation * _rotations
#       _pid.step_to(Velocity.HALF, Direction.FORWARD, SlewRate.SLOW, _forward_steps)

#       _pid.close_filewriter()
#       _stbd_motor.brake()
#       _stbd_motor.close()


        print(Fore.YELLOW + Style.BRIGHT + 'A. motor test complete; intended: {:d}; actual steps: {}.'.format(_forward_steps, _stbd_motor.get_steps()) + Style.RESET_ALL)

    except KeyboardInterrupt:
        print(Fore.YELLOW + Style.BRIGHT + 'B. motor test complete; intended: {:d}; actual steps: {}.'.format(_forward_steps, _stbd_motor.get_steps()) + Style.RESET_ALL)
        _stbd_motor.halt()
        quit()
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error in PID controller: {}'.format(e))
        traceback.print_exc(file=sys.stdout)
    finally:
        print(Fore.YELLOW + Style.BRIGHT + 'C. finally.')
#       _stbd_motor.halt()

if __name__== "__main__":
    main()


#EOF
