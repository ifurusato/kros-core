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

import asyncio
import random
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.orient import Orientation
from core.event import Event
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
        self._closed  = False
        self._enabled = False # used to be enabled by default
        # temporary until we move functionality to motors
        self._color         = Fore.MAGENTA
        self._port_velocity = 0
        self._stbd_velocity = 0
        self._increment     = 5
        self._max_velocity  = 100
        self._log.info('motors ready.')

    # ..........................................................................
    @property
    def name(self):
        return 'motors'

    # ..........................................................................
    def get_motor(self, orientation):
        if orientation is Orientation.PORT:
            return self._port_motor
        else:
            return self._stbd_motor

    # ..........................................................................
    def velocity_event(self, event):
        if event is Event.INCREASE_PORT_VELOCITY: # TODO
            self._port_velocity = self._update_value(self._port_velocity, self._increment)
            self._log.info(self._color + Style.BRIGHT + '🈴👍 INCREASE PORT VELOCITY; velocity: {:d}'.format(self._port_velocity) + Style.RESET_ALL)
            pass       
        elif event is Event.DECREASE_PORT_VELOCITY: # TODO
            self._port_velocity = self._update_value(self._port_velocity, -1 * self._increment)
            self._log.info(self._color + Style.BRIGHT + '🈴👎 DECREASE PORT VELOCITY; velocity: {:d}'.format(self._port_velocity) + Style.RESET_ALL)
            pass       
        elif event is Event.INCREASE_STBD_VELOCITY: # TODO
            self._stbd_velocity = self._update_value(self._stbd_velocity, self._increment)
            self._log.info(self._color + Style.BRIGHT + '🈯👍 INCREASE STBD VELOCITY; velocity: {:d}'.format(self._stbd_velocity) + Style.RESET_ALL)
            pass       
        elif event is Event.DECREASE_STBD_VELOCITY: # TODO
            self._stbd_velocity = self._update_value(self._stbd_velocity, -1 * self._increment)
            self._log.info(self._color + Style.BRIGHT + '🈯👎 DECREASE STBD VELOCITY; velocity: {:d}'.format(self._stbd_velocity) + Style.RESET_ALL)
            pass       

    # ..........................................................................
    def stop_event(self, event):
        if event is Event.HALT: # TODO
            self._log.info(self._color + '🛑 HALT.' + Style.RESET_ALL)
        elif event is Event.STOP: # TODO
            self._log.info(self._color + '🛑 STOP.' + Style.RESET_ALL)
        elif event is Event.BRAKE: # TODO
            self._log.info(self._color + '🛑 BRAKE.' + Style.RESET_ALL)
        self._port_velocity = 0
        self._stbd_velocity = 0

    # ..........................................................................
    def _update_value(self, value, increment):
        value += increment
        if value > self._max_velocity:
            value = self._max_velocity
        elif value < -1 * self._max_velocity:
            value = -1 * self._max_velocity
        return value
    # ..........................................................................
    def change_speed(self, orientation, change):
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
