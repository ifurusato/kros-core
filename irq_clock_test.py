#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#

import itertools
from datetime import datetime as dt
import time
from colorama import init, Fore, Style
init(autoreset=True)

from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from hardware.irq_clock import IrqClock

_log = Logger('irq-clock-test', Level.INFO)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def callback_method():
    global _counter, _timestamp
    _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
    _log.info('[{:04d}] IRQ callback: '.format(next(_counter)) + Fore.YELLOW + ' {:7.4f}ms elapsed.'.format(_elapsed_ms))
    _timestamp = dt.now()

# main ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

def main():
    global _counter, _timestamp

    _irq_clock = None
    _log.info('starting test...')

    _counter   = itertools.count()
    _timestamp = dt.now()

    try:

        # read YAML configuration
        _level = Level.INFO
        _loader = ConfigLoader(_level)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _irq_clock = IrqClock(_config, Level.INFO)
        _irq_clock.add_callback(callback_method)

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

