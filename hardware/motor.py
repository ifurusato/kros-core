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
from hardware.slew import SlewLimiter
from hardware.jerk import JerkLimiter

# ..............................................................................
class Motor(Component):
    '''
    Controls a motor that uses a Hall Effect encoder to determine the robot's
    velocity and distance traveled. This uses a mock when the motor controller
    is unavailable.

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
        self._log = Logger('motor:{}'.format(orientation.label), level)
        Component.__init__(self, self._log, suppressed=False, enabled=False)
        self._log.info('initialising {} motor with {} as motor controller...'.format(orientation, type(self._tb)))
        # configuration
        # get motors configuration section (we don't actually use this in the mock)
        _cfg = config['kros'].get('motors')
        self._motor_power_limit = _cfg.get('motor_power_limit') # power limit to motor
        self._steps             = 0     # step counter
        self._max_power         = 0.0   # capture maximum power applied
        self._max_driving_power = 0.0   # capture maximum adjusted power applied
        self._max_power_ratio   = 0.0   # will be set by MotorConfigurer
        self._velocity          = 0     # currently a proxy for actual velocity
        self._target_velocity   = 0.0   # the target velocity of the motor
        _suppress_slew_limiter  = _cfg.get('suppress_slew_limiter')
        _enable_slew_limiter    = _cfg.get('enable_slew_limiter')
        self._slew_limiter      = SlewLimiter(config, orientation, suppressed=_suppress_slew_limiter, enabled=_enable_slew_limiter, level=level)
        _suppress_jerk_limiter  = _cfg.get('suppress_jerk_limiter')
        _enable_jerk_limiter    = _cfg.get('enable_jerk_limiter')
        self._jerk_limiter      = JerkLimiter(config, orientation, suppressed=_suppress_jerk_limiter, enabled=_enable_jerk_limiter, level=level) 
        self._log.info('ready.')

    # ..........................................................................
    @property
    def slew_limiter(self):
        return self._slew_limiter

    # ..........................................................................
    @property
    def jerk_limiter(self):
        return self._jerk_limiter

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

    # ..........................................................................
    @property
    def target_velocity(self):
        return self._target_velocity

    # ..........................................................................
    @target_velocity.setter
    def target_velocity(self, target_velocity):
        self._target_velocity = target_velocity

    # ..............................................................................
    @property
    def steps(self):
        return self._steps

    # ..............................................................................
    def reset_steps(self):
        self._steps = 0

    # max power ratio ..............................................................

    @property
    def max_power_ratio(self):
        return self._max_power_ratio

    @max_power_ratio.setter
    def max_power_ratio(self, max_power_ratio):
        self._max_power_ratio = max_power_ratio
        self._log.info(Fore.YELLOW + 'motor power limit: {:5.2f}'.format(self._motor_power_limit))

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
    def enable(self):
        if not self.enabled:
            Component.enable(self)
#       self._slew_limiter.enable()

    # ..........................................................................
    def disable(self):
        if self.enabled:
            Component.disable(self)
#       self._slew_limiter.disable()

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
    def update_motor_velocity(self):
        '''
        If the current velocity doesn't match the target, set the target
        velocity and motor power as an attempt to align them.
        '''
        if self.velocity != self.target_velocity:
            self.set_motor_velocity(self.target_velocity)

    # ..........................................................................
    def set_motor_velocity(self, target_velocity):
        '''
        Set the target velocity and motor power.
        '''
        self._log.info(Fore.BLACK + '🌺 set {} motor target velocity: {:5.2f} ➔ {:<5.2f}'.format(self._orientation, self.velocity, target_velocity))
        self.target_velocity = self._slew_limiter.limit(self.velocity, target_velocity)
        # TEMP
        if self.target_velocity is None:
            raise Exception('null self.target_velocity')
        # translate velocity to power...
        _power = self._convert_to_power(self.target_velocity)
        self.set_motor_power(_power)

    # ..........................................................................
    def _convert_to_power(self, velocity):
        '''
        TODO done by the Motor class or PID controller?
        90 becomes 0.9
        '''
        if velocity < 0:
            # with limit at -0.99, min would always be -0.99
            return max( velocity / 100.0, -1 * self._motor_power_limit )
        else:
            # with limit at 0.99, min will be always less than 0.99
            return min( velocity / 100.0, self._motor_power_limit )

    # ..........................................................................
    def set_motor_power(self, target_power):
        '''
        Sets the motor power to a number between -1.0 to 1.0, with the actual
        limits set by the max_power_ratio, which alters the value to match
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

        # okay, let's go .........................
        _driving_power = float(target_power * self.max_power_ratio)
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
