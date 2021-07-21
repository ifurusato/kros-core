#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-20
# modified: 2020-09-26
# modified: 2021-07-14
#
# This controller uses a threaded loop and uses a pair of PID controllers from
# the PID class.
#

import sys, time
from collections import deque as Deque
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.orient import Orientation
from core.message import Message
from core.event import Event
from hardware.pid import PID
from hardware.slew import SlewRate, SlewLimiter

# ..............................................................................
class PIDController(object):
    '''
     Provides a configurable PID motor controller via a threaded
     fixed-time loop. This also maintains a value for the current 
     motor velocity by sampling the step count from the motors on
     the same interval as the PID calls.

     If the 'kros:motors:pid:enable_slew' property is True, this
     will set a slew limiter on the PID setpoint.
    '''

    def __init__(self, config, message_bus, motor, setpoint=0.0, sample_time=0.01, level=Level.INFO):
        '''
        :param config:       The application configuration, read from a YAML file.
        :param message_bus:  The application message bus.
        :param motor:        The motor to be controlled.
        :param setpoint:     The initial setpoint or target output
        :param sample_time:  The time in seconds before generating a new output value.
                             This PID is expected to be called at a constant rate.
        :param level:        The log level, e.g., Level.INFO.
        '''
        if config is None:
            raise ValueError('null configuration argument.')
        self._config = config['kros'].get('motors').get('pid-controller')
        if message_bus is None:
            raise ValueError('null message bus argument.')
        self._message_bus = message_bus
        if motor is None:
            raise ValueError('null motor argument.')
        self._motor = motor
        self._orientation = motor.orientation
        self._log = Logger('pid-ctrl:{}'.format(self._orientation.label), level)
        if sys.version_info < (3,0):
            self._log.error('PID class requires Python 3.')
            sys.exit(1)
        # PID configuration ................................
#        self._pot_ctrl = self._config.get('pot_ctrl')
#        if self._pot_ctrl:
#            self._pot = Potentiometer(config, Level.INFO)
        _period_sec = 1.0 / self._config.get('sample_freq_hz')
        _kp         = self._config.get('kp') # proportional gain
        _ki         = self._config.get('ki') # integral gain
        _kd         = self._config.get('kd') # derivative gain
        _min_output = self._config.get('mininum_output')
        _max_output = self._config.get('maximum_output')
        self._pid = PID(self._orientation.label, _kp, _ki, _kd, _min_output, _max_output, sample_time=_period_sec, level=level)

        # used for hysteresis, if queue too small will zero-out motor power too quickly
        _queue_len = self._config.get('hyst_queue_len')
        self._deque = Deque([], maxlen=_queue_len)

        self._enable_slew = self._config.get('enable_slew')
        if self._enable_slew:
            raise Exception('use slew limiter from Motor instead.')
#           self._slewlimiter = SlewLimiter(config, orientation=self._motor.orientation, level=Level.INFO)
#           self._slewlimiter.set_rate_limit(SlewRate.NORMAL) # configurable?
#           self._slewlimiter.enable()
#           self._log.info('slew limiter enabled.')
        else:
            self._slewlimiter = None
            self._log.info('slew limiter disabled.')

        self._power        = 0.0
        self._last_power   = 0.0
        self._enabled      = False
        self._closed       = False
#       self._last_steps   = 0
#       self._max_diff_steps = 0
        self._log.info('ready.')

    # ..........................................................................
    @property
    def orientation(self):
        return self._orientation

    # ..............................................................................
    @property
    def kp(self):
        return self._pid.kp

    @kp.setter
    def kp(self, kp):
        self._pid.kp = kp

    @property
    def ki(self):
        return self._pid.ki

    @ki.setter
    def ki(self, ki):
        self._pid.ki = ki

    @property
    def kd(self):
        return self._pid.kd

    @kd.setter
    def kd(self, kd):
        self._pid.kd = kd

#   # ..............................................................................
#   def enable_slew(self, enable):
#       _old_value = self._enable_slew
#       if not self._slewlimiter.is_enabled():
#           self._slewlimiter.enable()
#       self._enable_slew = enable
#       return _old_value

#   # ..............................................................................
#   def set_slew_rate(self, slew_rate):
#       if type(slew_rate) is SlewRate:
#           self._slewlimiter.set_rate_limit(slew_rate)
#       else:
#           raise Exception('expected SlewRate argument, not {}'.format(type(slew_rate)))

    # ..............................................................................
    @property
    def steps(self):
        return self._motor.steps

    def reset_steps(self):
        self._motor._steps = 0

    # ..........................................................................
    @property
    def setpoint(self):
        '''
        Getter for the setpoint (PID set point).
        '''
        return self._pid.setpoint

    @setpoint.setter
    def setpoint(self, setpoint):
        '''
        Setter for the setpoint (PID set point).
        '''
#       if self._enable_slew:
#           setpoint = self._slewlimiter.limit(self.setpoint, setpoint)
        self._pid.setpoint = setpoint

    # ..........................................................................
    def set_limit(self, limit):
        '''
        Setter for the limit of the PID setpoint.
        Set to None (the default) to disable this feature.
        '''
        self._pid.set_limit(limit)

    # ..........................................................................
    @property
    def stats(self):
        '''
         Returns statistics a tuple for this PID contrroller:
            [kp, ki, kd, cp, ci, cd, last_power, current_motor_power, power, _velocity, setpoint, steps]
        '''
        kp, ki, kd = self._pid.constants
        cp, ci, cd = self._pid.components
        return kp, ki, kd, cp, ci, cd, self._last_power, self._motor.current_power_level, self._power, self._motor.velocity, self._pid.setpoint, self._motor.steps

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def handle(self, message):
        '''
        The PID loop that continues while the enabled flag is True.

        This uses a running average on the setpoint to settle the output
        at zero when it's clear the target velocity is zero. This is a
        perhaps cheap approach to hysteresis.
        '''
        if self._enabled and ( message.event is Event.CLOCK_TICK or message.event is Event.CLOCK_TOCK ):
            # calculate velocity from motor encoder's step count
            _velocity = self._motor.velocity
#           self._log.info(Fore.BLACK + 'handle({}): {:+d} steps; velocity: {:<5.2f}'.format(self._orientation.label, self._motor.steps, _velocity))
            _pid_output = self._pid(_velocity)
            self._power += _pid_output
            _motor_power = self._power / 100.0
#           self._log.info(Fore.WHITE + Style.NORMAL + 'handle() _steps: {:d}; _power: {:>5.2f}/_motor_power: {:>5.2f};\t'.format(self._motor.steps, self._power, _motor_power) \
#                   + 'pid output: {:5.2f};\t'.format(_pid_output) + Style.BRIGHT + 'velocity: {:5.2f}'.format(_velocity))
            self._motor.set_motor_power(_motor_power)
            self._last_power = self._power
#           _mean_setpoint = self._get_mean_setpoint(self._pid.setpoint)
#           if _mean_setpoint == 0.0:
#               self._motor.set_motor_power(0.0)
#           else:
#               self._motor.set_motor_power(self._power / 100.0)
        return message

    # ..........................................................................
    def _get_mean_setpoint(self, value):
        '''
        Returns the mean of setpoint values collected in the queue.
        This is used to provide hysteresis around the PID controller's
        setpoint, eliminating jitter particularly around zero.
        '''
        if value == None:
            raise Exception('null argument')
        self._deque.append(value)
        _n = 0
        _mean = 0.0
        for x in self._deque:
            _n += 1
            _mean += ( x - _mean ) / _n
        return float('nan') if _n < 1 else _mean

    # ..........................................................................
    def print_state(self):
        _fore = Fore.RED if self._orientation == Orientation.PORT else Fore.GREEN
        self._log.info(_fore + 'power:        \t{}'.format(self._power))
        self._log.info(_fore + 'last_power:   \t{}'.format(self._last_power))
        self._pid.print_state()

    # ..........................................................................
    def reset(self):
        self._pid.reset()
        self._motor.stop()
        self._log.info(Fore.GREEN + 'reset.')

    # ..........................................................................
    def enable(self):
        if not self._closed:
            if self._enabled:
                self._log.warning('PID loop already enabled.')
            else:
                self._message_bus.add_handler(Message, self.handle)
                self._enabled = True
        else:
            self._log.warning('cannot enable PID loop: already closed.')

    # ..........................................................................
    def disable(self):
        if not self._enabled:
            self._log.warning('already disabled.')
        elif self._closed:
            self._log.warning('already closed.')
        else:
            self._enabled = False
            self._log.info('disabled.')

    # ..........................................................................
    def close(self):
        self.disable()
        self._closed = True
        self._log.info('closed.')

#EOF
