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
from hardware.matrix import Matrices

# ..............................................................................
@pytest.mark.unit
def test_matrix():

    _log = Logger('matrix-test', Level.INFO)
    _matrices = None

    try:

        # read YAML configuration
        _config = ConfigLoader(Level.INFO).configure()

        _log.info(Fore.CYAN + 'start matrices test...')

        _enable_port = True
        _enable_stbd = True
        _matrices = Matrices(_enable_port, _enable_stbd, level=Level.INFO)

        _log.info('matrix write text...')
        _matrices.text('HE', 'LP')
        time.sleep(3)
        _matrices.clear()
        time.sleep(1)

        _log.info('matrix on...')
        _matrices.on()
        time.sleep(2)

        _log.info('matrix off...')
        _matrices.clear()
        time.sleep(1)

        _log.info('manual gradient wipes...')
        for i in range(1,8):
            _matrices.vertical_gradient(i)
            time.sleep(0.02)
        for i in range(7,-1,-1):
            _matrices.vertical_gradient(i)
            time.sleep(0.02)
        time.sleep(1)
        for i in range(1,11):
            _matrices.horizontal_gradient(i)
            time.sleep(0.02)
        for i in range(11,-1,-1):
            _matrices.horizontal_gradient(i)
            time.sleep(0.02)
        time.sleep(1)

        _log.info('starting matrix vertical wipe...')
        _matrices.wipe(Matrices.DOWN, True, 0.00)
        time.sleep(0.0)
        _matrices.wipe(Matrices.DOWN, False, 0.00)
        _matrices.clear()
        time.sleep(1)

        _log.info('starting matrix horizontal wipe right...')
        _matrices.wipe(Matrices.RIGHT, True, 0.00)
        time.sleep(0.0)
        _matrices.wipe(Matrices.RIGHT, False, 0.00)
        _matrices.clear()
        # UP and LEFT not implemented

        # now the cylon scanning loop ......
        _matrices.clear()
        _log.info('starting column on ranged matrices, Ctrl-C to quit.')
        while True:
            for c in range(0,22):
                _matrices.column(c)
                time.sleep(0.001)
            for c in range(21,-1,-1):
                _matrices.column(c)
                time.sleep(0.001)
        time.sleep(0.5)
        _matrices.clear()

    except KeyboardInterrupt:
        _log.info(Fore.MAGENTA + 'Ctrl-C caught: interrupted.')
    finally:
        _log.info('closing matrix test...')
        if _matrices:
            _matrices.clear()


# call main ......................................

def main():

    test_matrix()

if __name__== "__main__":
    main()

