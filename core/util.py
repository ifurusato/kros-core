#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-07-07
# modified: 2021-07-07
#

import time
from colorama import init, Fore, Style
init()

# ..............................................................................
class Util(object):
    '''
    A collection of static utility methods.
    '''
    def __init__(self):
        super().__init__()

    # ..........................................................................
    @staticmethod
    def get_formatted_value(value):
        if isinstance(value, float):
            return '{:5.2f}'.format(value)
        else:
            return '{}'.format(value)

    # ..........................................................................
    @staticmethod
    def get_formatted_time(label, value):
       if value is None:
           return ''
       elif value > 1000.0:
           return label + ' {:4.3f}s'.format(value/1000.0)
       else:
           return label + ' {:4.3f}ms'.format(value)

    # ..........................................................................
    @staticmethod
    def repeat(string, number):
        '''
        Repeat 'string' a given number of times.
        '''
        return (string * (number//len(string) + 1))[:number]

    # ..........................................................................
    @staticmethod
    def clip(value, min_value, max_value):
        '''
        A replacement for numpy's clip():

            _value = numpy.clip(target_value, _min, _max)
        '''
        return min_value if value <= min_value else max_value if value >= max_value else value

    @staticmethod
    def clamp(n, minimum, maximum): 
        '''
        Another clip alternative.
        '''
        return max(minimum, min(n, maximum))

#EOF
