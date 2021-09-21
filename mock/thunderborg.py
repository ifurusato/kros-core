#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019-2021 by Murray Altheim. All rights reserved. This file is part
# of the K-Series Robot Operating System (KROS) project, released under the MIT
# License. Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-14
# modified: 2021-04-22
#
# Class used to control ThunderBorg motor controller (from PiBorg), and responds
# to a request for a battery reading with a fixed value.
#

"""
This module is designed to communicate with a nonexistent (mock) ThunderBorg.

It only provides for setting and getting the power setting of motors 1 and 2.
"""

import itertools
from colorama import init, Fore, Style
init()

from core.logger import Level, Logger

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ThunderBorg(object):
    """
This module is designed to communicate with the ThunderBorg
    """
    def __init__(self, level):
        super().__init__()
        self._log = Logger('mock-thunderborg', level)
        self._log.info('ready.')
        self._counter1     = itertools.count()
        self._counter2     = itertools.count()
        self._modulo       = 100
        self._motor1_power = 0.0
        self._motor2_power = 0.0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def SetMotor1(self, power):
        """
SetMotor1(power)

Sets the drive level for motor 1, from +1 to -1.
e.g.
SetMotor1(0)     -> motor 1 is stopped
SetMotor1(0.75)  -> motor 1 moving forward at 75% power
SetMotor1(-0.5)  -> motor 1 moving reverse at 50% power
SetMotor1(1)     -> motor 1 moving forward at 100% power
        """
        if next(self._counter1) % self._modulo == 0.0:
            self._log.debug(Fore.RED + Style.DIM + 'SetMotor1() power: {:5.2f}'.format(power))
        self._motor1_power = power

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def GetMotor1(self):
        """
power = GetMotor1()

Gets the drive level for motor 1, from +1 to -1.
e.g.
0     -> motor 1 is stopped
0.75  -> motor 1 moving forward at 75% power
-0.5  -> motor 1 moving reverse at 50% power
1     -> motor 1 moving forward at 100% power
        """
        return self._motor1_power

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def SetMotor2(self, power):
        """
SetMotor2(power)

Sets the drive level for motor 2, from +1 to -1.
e.g.
SetMotor2(0)     -> motor 2 is stopped
SetMotor2(0.75)  -> motor 2 moving forward at 75% power
SetMotor2(-0.5)  -> motor 2 moving reverse at 50% power
SetMotor2(1)     -> motor 2 moving forward at 100% power
        """
        if next(self._counter2) % self._modulo == 0.0:
            self._log.debug(Fore.GREEN + Style.DIM + 'SetMotor2() power: {:5.2f}'.format(power))
        self._motor2_power = power

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def GetMotor2(self):
        """
power = GetMotor2()

Gets the drive level for motor 2, from +1 to -1.
e.g.
0     -> motor 2 is stopped
0.75  -> motor 2 moving forward at 75% power
-0.5  -> motor 2 moving reverse at 50% power
1     -> motor 2 moving forward at 100% power
        """
        return self._motor2_power

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def SetMotors(self, power):
        """
SetMotors(power)

Sets the drive level for all motors, from +1 to -1.
e.g.
SetMotors(0)     -> all motors are stopped
SetMotors(0.75)  -> all motors are moving forward at 75% power
SetMotors(-0.5)  -> all motors are moving reverse at 50% power
SetMotors(1)     -> all motors are moving forward at 100% power
        """
        self.SetMotor1(power)
        self.SetMotor2(power)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def MotorsOff(self):
        """
MotorsOff()

Sets all motors to stopped, useful when ending a program
        """
        self.SetMotor1(0.0)
        self.SetMotor2(0.0)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def GetBatteryReading(self):
        """
voltage = GetBatteryReading()

Reads the current battery level from the main input.
Returns the value as a voltage based on the 3.3 V rail as a reference.
        """
        return 19.09

#EOF
