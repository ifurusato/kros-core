#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#

import pigpio
import itertools
import os, sys, signal, time
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from core.component import Component
from hardware.external_clock import ExternalClock

_log = Logger('ext-clock-test', Level.INFO)
_ext_clock    = None
_x_modulo     = 1
_x_counter    = itertools.count()
_x_millis     = lambda: int(round(time.time() * 1000))
_x_start_time = _x_millis()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#def ext_callback_method(*args):
def ext_callback_method(gpio, level, tick):
    global _x_start_time
    _count = next(_x_counter)
    if _count % _x_modulo == 0.0:
        _now = _x_millis()
        _elapsed = _now - _x_start_time
        _x_start_time = _now
#       gpio  = args[0]
#       level = args[1]
#       tick  = args[2]
        print(Fore.BLUE + 'external callback; gpio: {}; level: {}; tick: {};\t'.format(gpio, level, tick, _elapsed) 
                + Fore.YELLOW + ' {:6.3f}ms elapsed.'.format(_elapsed) + Style.RESET_ALL)

# main ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

def main():

    _log.info('starting test...')
    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

#       _pin = 6
#       _ext_clock = ExternalClock(_config)
        _ext_clock = ExternalClock(_config, ext_callback_method)
        _ext_clock.enable()

        while True:
            _log.info(Fore.BLACK + 'waiting for clock toggle.')
            time.sleep(5.0)

    except KeyboardInterrupt:
        _log.info(Fore.RED + "caught Ctrl-C.")
    finally:
        if _ext_clock:
            _log.info("closing external clock...")
            if _ext_clock:
                _ext_clock.close()

if __name__== "__main__":
    main()

