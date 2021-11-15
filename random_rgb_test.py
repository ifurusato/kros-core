#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#

import time
from colorama import init, Fore, Style
init(autoreset=True)

from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from core.orientation import Orientation
from hardware.i2c_scanner import I2CScanner
from hardware.irq_clock import IrqClock
from hardware.color import Color
from hardware.rgbmatrix import RgbMatrix, DisplayType, WipeDirection

_log = Logger('irq-clock-test', Level.INFO)

# main ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

def main():

    _irq_clock = None
    _log.info('starting test...')

    try:

        # read YAML configuration
        _level = Level.INFO
        _loader = ConfigLoader(_level)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _i2c_scanner = I2CScanner(_config, Level.WARN)
        if not _i2c_scanner.has_address([0x74, 0x77]):
            _log.warning('test ignored: no rgbmatrix displays found.')
            return
        _addresses = _i2c_scanner.get_int_addresses()
        _enable_port = 0x77 in _addresses
        _enable_stbd = 0x74 in _addresses

        _rgbmatrix = RgbMatrix(_enable_port, _enable_stbd, Level.INFO)
        _log.info('starting test...')
        _rgbmatrix.enable()
        _port_rgbmatrix = _rgbmatrix.get_rgbmatrix(Orientation.PORT)
        _stbd_rgbmatrix = _rgbmatrix.get_rgbmatrix(Orientation.STBD)

        _irq_clock = IrqClock(_config, level=Level.INFO)
        _irq_clock.add_callback(_rgbmatrix.random_update)

        _log.info('starting IRQ clock...')
        _irq_clock.enable()

        while True:
            _log.info(Fore.BLACK + 'waiting for clock toggle.')
            time.sleep(5.0)

    except KeyboardInterrupt:
        _log.info(Fore.RED + "caught Ctrl-C.")
    finally:
        if _irq_clock:
            _log.info("closing external clock...")
            if _irq_clock:
                _irq_clock.close()

if __name__== "__main__":
    main()

#EOF
