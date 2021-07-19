#!/usr/bin/env python3 # -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-18
# modified: 2021-06-29
#

import sys, itertools, time
from colorama import init, Fore, Style
init()

from core.logger import Level, Logger
from core.component import Component
from core.orient import Orientation
from hardware.jerk import JerkLimiter

# ..............................................................................
class Motor(Component):
    '''
    Mocks control over a motor that uses a Hall Effect encoder
    to determine the robot's velocity and distance traveled.

    This uses the kros:motors: section of the configuration.

    :param config:      application configuration
    :param tb:          reference to the mocked ThunderBorg motor controller
    :param orientation: motor orientation
    :param level:       log level
    '''
    def __init__(self, config, tb, orientation, level=Level.INFO):
        if config is None:
            raise ValueError('null config argument.')
        if tb is None:
            raise ValueError('null thunderborg argument.')
        self._tb = tb
        self._orientation = orientation
        self._log = Logger('mock-motor:{}'.format(orientation.label), level)
        Component.__init__(self, self._log, suppressed=False, enabled=False)
        self._log.info('initialising {} motor with {} as motor controller...'.format(orientation, type(self._tb)))
        # configuration
        # get motors configuration section (we don't actually use this in the mock)
        _cfg = config['kros'].get('motors')
        self._motor_power_limit = _cfg.get('motor_power_limit')  # power limit to motor
        self._motor_delta_limit = _cfg.get('motor_delta_limit')  # change limit to motor
        self._log.info('motor power limit: {:5.2f}'.format(self._motor_power_limit))
        self._steps             = 0     # step counter
        self._max_power         = 0.0   # capture maximum power applied
        self._max_driving_power = 0.0   # capture maximum adjusted power applied
        self._max_power_ratio   = 1.0   # will be set by MotorConfigurer
        self._velocity          = 0     # currently a proxy for actual velocity
        self._jerk_limiter      = JerkLimiter(config, orientation, self._motor_power_limit, level) 
#       self._jerk_limiter      = JerkLimiter(config, orientation, level) 
        self._log.info('ready.')

    # ..........................................................................
    @property
    def orientation(self):
        '''
        Returns the orientation of this motor.
        '''
        return self._orientation

    # ..........................................................................
    @property
    def velocity(self):
        return self._velocity

    # ..........................................................................
    @velocity.setter
    def velocity(self, velocity):
        self._velocity = velocity

    # ..............................................................................
    @property
    def steps(self):
        return self._steps

    # ..............................................................................
    def reset_steps(self):
        self._steps = 0

    # ..............................................................................
    def set_max_power_ratio(self, max_power_ratio):
        self._max_power_ratio = max_power_ratio

    # ..............................................................................
    def get_max_power_ratio(self):
        return self._max_power_ratio

    # ..............................................................................
    def _callback_step_count(self, pulse):
        '''
        This callback is used to capture encoder steps.
        '''
        if self._orientation is Orientation.PORT:
            self._steps = self._steps - pulse
        else:
            self._steps = self._steps + pulse

    # ..........................................................................
    def disable(self):
        if self.enabled:
            Component.disable(self)

    # ..........................................................................
    def close(self):
        if self.enabled:
            self.disable()
        if self._max_power > 0 or self._max_driving_power > 0:
            self._log.info('on closing: max power: {:>5.2f}; max adjusted power: {:>5.2f}.'.format(self._max_power, self._max_driving_power))
        # just do it
        if self._orientation is Orientation.PORT:
            self._log.info(Fore.YELLOW + 'set motor PORT to zero.')
            self._tb.SetMotor1(0.0)
        else:
            self._log.info(Fore.YELLOW + 'set motor STBD to zero.')
            self._tb.SetMotor2(0.0)
        self._log.info('closed.')

    # ..........................................................................
    @staticmethod
    def cancel():
        '''
        Stop both motors immediately. This can be called from either motor.
        '''
        print('motors cancelled.')

    # ..........................................................................
    def is_in_motion(self):
        '''
        Returns True if the motor is moving.
        '''
        return self.current_power > 0.0

    # ..........................................................................
    def set_motor_power(self, target_power):
        '''
        Sets the motor power to a number between -1.0 to 1.0, with the actual
        limits set by the _max_power_ratio, which alters the value to match
        the power/motor voltage ratio.

        :param target_power:  the target motor power
        '''
        if not self.enabled and target_power > 0.0: # though we'll let the power be set to zero
            self._log.warning('motor disabled, ignoring setting of {:<5.2f}'.format(target_power))
            return
        _max = 0.9 # was 0.3?

#       self._motor_delta_limit

        _current_power = self.current_power
        if self.orientation is Orientation.PORT and False:
            # TEMP (port only) evaluate change...
            _diff = target_power - _current_power
            if _diff < _max:
                self._log.info(Fore.YELLOW + '😨 current: {:4.2f}; target: {:4.2f}; diff: {:4.2f}; max: {:4.2f}'.format(
                        _current_power, target_power, _diff, _max))
            elif _diff == 0:
                self._log.info(Fore.BLACK + '😨 current: {:4.2f}; target: {:4.2f}; diff: {:4.2f}; max: {:4.2f}'.format(
                        _current_power, target_power, _diff, _max))
            elif _diff < 0:
                self._log.info(Fore.RED + '😨 current: {:4.2f}; target: {:4.2f}; diff: {:4.2f}; max: {:4.2f}'.format(
                        _current_power, target_power, _diff, _max))
            else:
                self._log.info(Fore.GREEN + '😨 current: {:4.2f}; target: {:4.2f}; diff: {:4.2f}; max: {:4.2f}'.format(
                        _current_power, target_power, _diff, _max))

        target_power = self._jerk_limiter.limit(self.current_power, target_power)
        self._log.debug('current: {:4.2f}; target: {:4.2f}'.format(self.current_power, target_power))

        # safety checks ..........................
        if target_power > self._motor_power_limit:
            self._log.error('motor power too high: {:>5.2f}; limit: {:>5.2f}'.format(target_power, self._motor_power_limit))
            target_power = self._motor_power_limit
        elif target_power < ( -1.0 * self._motor_power_limit ):
            self._log.error('motor power too low: {:>5.2f}; limit: {:>5.2f}'.format( target_power, ( -1.0 * self._motor_power_limit )))
            target_power = -1.0 * self._motor_power_limit
        else:
            self._log.debug('ok- motor power: {:>5.2f}; limit: {:>5.2f}'.format( target_power, self._motor_power_limit ))
#
#       if abs(_current_power - target_power) > _max and _current_power > 0.0 and target_power < 0:
#           self._log.error('cannot perform positive-negative power jump: {:>5.2f} to {:>5.2f}.'.format(_current_power, target_power))
#           return
#       elif abs(_current_power - target_power) > _max and _current_power < 0.0 and target_power > 0:
#           self._log.error('cannot perform negative-positive power jump: {:>5.2f} to {:>5.2f}.'.format(_current_power, target_power))
#           return

        # okay, let's go .........................
        _driving_power = float(target_power * self._max_power_ratio)
        self._max_power = max(target_power, self._max_power)
        self._max_driving_power = max(abs(_driving_power), self._max_driving_power)
        # display actual power to motor
#       self._log.info(Fore.MAGENTA + Style.BRIGHT + 'power argument: {:>5.2f}'.format(target_power) + Style.NORMAL \
#               + '\tcurrent power: {:>5.2f}; driving power: {:>5.2f}.'.format(_current_power, _driving_power))
        if self._orientation is Orientation.PORT:
            self._tb.SetMotor1(_driving_power)
        else:
            self._tb.SetMotor2(_driving_power)

    # ................................
    @property
    def current_power(self):
        '''
         Makes a best attempt at getting the current power value from the motors.
        '''
        value = None
        count = 0
        if self._orientation is Orientation.PORT:
            while value == None and count < 20:
                count += 1
                value = self._tb.GetMotor1()
                time.sleep(0.005)
        else:
            while value == None and count < 20:
                count += 1
                value = self._tb.GetMotor2()
                time.sleep(0.005)
        if value == None:
            return 0.0
        else:
            return value

    # ..........................................................................
    @property
    def stopped(self):
        '''
         Returns True if the motor is entirely stopped.
        '''
        return ( self.current_power == 0.0 )

    def stop(self):
        '''
        Stops the motor immediately.
        '''
        self._log.info('stop.')
        if self._orientation is Orientation.PORT:
            self._tb.SetMotor1(0.0)
        else:
            self._tb.SetMotor2(0.0)
        pass

#EOF
