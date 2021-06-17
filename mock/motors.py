#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-16
# modified: 2021-04-22
#

from threading import Thread
import asyncio
import random
import time
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.orient import Orientation, Speed, Direction
from core.event import Event
from core.slew import SlewLimiter
from mock.motor import Motor

# ..............................................................................
class Motors(object):
    '''
    A mocked dual motor controller with encoders.

    :param name:         the subscriber name (for logging)
    :param tb:           the ThunderBorg motor controller
    :param events:       the list of events used as a filter, None to set as cleanup task
    :param level:        the logging level 
    '''
    def __init__(self, config, tb, level=Level.INFO):
        self._log = Logger('motors', level)
        self._log.info('initialising motors...')
        if config is None:
            raise Exception('no config argument provided.')
        self._config = config
        if tb is None:
            raise Exception('no tb argument provided.')
        _tb = tb
        self._port_motor = Motor(self._config, _tb, Orientation.PORT, level)
        self._stbd_motor = Motor(self._config, _tb, Orientation.STBD, level)
        self._port_slew = SlewLimiter(self._config, 'slew-port', level)
        self._stbd_slew = SlewLimiter(self._config, 'slew-stbd', level)
        self._closed  = False
        self._enabled = False # used to be enabled by default
        # temporary until we move functionality to motors
        self._color         = Fore.MAGENTA
        self._loop_thread   = None
        self._loop_enabled  = False
#       self._port_velocity = 0
        self._stbd_velocity = 0
        self._increment     = 5
        self._max_velocity  = 100
        self._log.info('motors ready.')

    # ..........................................................................
    @property
    def name(self):
        return 'motors'

    # ..........................................................................
    def start_loop(self):
        '''
        Start the display loop.
        '''
        if self._loop_thread is None:
            self._loop_enabled = True
            self._loop_thread = Thread(name='display_loop', target=Motors._loop, args=[self, lambda: self._loop_enabled], daemon=True)
            self._loop_thread.start()
            self._log.info('clock enabled.')
        else:
            self._log.warning('cannot enable loop: thread already exists.')

    # ..........................................................................
    def stop_loop(self):
        '''
        Stop the display loop.
        '''
        if self._loop_enabled:
            self._loop_enabled = False
            self._loop_thread  = None
            self._log.info('loop disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def loop_is_running(self):
        return self._loop_enabled

    # ..........................................................................
    def _loop(self, f_is_enabled):
        '''
        The display loop, which executes while the f_is_enabled flag is True.
        '''
        while f_is_enabled():
            self._log.info('velocity:\t' + Fore.RED   + 'port: {:5.2f}\t'.format(self._port_motor.velocity) 
                                         + Fore.GREEN + 'stbd: {:5.2f}'.format(self._stbd_motor.velocity))
            time.sleep(1.0)
        self._log.info('exited display loop.')

    # ..........................................................................
    def get_motor(self, orientation):
        if orientation is Orientation.PORT:
            return self._port_motor
        else:
            return self._stbd_motor

    # ..........................................................................
    def velocity_event(self, payload):
        event = payload.event
        value = payload.value
        if event is Event.INCREASE_PORT_VELOCITY: # TODO
            self._increment_motor_velocity(Orientation.PORT, self._increment)
            self._log.info(self._color + Style.BRIGHT + '🈴👍 INCREASE PORT VELOCITY; velocity: {:d}'.format(self._port_motor.velocity))
            pass       
        elif event is Event.DECREASE_PORT_VELOCITY: # TODO
            self._increment_motor_velocity(Orientation.PORT, -1 * self._increment)
            self._log.info(self._color + Style.BRIGHT + '🈴👎 DECREASE PORT VELOCITY; velocity: {:d}'.format(self._port_motor.velocity))
            pass       
        elif event is Event.INCREASE_STBD_VELOCITY: # TODO
            self._increment_motor_velocity(Orientation.STBD, self._increment)
            self._log.info(self._color + Style.BRIGHT + '🈯👍 INCREASE STBD VELOCITY; velocity: {:d}'.format(self._stbd_motor.velocity))
            pass       
        elif event is Event.DECREASE_STBD_VELOCITY: # TODO
            self._increment_motor_velocity(Orientation.STBD, -1 * self._increment)
            self._log.info(self._color + Style.BRIGHT + '🈯👎 DECREASE STBD VELOCITY; velocity: {:d}'.format(self._stbd_motor.velocity))
            pass       
        elif event is Event.DECREASE_VELOCITY: 
            self._increment_motor_velocity(Orientation.PORT, -1 * self._increment)
            self._increment_motor_velocity(Orientation.STBD, -1 * self._increment)
            self._log.info(self._color + Style.BRIGHT + '👎 DECREASE VELOCITY;\t'
                    + Fore.RED + 'port: {:d};\t'.format(self._port_motor.velocity) 
                    + Fore.GREEN + 'stbd: {:d}'.format(self._stbd_motor.velocity))
        elif event is Event.INCREASE_VELOCITY: 
            self._increment_motor_velocity(Orientation.PORT, self._increment)
            self._increment_motor_velocity(Orientation.STBD, self._increment)
            self._log.info(self._color + Style.BRIGHT + '👍 INCREASE VELOCITY;\t'
                    + Fore.RED + 'port: {:d};\t'.format(self._port_motor.velocity) 
                    + Fore.GREEN + 'stbd: {:d}'.format(self._stbd_motor.velocity))
        else:
            self._log.warning('🍑 unrecognised event {}'.format(event.description))

    # ..........................................................................
    def chadburn_event(self, event):
        _speed = None
        _direction = None
        if event is Event.FULL_ASTERN:
            _speed = Speed.STOP
            self._log.info(self._color + '🐢 STOP.' + Style.RESET_ALL)
        elif event is Event.FULL_ASTERN:
            _direction = Direction.ASTERN
            _speed = Speed.FULL
            self._log.info(self._color + '🐢 FULL ASTERN.' + Style.RESET_ALL)
        elif event is Event.HALF_ASTERN:
            _direction = Direction.ASTERN
            _speed = Speed.HALF
            self._log.info(self._color + '🐢 HALF ASTERN.' + Style.RESET_ALL)
        elif event is Event.SLOW_ASTERN:
            _direction = Direction.ASTERN
            _speed = Speed.SLOW
            self._log.info(self._color + '🐢 SLOW ASTERN.' + Style.RESET_ALL)
        elif event is Event.DEAD_SLOW_ASTERN:
            _direction = Direction.ASTERN
            _speed = Speed.DEAD_SLOW
            self._log.info(self._color + '🐢 DEAD SLOW ASTERN.' + Style.RESET_ALL)
        elif event is Event.DEAD_SLOW_AHEAD:
            _direction = Direction.AHEAD
            _speed = Speed.DEAD_SLOW
            self._log.info(self._color + '🐰 DEAD SLOW AHEAD.' + Style.RESET_ALL)
        elif event is Event.SLOW_AHEAD:
            _direction = Direction.AHEAD
            _speed = Speed.SLOW
            self._log.info(self._color + '🐰 SLOW AHEAD.' + Style.RESET_ALL)
        elif event is Event.HALF_AHEAD:
            _direction = Direction.AHEAD
            _speed = Speed.HALF
            self._log.info(self._color + '🐰 HALF AHEAD.' + Style.RESET_ALL)
        elif event is Event.FULL_AHEAD:
            _direction = Direction.AHEAD
            _speed = Speed.FULL
            self._log.info(self._color + ' FULL AHEAD.' + Style.RESET_ALL)
        else:
            self._log.warning('🍑 unrecognised event {}'.format(event.description))
            return
        # set speed value based on direction
        self._log.info(self._color + '🐰🐢 set chadburn velocity: {}  {}.'.format(_speed.label, _direction) + Style.RESET_ALL)
        _value = _speed.value if _direction is Direction.AHEAD else -1 * _speed.value
        self._set_motor_velocity(Orientation.PORT, _value)
        self._set_motor_velocity(Orientation.STBD, _value)

    # ..........................................................................
    def stop_event(self, event):
        if event is Event.HALT: # TODO
            self._log.info(self._color + '🛑 HALT.' + Style.RESET_ALL)
        elif event is Event.STOP: # TODO
            self._log.info(self._color + '🛑 STOP.' + Style.RESET_ALL)
        elif event is Event.BRAKE: # TODO
            self._log.info(self._color + '🛑 BRAKE.' + Style.RESET_ALL)
        self._port_motor.velocity = 0
        self._stbd_motor.velocity = 0

    # ..........................................................................
    def _update_value(self, value, increment):
        value += increment
        if value > self._max_velocity:
            value = self._max_velocity
        elif value < -1 * self._max_velocity:
            value = -1 * self._max_velocity
        return value

    # ..........................................................................
    def _increment_motor_velocity(self, orientation, increment):
        '''
        Increment the velocity of the specified motor by the supplied increment
        (which can be a positive or negative value).
        '''
        if orientation is Orientation.PORT:
            _port_velocity = self._port_motor.velocity
            _updated_port_velocity = self._update_value(_port_velocity, increment)
            self._port_motor.velocity = _updated_port_velocity
            self._log.info(Fore.RED + Style.NORMAL + '🍿 increment port motor velocity: {:5.2f} + {:5.2f} -▶ {:<5.2f}'.format(_port_velocity, increment, _updated_port_velocity))
        else:
            _stbd_velocity = self._stbd_motor.velocity
            _updated_stbd_velocity = self._update_value(_stbd_velocity, increment)
            self._stbd_motor.velocity = _updated_stbd_velocity
            self._log.info(Fore.RED + Style.NORMAL + '🍿 increment stbd motor velocity: {:5.2f} + {:5.2f} -▶ {:<5.2f}'.format(_stbd_velocity, increment, _updated_stbd_velocity))

    # ..........................................................................
    def _set_motor_velocity(self, orientation, velocity):
        '''
        Set the target velocity of the specified motor.
        '''
        if orientation is Orientation.PORT:
            _port_velocity = self._port_motor.velocity
            self._port_motor.velocity = velocity
            self._log.info(Fore.RED + Style.NORMAL + '🍿 set port motor velocity: {:5.2f} -▶ {:<5.2f}'.format(_port_velocity, velocity))
        else:
            _stbd_velocity = self._stbd_motor.velocity
            self._stbd_motor.velocity = velocity
            self._log.info(Fore.RED + Style.NORMAL + '🍿 set stbd motor velocity: {:5.2f} -▶ {:<5.2f}'.format(_stbd_velocity, velocity))

    # ..........................................................................
    def _change_speed(self, orientation, change):
        '''
        Set the power sent to the specified motor.
        '''
        if orientation is Orientation.PORT:
            _port_power = self._port_motor.get_current_power_level()
            _updated_port_power = _port_power + change
            self._port_motor.set_motor_power(_updated_port_power)
            _port_power = self._port_motor.get_current_power_level()
            self._log.info(Fore.RED + Style.NORMAL + 'port motor power: {:5.2f} + {:5.2f} -▶ {:<5.2f}'.format(_port_power, change, _updated_port_power))
        else:
            _stbd_power = self._stbd_motor.get_current_power_level()
            _updated_stbd_power = _stbd_power + change
            self._stbd_motor.set_motor_power(_updated_stbd_power)
            _stbd_power = self._stbd_motor.get_current_power_level()
            self._log.info(Fore.GREEN + Style.NORMAL + 'stbd motor power: {:5.2f} + {:5.2f} -▶ {:<5.2f}'.format(_stbd_power, change, _updated_stbd_power))

    # ..........................................................................
    def halt(self):
        '''
        Quickly (but not immediately) stops both motors.
        '''
        self._log.info('halting...')
        if not self.is_stopped():
            self._port_motor.stop()
            self._stbd_motor.stop()
#           _tp = Thread(name='halt-port', target=self.processStop, args=(Event.HALT, Orientation.PORT))
#           _ts = Thread(name='hapt-stbd', target=self.processStop, args=(Event.HALT, Orientation.STBD))
#           _tp.start()
#           _ts.start()
            self._log.info('halted.')
        else:
            self._log.debug('already halted.')
        return True

    # ..........................................................................
    def brake(self):
        '''
        Slowly coasts both motors to a stop.
        '''
        self._log.info('braking...')
        if not self.is_stopped():
            self._port_motor.stop()
            self._stbd_motor.stop()
#           _tp = Thread(name='brake-port', target=self.processStop, args=(Event.BRAKE, Orientation.PORT))
#           _ts = Thread(name='brake-stbd', target=self.processStop, args=(Event.BRAKE, Orientation.STBD))
#           _tp.start()
#           _ts.start()
            self._log.info('braked.')
        else:
            self._log.warning('already braked.')
        return True

    # ..........................................................................
    def stop(self):
        '''
        Stops both motors immediately, with no slewing.
        '''
        self._log.info('stopping...')
        if not self.is_stopped():
            self._port_motor.stop()
            self._stbd_motor.stop()
            self._log.info('stopped.')
        else:
            self._log.warning('already stopped.')
        return True

    # ..........................................................................
    def is_stopped(self):
        return self._port_motor.is_stopped() and self._stbd_motor.is_stopped()

    # ..........................................................................
    def is_in_motion(self):
        '''
        Returns true if either motor is moving.
        '''
        return self._port_motor.is_in_motion() or self._stbd_motor.is_in_motion()

    # ..........................................................................
    def enable(self):
        '''
        Enables the motors. This issues a warning if already enabled, but no
        harm is done in calling it repeatedly.
        '''
        if self._enabled:
            self._log.warning('already enabled.')
        if not self._port_motor.enabled:
            self._port_motor.enable()
        if not self._stbd_motor.enabled:
            self._stbd_motor.enable()
        self._enabled = True
        self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        '''
        Disable the motors, halting first if in motion.
        '''
        if self._enabled:
            self._log.info('disabling...')
            self._enabled = False
            if self.is_in_motion(): # if we're moving then halt
                self._log.warning('event: motors are in motion (halting).')
                self.halt()
            self._port_motor.disable()
            self._stbd_motor.disable()
            self._log.info('disabling pigpio...')
            self._log.info('disabled.')
        else:
            self._log.debug('already disabled.')

    # ..........................................................................
    def close(self):
        '''
        Halts, turn everything off and stop doing anything.
        '''
        if not self._closed:
            if self._enabled:
                self.disable()
            self._log.info('closing...')
            self._port_motor.close()
            self._stbd_motor.close()
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.debug('already closed.')

    # ..........................................................................
    @staticmethod
    def cancel():
        self._log.info('cancelling motors...')
#       Motor.cancel()

#EOF
