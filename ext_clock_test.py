#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-10-31
# modified: 2021-10-31
#

import itertools
from datetime import datetime as dt
import os, sys, signal, time
from colorama import init, Fore, Style
init(autoreset=True)

from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from hardware.external_clock import ExternalClock
from hardware.clock_subscriber import ClockSubscriber

from hardware.irq_clock import IrqClock

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Recipient():
    def __init__(self):
        self._log = Logger('rx', Level.INFO)
        self._counter = itertools.count()
        self._last_timestamp = dt.now()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def callback(self):
        _elapsed_ms = (dt.now() - self._last_timestamp).total_seconds() * 1000.0
        _count = next(self._counter)
        self._log.info('[{:04d}] callback:\t'.format(_count) + Fore.YELLOW + ' {:7.4f}ms elapsed.'.format(_elapsed_ms))
        self._last_timestamp = dt.now()


# main ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

def main():

    _ext_clock   = None
    _log = Logger('ext-clock-test', Level.INFO)
    _log.info('starting test...')

    try:

        # read YAML configuration
        _config = ConfigLoader(Level.INFO).configure()

        _pin = 5
        _log.info('creating external clock on pin {:d}...'.format(_pin))
        _irq_clock = IrqClock(_config, _pin, Level.INFO)

        _rx = Recipient()
        _irq_clock.add_callback(_rx.callback)
        _irq_clock.enable()
        _log.info('external clock enabled.')

        while True:
            _log.info(Fore.BLACK + 'waiting for clock toggle.')
            time.sleep(5.0)

    except KeyboardInterrupt:
        _log.info(Fore.RED + 'caught Ctrl-C.')
    finally:
        if _irq_clock:
            _log.info('closing external clock...')
            if _irq_clock:
                _irq_clock.close()

if __name__== "__main__":
    main()

