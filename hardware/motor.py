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
from core.speed import Speed
from core.message_bus import MessageBus
from hardware.pid_ctrl import PIDController
from hardware.slew import SlewLimiter
from hardware.jerk import JerkLimiter
from mock.velocity import MockVelocity
from hardware.velocity import Velocity

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Motor(Component):
    '''
    Controls a motor that uses a Hall Effect encoder to determine the robot's
    velocity and distance traveled. This uses a mock when the motor controller
    is unavailable.

    This Motor class takes an input as velocity (-100.0 to 100.0) which is
    pre-processed by a SlewLimiter (which buffers sudden changes to the target
    velocity), then is passed along to a PIDController, which converts the
    velocity to power (-1.0 to 1.0), which is then passed through a JerkLimiter
    to avoid sudden (and potentially dangerous) changes to the motor. All three
    are optional; when the PIDController is disabled a velocity-to-power
    dual-axis proportional interpolating function is used.

    This uses the kros:motor: section of the configuration.

    :param config:      application configuration
    :param tb:          reference to the mocked ThunderBorg motor controller
    :param orientation: motor orientation
    :param level:       log level
    '''
    def __init__(self, config, tb, message_bus, orientation, level=Level.INFO):
        if config is None:
            raise ValueError('null config argument.')
        if tb is None:
            raise ValueError('null thunderborg argument.')
        self._tb = tb
        if not isinstance(message_bus, MessageBus):
            raise ValueError('wrong type for message bus argument: {}'.format(type(message_bus)))
        self._message_bus = message_bus
        self._orientation = orientation
        self._log = Logger('motor:{}'.format(orientation.label), level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        self._log.info('initialising {} motor with {} as motor controller...'.format(orientation.name, type(self._tb).__name__))
        # configuration ..............................................
        _cfg = config['kros'].get('motor')
        self._max_velocity       = _cfg.get('maximum_velocity') # limit to motor velocity
        self._log.info('max velocity:\t{:<5.2f}'.format(self._max_velocity))
        self._velocity_clip = lambda n: ( -1.0 * self._max_velocity ) if n <= ( -1.0 * self._max_velocity ) \
                else self._max_velocity if n >= self._max_velocity \
                else n
        self._motor_power_limit = _cfg.get('motor_power_limit') # power limit to motor
        self._log.info('motor power limit: {:<5.2f}'.format(self._motor_power_limit))
        self._power_clip = lambda n: ( -1.0 * self._motor_power_limit ) if n <= ( -1.0 * self._motor_power_limit ) \
                else self._motor_power_limit if n >= self._motor_power_limit \
                else n
        self.__callbacks         = []
        self.__steps             = 0     # step counter
        self.__max_applied_power = 0.0   # capture maximum power applied
        self.__max_power_ratio   = 0.0   # will be set by MotorConfigurer
        self.__target_velocity   = 0.0   # the target velocity of the motor
        self._decoder            = None  # motor encoder
        self._slew_limiter       = None
        self._jerk_limiter       = None
        # slew limiter ...............................................
        _suppress_slew_limiter   = _cfg.get('suppress_slew_limiter')
        _enable_slew_limiter     = _cfg.get('enable_slew_limiter')
#       if not _suppress_slew_limiter and _enable_slew_limiter:
        self._slew_limiter       = SlewLimiter(config, orientation, suppressed=_suppress_slew_limiter, enabled=_enable_slew_limiter, level=level)
        # provides closed loop velocity feedback .....................
        self._using_mocks = config['kros'].get('arguments').get('using_mocks')
        if self._using_mocks:
            self._log.info(Fore.YELLOW + 'using mocks: {}'.format(self._using_mocks))
            self._velocity       = MockVelocity(orientation, level=level)
#           raise Exception('using mocked velocity.')
        else:
            self._velocity       = Velocity(config, self, level=level)
            self._velocity.enable()
        # pid controller .............................................
        _suppress_pid_controller = _cfg.get('suppress_pid_controller')
        _enable_pid_controller   = _cfg.get('enable_pid_controller')
        self._pid_controller     = PIDController(config, self._message_bus, self, suppressed=_suppress_pid_controller, enabled=_enable_pid_controller, level=level)
        # jerk limiter ...............................................
        _suppress_jerk_limiter   = _cfg.get('suppress_jerk_limiter')
        _enable_jerk_limiter     = _cfg.get('enable_jerk_limiter')
#       if not _suppress_jerk_limiter and _enable_jerk_limiter:
        self._jerk_limiter       = JerkLimiter(config, orientation, suppressed=_suppress_jerk_limiter, enabled=_enable_jerk_limiter, level=level)
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_callback(self, callback):
        '''
        Used by the Velocity class to obtain a callback on the motor loop.
        '''
        self.__callbacks.append(callback)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def orientation(self):
        '''
        Returns the orientation of this motor.
        '''
        return self._orientation

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def max_velocity(self):
        return self._max_velocity

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def slew_limiter(self):
        '''
        Returns the slew limiter used by this motor.
        This should be used only to obtain information, not for control.
        '''
        return self._slew_limiter

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def pid_controller(self):
        '''
        Returns the PID controller used by this motor.
        This should be used only to obtain information, not for control.
        '''
        return self._pid_controller

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def jerk_limiter(self):
        '''
        Returns the jerk limiter used by this motor.
        This should be used only to obtain information, not for control.
        '''
        return self._jerk_limiter

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def decoder(self):
        return self._decoder

    @decoder.setter
    def decoder(self, decoder):
        self._decoder = decoder

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def velocity(self):
        return self._velocity.value

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def target_velocity(self):
        '''
        Return the current internal target velocity of the Motor.
        '''
        return self.__target_velocity

    @target_velocity.setter
    def target_velocity(self, target_velocity):
        '''
        Set the target velocity of the Motor.
        '''
        if not isinstance(target_velocity, float):
            raise ValueError('expected float, not {}'.format(type(target_velocity)))
#       self._log.debug('set target velocity: {:5.2f} of {} motor.'.format(target_velocity, self._orientation.name))
        self.__target_velocity = target_velocity
        if self._using_mocks:
            self._velocity.velocity = target_velocity
#           raise Exception('using velocity mock!')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def steps(self):
        return self.__steps

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def reset_steps(self):
        self.__steps = 0

    # max power rate ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def max_power_ratio(self):
        return self.__max_power_ratio

    @max_power_ratio.setter
    def max_power_ratio(self, max_power_ratio):
        self.__max_power_ratio = max_power_ratio
        self._log.info(Fore.YELLOW + 'maximum power ratio: {:<5.2f}'.format(self.__max_power_ratio))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _callback_step_count(self, pulse):
        '''
        This callback is used to capture encoder steps.
        '''
        if self._orientation is Orientation.PORT:
            self.__steps = self.__steps + pulse
        else:
            self.__steps = self.__steps - pulse

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def is_in_motion(self):
        '''
        Returns True if the motor is moving.
        '''
        return self.current_power > 0.0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def update_target_velocity(self):
        '''
        If the current velocity doesn't match the target, set the target
        velocity and motor power as an attempt to align them.

        This method is the one that should be called on a regular basis,
        and ties the SlewLimiter, PIDController and JerkLimiter together.

        All of the dunderscored methods are intended as internal methods.
        '''
        if self.enabled:
            for callback in self.__callbacks:
                callback()
            _velocity = self._velocity()
            _current_target_velocity = self.__target_velocity
            # set the target velocity variable modified by the slew limiter, if active
            if self._slew_limiter and self._slew_limiter.is_active:
                _current_target_velocity = self._slew_limiter.limit(self.velocity, _current_target_velocity)

            # use velocity clipper as a sanity checker
            _current_target_velocity = self._velocity_clip(_current_target_velocity)

            # we now convert velocity to power, either by passing the target velocity to the PID controller (when active)
            # otherwise directly setting power to the motor via the proportional interpolator from the Speed Enum.
#           self._log.debug('setting target velocity to: {:<5.2f} (from {:5.2f})'.format(_current_target_velocity, self.__target_velocity))
            if self._pid_controller.is_active: # via PID
                self._pid_controller.set_velocity(_current_target_velocity)
            else: # via Speed
                _power = Speed.get_proportional_power(_current_target_velocity)
                self.__set_motor_power(_power)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_motor_power(self, target_power):
        '''
        Direct-drive the motor via a target power argument, whose value must be
        between -1.0 and 1.0.
        '''
        self.__set_motor_power(target_power)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __set_motor_power(self, target_power):
        '''
        Sets the motor power to a number between -1.0 to 1.0, with the actual
        limits set by the max_power_ratio, which alters the value to match
        the power/motor voltage ratio.

        If the JerkLimiter is active this acts as a sanity check on
        overly-rapid changes to motor power.

        :param target_power:  the target motor power
        '''
        if target_power is None:
            raise ValueError('null target_power argument.')
        elif ( not self.enabled ) and target_power > 0.0: # though we'll let the power be set to zero
            self._log.warning('motor enabled {}, ignoring setting of {:<5.2f}'.format(self.enabled, target_power))
            return
        _current_power = self.current_power
        # even if disabled or suppressed, JerkLimiter still clips
        if self._jerk_limiter:
            target_power = self._jerk_limiter.limit(self.current_power, target_power)
        # keep track of highest-applied target power
        self.__max_applied_power = max(abs(target_power), self.__max_applied_power)

        # okay, let's go .........................
        # driving power is modified by the max power ratio to reduce battery voltage to motor voltage
        _driving_power = float(target_power * self.max_power_ratio)
        # temporary, just for safety
        _clipped_driving_power = self._power_clip(_driving_power)
        if self._orientation is Orientation.PORT:
#           self._log.debug('power: target {:5.2f} converted to driving {:<5.2f} clipped to: {:5.2f}'.format(target_power, _driving_power, _clipped_driving_power))
            self._tb.SetMotor1(_clipped_driving_power)
            pass
        else:
#           self._log.debug('power: target {:5.2f} converted to driving {:<5.2f} clipped to: {:5.2f}'.format(target_power, _driving_power, _clipped_driving_power))
            self._tb.SetMotor2(_clipped_driving_power)
            pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
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

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
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
        if self._orientation is Orientation.PORT:
            self._tb.SetMotor1(0.0)
        elif self._orientation is Orientation.STBD:
            self._tb.SetMotor2(0.0)
        else:
            raise ValueError('unrecognised orientation.')
        self._log.info('🆑 {} motor stopped.'.format(self._orientation.name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def off(self):
        '''
        Stops the motor entirely.
        '''
        if self._orientation is Orientation.PORT:
            self._tb.SetMotor1Off()
        elif self._orientation is Orientation.STBD:
            self._tb.SetMotor2Off()
        else:
            raise ValueError('unrecognised orientation.')
        self._log.info('🆑 {} motor off.'.format(self._orientation.name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        if not self.enabled:
            if self._slew_limiter:
                self._slew_limiter.enable()
            if self._jerk_limiter:
                self._jerk_limiter.enable()
            Component.enable(self)
        self._log.info('enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        if self.enabled:
            if self._slew_limiter:
                self._slew_limiter.disable()
            if self._jerk_limiter:
                self._jerk_limiter.disable()
            Component.disable(self)
        self._log.info('disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        if self.enabled:
            self.disable()
        self._log.info('on closing, maximum applied power: {:>5.2f}'.format(self.__max_applied_power))
        # just do it anyway
        self.stop()
        self._log.info('closed.')

#EOF
