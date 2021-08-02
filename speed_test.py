#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019-2021 by Murray Altheim. All rights reserved. This file is part
# of the K-Series Robot Operating System (KROS) project, released under the MIT
# License. Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-14
# modified: 2021-07-20
#

import pytest
import sys, itertools, traceback
import numpy
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from core.speed import Speed

_log = Logger("main", Level.INFO)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_speed():

    _log = Logger("test-speed", Level.INFO)
    # read YAML configuration
    _config = ConfigLoader().configure()
    Speed.configure(_config)
    '''
    Okay, now we have the velocity points on the x axis, though they're not 
    evenly spaced. For any given velocity (even outside of the permitted range)
    we can determine where on the x axis we are (between which two points) and 
    interpolate the x coordinate. We can then determine the two points on the 
    Y axis that we're between and interpolate there as well.
    '''
    for vel in numpy.arange(-105.0, 105.0, 1.0, float):
        _pp = Speed.get_proportional_power(vel)
        _log.info(Fore.YELLOW + 'velocity: {:5.2f};  \tpower: {:5.2f}'.format(vel, _pp))

    _log.info('complete.')

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():
    try:
        test_speed()
    except KeyboardInterrupt:
        print('Ctrl-C caught: test interrupted.')
    except Exception as e:
        print(Fore.RED + 'Error in test: {} / {}'.format(e, traceback.format_exc()) + Style.RESET_ALL)
    finally:
        pass

if __name__ == "__main__":
    main()

#EOF
