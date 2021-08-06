#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-05
# modified: 2021-08-05
#

from colorama import init, Fore, Style
init()

from core.orient import Orientation
from core.logger import Level, Logger

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MockVelocity(object):
    '''
    This mocks the Velocity class, simply returning the value set as the
    target velocity.

    :param config:   the application configuration
    :param motor:    the motor whose velocity is to be measured
    :param level:    the logging level
    '''
    def __init__(self, orientation, level=Level.INFO):
        self._log = Logger('mock-velo:{}'.format(orientation.label), level)
        self._velocity = 0.0
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def target_velocity(self):
        return self._velocity

    @target_velocity.setter
    def target_velocity(self, target_velocity):
        self._log.info('setting target velocity: {}'.format(target_velocity))
        self._velocity = target_velocity

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __call__(self):
        '''
        Returns the set target velocity.
        '''
        return self._velocity

#EOF
