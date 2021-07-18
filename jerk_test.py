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

import pytest, unittest
import sys, traceback
import numpy
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from core.orient import Orientation
from hardware.jerk import JerkLimiter


class TestJerk(unittest.TestCase):

    # ..............................................................................
    @pytest.mark.unit
    def test_jerk(self):
    
        _log = Logger("test", Level.INFO)
    
        # read YAML configuration
        _config = ConfigLoader().configure()
    
        _jerk = JerkLimiter(_config, Orientation.PORT, Level.INFO)
        
        _jerk.print_test_result(-0.3, 0.1)
        _jerk.print_test_result(-0.2, 0.1)
        _jerk.print_test_result(-0.1, 0.2)
        _jerk.print_test_result(0.5, 0.8)
    
        _neg = -0.90001
        _zero = 0.0
        _min = -0.90
        _max = 0.90
        _over = 1.2
        _step = 0.1
        _last_value = _neg
        _log.info('ramp up!   .................')
        for _power in numpy.arange(_neg, _over, _step, float):
            _value = _jerk.print_test_result(_last_value, _power)
            print('VALUE: {}'.format(_value))
            self.assertTrue(_value >= _min)
            self.assertTrue(_value <= _max)
#           self.assertTrue(abs(round( _value - _last_value, 3)) <= _step)
            _last_value = _power
    
        _log.info('ramp down!   ...............')
        for _power in numpy.arange(_max, _neg, -1 * _step, float):
            _value = _jerk.print_test_result(_last_value, _power)
            print('VALUE: {}'.format(_value))
            self.assertTrue(_value >= _min)
            self.assertTrue(_value <= _max)
#           self.assertTrue(abs(round( _value - _last_value, 3)) <= _step)
            _last_value = _power
        
        _log.info('complete.')

#   raise Exception('error message.')

# main .........................................................................
def main():
    try:
        _test = TestJerk()
        _test.test_jerk()
    except KeyboardInterrupt:
        print('Ctrl-C caught: test interrupted.')
        sys.exit(0)
    except Exception as e:
        print(Fore.RED + 'Error in test: {} / {}'.format(e, traceback.print_stack()) + Style.RESET_ALL)
        sys.exit(1)
    finally:
        pass

# ........................
if __name__ == "__main__":
    main()

#EOF
