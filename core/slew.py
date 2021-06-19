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
# A general purpose slew limiter that limits the rate of change of a value.
#

import time
from enum import Enum
from collections import deque
from colorama import init, Fore, Style
init()

#try:
#    import numpy
#except ImportError:
#    exit("This script requires the numpy module\nInstall with: pip3 install --user numpy")

from core.logger import Level, Logger

# ..............................................................................
class SlewLimiter():
    '''
    A general purpose slew limiter that limits the rate of change of a value.

    This uses the ros:slew: section of the YAML configuration.

    Parameters:
    :param config:  application configuration
    :param orientation:   used for the logger label
    :param level:   the logging Level
    '''
    def __init__(self, config, orientation, level):
        self._log = Logger('slew:{}'.format(orientation.label), level)
        self._millis  = lambda: int(round(time.time() * 1000))
        self._seconds = lambda: int(round(time.time()))
        self._clamp   = lambda n: self._minimum_output if n <= self._minimum_output else self._maximum_output if n >= self._maximum_output else n
        # Slew configuration .........................................
        cfg = config['kros'].get('slew')
        self._minimum_output = cfg.get('minimum_output')
        self._maximum_output = cfg.get('maximum_output')
        self._log.info('minimum output: {:5.2f}; maximum output: {:5.2f}'.format(self._minimum_output, self._maximum_output))
        self._slew_rate      = SlewRate.SLOW # default rate_limit, value change permitted per millisecond
        self._log.info('slew rate: {}; {:6.4f}/cycle'.format(self._slew_rate.label, self._slew_rate.limit))
        self._stats_queue    = None
        self._start_time     = None
        self._enabled        = False
        self._log.info('ready.')

    # ..........................................................................
    def set_rate_limit(self, slew_rate):
        '''
        Sets the slew rate limit to the argument, in value/second. This
        overrides the value set in configuration.
        '''
        if not isinstance(slew_rate, SlewRate):
            raise Exception('expected SlewRate argument, not {}'.format(type(slew_rate)))
        self._slew_rate = slew_rate
        self._log.info('slew rate limit set to {}; {:>6.4f}/cycle.'.format(slew_rate.label, self._slew_rate.limit))

    # ..........................................................................
    def is_enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        self._log.info(Fore.YELLOW + 'starting slew limiter with rate limit of {:5.3f}/cycle.'.format(self._slew_rate.limit))
        self._enabled = True
        self._start_time = self._millis()
        self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        self._log.info(Fore.MAGENTA + 'slew disabled.')
        self._enabled = False

    # ..........................................................................
    def reset(self, value):
        '''
        Resets the elapsed timer.
        '''
        self._start_time = self._millis()

    # ..........................................................................
    def slew(self, current_value, target_value):
        '''
        The returned result is the maximum amount of change between the current value
        and the target value based on the amount of elapsed time between calls (in
        milliseconds) multiplied by a constant set in configuration.

        If not enabled this returns the passed target value argument.
        '''
        if not self._enabled:
            self._log.warning('disabled; returning original target value {:+06.2f}.'.format(target_value))
            return target_value
        self._log.debug(Fore.BLACK + 'slew from current {:+06.2f} to target value {:+06.2f}.'.format(current_value, target_value))
        _now = self._millis()
        _elapsed = _now - self._start_time
        if target_value == current_value:
            _value = current_value
#           self._log.debug(Fore.BLACK + 'already there; returning target: {:+06.2f})'.format(_value))
        elif target_value > current_value: # increasing ..........
            _min = current_value - ( self._slew_rate.limit * _elapsed )
            _max = current_value + ( self._slew_rate.limit * _elapsed )
            _value = self._clip(target_value, _min, _max)
#           _value = numpy.clip(target_value, _min, _max)
            self._log.debug(Fore.GREEN + '-value: {:+06.2f} = clip(target_value: {:+06.2f}), _min: {:+06.2f}), _max: {:+06.2f}); elapsed: {:+06.2f}'.format(\
                    _value, target_value, _min, _max, _elapsed))
        else: # decreasing .......................................
            _min = current_value - ( self._slew_rate.limit * _elapsed )
            _max = current_value + ( self._slew_rate.limit * _elapsed )
            _value = self._clip(target_value, _min, _max)
#           _value = numpy.clip(target_value, _min, _max)
            self._log.debug(Fore.RED + '-value: {:+06.2f} = clip(target_value: {:+06.2f}), _min: {:+06.2f}), _max: {:+06.2f}); elapsed: {:+06.2f}'.format(\
                    _value, target_value, _min, _max, _elapsed))
        # clip the output between min and max set in config (if negative we fix it before and after)
        if _value < 0:
            _clamped_value = -1.0 * self._clamp(-1.0 * _value)
        else:
            _clamped_value = self._clamp(_value)
        self._log.debug('slew from current {:>6.2f} to target {:>6.2f} returns:'.format(current_value, target_value) \
                + Fore.MAGENTA + '\t{:>6.2f}'.format(_clamped_value) + Fore.BLACK + ' (clamped from {:>6.2f})'.format(_value))
        return _clamped_value

    # ..........................................................................
    def _clip(self, value, min_value, max_value):
        '''
        A replacement for numpy's clip():

            _value = numpy.clip(target_value, _min, _max)
        '''
        return min_value if value <= min_value else max_value if value >= max_value else value

# ..............................................................................
class SlewRate(Enum): #       tested to 50.0 velocity:
    EXTREMELY_SLOW   = ( 0.3, 0.0034, 0.16, 00.0001 ) # 5.1 sec
    VERY_SLOW        = ( 1,   0.01,   0.22, 00.0002 ) # 3.1 sec
    SLOWER           = ( 2.5, 0.03,   0.38, 00.0005 ) # 1.7 sec
    SLOW             = ( 2,   0.05,   0.48, 00.0010 ) # 1.3 sec
    NORMAL           = ( 3,   0.08,   0.58, 00.0050 ) # 1.0 sec
    FAST             = ( 4,   0.20,   0.68, 00.0100 ) # 0.6 sec
    VERY_FAST        = ( 5,   0.4,    0.90, 00.0200 ) # 0.5 sec

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, num, ratio, pid, limit):
        self._ratio = ratio
        self._pid   = pid
        self._limit = limit

    @property
    def label(self):
        return self.name

#   @property
#   def ratio(self):
#       return self._ratio

#   @property
#   def pid(self):
#       return self._pid

    @property
    def limit(self):
        return self._limit

#EOF
