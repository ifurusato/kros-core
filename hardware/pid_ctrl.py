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
# modified: 2021-07-29
#

import sys
from collections import deque as Deque
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.orient import Orientation
from core.message import Message
from core.message_bus import MessageBus
from core.event import Event
from hardware.pid import PID

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class PIDController(Component):
    '''
    Provides a configurable PID motor controller. This also maintains a value
    for the current motor velocity by sampling the step count from the motors
    on the same interval as the PID calls.

    :param config:       The application configuration, read from a YAML file.
    :param message_bus:  The application message bus.
    :param motor:        The motor to be controlled.
    :param setpoint:     The initial setpoint or target output
    :param period:       The sample time in seconds before generating a new output value.
                         This PID is expected to be called at a constant rate.
    :param suppressed:   Initial suppressed state.
    :param enabled:      Initial enabled state.
    :param level:        The log level, e.g., Level.INFO.
    '''
    def __init__(self, config, message_bus, motor, setpoint=0.0, period=0.01, suppressed=False, enabled=True, level=Level.INFO):
        if not isinstance(config, dict):
            raise ValueError('wrong type for config argument: {}'.format(type(config)))
        self._config = config
        if not isinstance(message_bus, MessageBus):
            raise ValueError('wrong type for message bus argument: {}'.format(type(message_bus)))
        self._message_bus = message_bus
        if motor is None:
            raise ValueError('null motor argument.')
        self._motor = motor
        self._orientation = motor.orientation
        self._log = Logger('pid-ctrl:{}'.format(self._orientation.label), level)
        Component.__init__(self, self._log, suppressed=suppressed, enabled=enabled)
        # PID configuration ................................
        _cfg = config['kros'].get('motor').get('pid_controller')
        _kp         = _cfg.get('kp') # proportional gain
        _ki         = _cfg.get('ki') # integral gain
        _kd         = _cfg.get('kd') # derivative gain
        _min_output = _cfg.get('minimum_output')
        _max_output = _cfg.get('maximum_output')
        _freq_hz    = _cfg.get('sample_freq_hz')
        _period_sec = 1.0 / _freq_hz
        self._log.info('sample frequency: {:d}Hz; period: {:5.2f} sec.'.format(_freq_hz, _period_sec))
        self._pid = PID(self._orientation.label, _kp, _ki, _kd, _min_output, _max_output, period=_period_sec, level=level)
        # used for hysteresis, if queue too small will zero-out motor power too quickly
        _queue_len = _cfg.get('hyst_queue_len')
        self._deque = Deque([], maxlen=_queue_len)
        self._power        = 0.0
        self._last_power   = 0.0
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def orientation(self):
        return self._orientation

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
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

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def steps(self):
        return self._motor.steps

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def reset_steps(self):
        self._motor._steps = 0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
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
        self._pid.setpoint = setpoint

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_limit(self, limit):
        '''
        Setter for the limit of the PID setpoint.
        Set to None (the default) to disable this feature.
        '''
        self._pid.set_limit(limit)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def stats(self):
        '''
         Returns statistics a tuple for this PID contrroller:
            [kp, ki, kd, cp, ci, cd, last_power, current_motor_power, power, _velocity, setpoint, steps]
        '''
        kp, ki, kd = self._pid.constants
        cp, ci, cd = self._pid.components
        return kp, ki, kd, cp, ci, cd, self._last_power, self._motor.current_power_level, self._power, self._motor.velocity, self._pid.setpoint, self._motor.steps

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   @property
#   def enabled(self):
#       return self.enabled

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_velocity(self, velocity):
        if self.enabled:
            self._log.info(Fore.WHITE + Style.DIM + '🍈 set PID velocity for {} motor: {:+d} steps; velocity: {:<5.2f}'.format(self._orientation.label, self._motor.steps, velocity))
#           self._pid.setpoint = velocity
            # converts velocity to power...
            _pid_output = self._pid(velocity)
            self._power += _pid_output
            _motor_power = self._power / 100.0
            self._log.info(Fore.WHITE + Style.DIM + '🍈 set power for {} motor: {:<5.2f} (pid output: {:5.2f})'.format(self._orientation.label, _motor_power, _pid_output))
#           self._log.info(Fore.WHITE + Style.NORMAL + 'handle() _steps: {:d}; _power: {:>5.2f}/_motor_power: {:>5.2f};\t'.format(self._motor.steps, self._power, _motor_power) \
#                   + 'pid output: {:5.2f};\t'.format(_pid_output) + Style.BRIGHT + 'velocity: {:5.2f}'.format(velocity))
            self._motor.set_motor_power(_motor_power)
            self._last_power = self._power
#           _mean_setpoint = self._get_mean_setpoint(self._pid.setpoint)
#           if _mean_setpoint == 0.0:
#               self._motor.set_motor_power(0.0)
#           else:
#               self._motor.set_motor_power(self._power / 100.0)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def handle(self, message):
        '''
        The PID loop that continues while the enabled flag is True.

        This uses a running average on the setpoint to settle the output
        at zero when it's clear the target velocity is zero. This is a
        perhaps cheap approach to hysteresis.
        '''
        if self.enabled and ( message.event is Event.CLOCK_TICK or message.event is Event.CLOCK_TOCK ):
            # obtain velocity from motor encoder's step count
            self.set_velocity(self._motor.velocity)
        return message

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
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

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_state(self):
        _fore = Fore.RED if self._orientation == Orientation.PORT else Fore.GREEN
        self._log.info(_fore + 'power:        \t{}'.format(self._power))
        self._log.info(_fore + 'last_power:   \t{}'.format(self._last_power))
        self._pid.print_state()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def reset(self):
        self._pid.reset()
        self._motor.stop()
        self._log.info(Fore.GREEN + 'reset.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        if self.closed:
            self._log.warning('cannot enable PID loop: already closed.')
        else:
            if self.enabled:
                self._log.warning('PID loop already enabled.')
            else:
                self._message_bus.add_handler(Message, self.handle)
                Component.enable(self)

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   def disable(self):
#       if not self.enabled:
#           self._log.warning('already disabled.')
#       elif self.closed:
#           self._log.warning('already closed.')
#       else:
#           self.enabled = False
#           self._log.info('disabled.')

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   def close(self):
#       self.disable()
#       self.closed = True
#       self._log.info('closed.')

#EOF
