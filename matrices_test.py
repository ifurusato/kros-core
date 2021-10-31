#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-10
# modified: 2021-09-02
#
# This tests the 11x7 Matrix, including several custom modes.
#

import pytest
import sys, time
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from hardware.i2c_scanner import I2CScanner
from hardware.matrix import Matrices
from hardware.irq_clock import IrqClock

# ..............................................................................
@pytest.mark.unit
def test_matrix():

    _log = Logger('matrix-test', Level.INFO)
    _matrices = None

    try:

        # read YAML configuration
        _config = ConfigLoader(Level.INFO).configure()

        _pin = 5
        _log.info('🌞 1. creating external clock on pin {:d}...'.format(_pin))
        _irq_clock = IrqClock(_config, _pin, Level.INFO)

        _log.info(Fore.CYAN + 'start matrices test...')

        _i2c_scanner = I2CScanner(_config, Level.WARN)
        if not _i2c_scanner.has_address([0x75, 0x77]):
            _log.warning('test ignored: no rgbmatrix displays found.')
            return
        _addresses = _i2c_scanner.get_int_addresses()
        _enable_port = 0x77 in _addresses
        _enable_stbd = 0x75 in _addresses

        _matrices = Matrices(_enable_port, _enable_stbd, level=Level.INFO)

        _irq_clock.add_callback(_matrices.horizontal_whack)

#       _log.info('matrix write text...')
#       _matrices.text('HE', 'LP')
#       time.sleep(3)
#       _matrices.clear_all()
#       time.sleep(1)

#       _log.info('matrix on...')
#       _matrices.on()
#       time.sleep(2)

#       _log.info('matrix off...')
#       _matrices.clear_all()
#       time.sleep(1)

        _irq_clock.enable()

#       _log.info('manual gradient wipes...')
#       for i in range(1,8):
#           _matrices.vertical_gradient(i)
#           time.sleep(0.02)
#       for i in range(7,-1,-1):
#           _matrices.vertical_gradient(i)
#           time.sleep(0.02)
#       time.sleep(1)
#       for i in range(1,11):
#           _matrices.horizontal_gradient(i)
#           time.sleep(0.02)
#       for i in range(11,-1,-1):
#           _matrices.horizontal_gradient(i)
#           time.sleep(0.02)
#       time.sleep(1)

#       _log.info('starting matrix vertical wipe...')
#       _matrices.wipe(Matrices.DOWN, True, 0.00)
#       time.sleep(0.0)
#       _matrices.wipe(Matrices.DOWN, False, 0.00)
#       _matrices.clear_all()
#       time.sleep(1)

#       _log.info('starting matrix horizontal wipe right...')
#       _matrices.wipe(Matrices.RIGHT, True, 0.00)
#       time.sleep(0.0)
#       _log.info('starting matrix horizontal wipe left...')
#       _matrices.wipe(Matrices.LEFT, False, 0.00)
#       _matrices.clear_all()
        # UP and LEFT not implemented

#       # now the cylon scanning loop ......
#       _matrices.clear_all()
#       _log.info('starting column on ranged matrices, ' + Fore.YELLOW + 'Ctrl-C to quit.')
        while True:
#           for c in range(0,22):
#               _matrices.column(c)
#               time.sleep(0.001)
#           for c in range(21,-1,-1):
#               _matrices.column(c)
#               time.sleep(0.001)
            time.sleep(1)
#       time.sleep(0.5)
        _matrices.clear_all()

    except KeyboardInterrupt:
        _log.info(Fore.MAGENTA + 'Ctrl-C caught: interrupted.')
    finally:
        _log.info('closing matrix test...')
        if _matrices:
            _matrices.clear_all()


# call main ......................................

def main():

    test_matrix()

if __name__== "__main__":
    main()

