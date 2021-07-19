#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-27
# modified: 2020-05-21
#
# A jerk limiter that limits the rate of acceleration of a motor power.
#

from math import isclose
from colorama import init, Fore, Style
init()

from core.logger import Level, Logger
from core.component import Component

# ..............................................................................
class JerkLimiter(object):
    '''
    A jerk limiter that limits the rate of change of a value. This isn't
    actually a jerk limiter in the formal sense because it doesn't take
    time into account in its calculation, and therefore not acceleration
   (and 'jerk' is defined as the rate of change of acceleration). This is
    just a simple low pass filter using fixed values for min/max clipping.
    It is used to add a safety feature to the values of motor power sent
    to the controller, so due to its position in the controller process
    it is acting in the capacity of minimising jerk.

    This uses the ros:motors:jerk: section of the YAML configuration.

    Parameters:
    :param config:           application configuration
    :param orientation:      used only for the logger label
    :param max_power_limit:  optionally set the maximum power limit (with 'value * -1' for lower limit)
    :param level:            the logging Level
    '''
    def __init__(self, config, orientation, max_power_limit=None, level=Level.INFO):
        self._log = Logger('jerk:{}'.format(orientation.label), level)
        _cfg = config['kros'].get('motors').get('jerk')
        self._maximum_change = _cfg.get('maximum_change')
        if max_power_limit != None:
            _maximum_output = max_power_limit
            _minimum_output = -1 * max_power_limit
        else:
            _minimum_output = _cfg.get('minimum_output')
            _maximum_output = _cfg.get('maximum_output')
        self._log.info('maximum change: {:5.2f}; minimum output: {:5.2f}; maximum output: {:5.2f}'.format(
                self._maximum_change, _minimum_output, _maximum_output))
        self._clip = lambda n: _minimum_output if n <= _minimum_output else _maximum_output if n >= _maximum_output else n
        self._log.info('ready.')

    # ..........................................................................
    def limit(self, current_value, target_value):
        '''
        The returned result is the limited by maximum amount of change between
        the current value and the target value, using a constant set in
        configuration. If the two arguments are the same (mathematically close)
        we just return the current value. The result is clipped to the minimum
        and maximum output values set in configuration.

        This filter works for either negative or positive values, clipping
        changes larger than the jerk value.
        '''
        self._log.debug('limit current {:+06.2f} to target value {:+06.2f}.'.format(current_value, target_value))
        _value = target_value
        if isclose(current_value, target_value, abs_tol=1e-3):
            pass
        elif target_value > current_value: # increasing ..........
            if abs(current_value - target_value) > self._maximum_change:
                # only allow the current value plus the jerk limit
                _value = current_value + self._maximum_change
        else: # decreasing .......................................
            if abs(current_value - target_value) > self._maximum_change:
                # only allow the current value minus the jerk limit
                _value = current_value - self._maximum_change
        return -1.0 * self._clip(-1.0 * _value) if _value < 0.0 else self._clip(_value)

    # ..........................................................................
    def print_test_result(self, current_value, target_value):
        _result = self.limit(current_value, target_value)
        self._log.info(Fore.GREEN + 'current: {:5.2f}; '.format(current_value)
                + Fore.MAGENTA + 'target: {:5.2f}; '.format(target_value)
                + Fore.YELLOW  + 'result: {:5.2f}.'.format(_result))
        return _result

#EOF
