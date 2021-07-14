#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-08
# modified: 2020-10-18
#

from colorama import init, Fore, Style
init()

#from core.config_loader import ConfigLoader
from core.logger import Logger, Level
from core.orient import Orientation
from core.rate import Rate
from core.message_bus import MessageBus
from hardware.motors import Motors
from hardware.pid_ctrl import PIDController

# ..............................................................................
class PIDMotorController(object):
    '''
    A simple composite pattern consisting of two PIDControllers, one for
    control of the port motor, another for the starboard motor.
    '''
    def __init__(self, config, message_bus, motors, level=Level.INFO):
        super().__init__()
        if not isinstance(config, dict):
            raise ValueError('wrong type for config argument: {}'.format(type(name)))
        self._config = config
        self._log = Logger("pmc", level)
        if not isinstance(message_bus, MessageBus):
            raise ValueError('unrecognised message bus argument: {}'.format(type(message_bus)))
        self._message_bus = message_bus
        self._motors   = motors
        self._port_pid = PIDController(self._config, self._message_bus, self._motors.get_motor(Orientation.PORT), level=level)
        self._stbd_pid = PIDController(self._config, self._message_bus, self._motors.get_motor(Orientation.STBD), level=level)
        self._log.info('ready.')

    # ..........................................................................
    def get_motors(self):
        return self._motors

    # ..........................................................................
    def get_pid_controllers(self):
        return self._port_pid, self._stbd_pid

    # ..........................................................................
    def set_max_velocity(self, max_velocity):
        self._port_pid.set_max_velocity(max_velocity)
        self._stbd_pid.set_max_velocity(max_velocity)

    # ..........................................................................
    @property
    def enabled(self):
        return self._port_pid.enabled or self._stbd_pid.enabled

    # ..........................................................................
    def enable(self):
        self._port_pid.enable()
        self._stbd_pid.enable()

    # ..........................................................................
    def disable(self):
        self._motors.disable()
        self._port_pid.disable()
        self._stbd_pid.disable()

    # ..........................................................................
    def close(self):
        if self.enabled:
            self.disable()
        self._motors.close()
        self._port_pid.close()
        self._stbd_pid.close()

#EOF
