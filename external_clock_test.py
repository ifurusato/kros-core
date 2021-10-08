#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#

import itertools
from datetime import datetime as dt
import os, sys, signal, time
from colorama import init, Fore, Style
init(autoreset=True)

from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from core.component import Component
from hardware.external_clock import ExternalClock

_log = Logger('ext-clock-test', Level.INFO)
_ext_clock    = None
_modulo       = 1
#_slow_modulo  = 1
_x_counter    = itertools.count()
_timestamp    = dt.now()
#_slow_timestamp    = dt.now()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def ext_callback_method():
    global _timestamp
    _count = next(_x_counter)
    if _count % _modulo == 0.0:
        _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
        print(Fore.BLUE + 'external callback;\t' + Fore.YELLOW + ' {:7.4f}ms elapsed.'.format(_elapsed_ms))
        _timestamp = dt.now()

## ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#def ext_slow_callback_method():
#    global _slow_timestamp
#    _count = next(_x_counter)
#    if _count % _slow_modulo == 0.0:
#        _elapsed_ms = (dt.now() - _slow_timestamp).total_seconds() * 1000.0
#        print(Fore.GREEN + 'external slow callback;\t' + Fore.YELLOW + ' {:7.4f}ms elapsed.'.format(_elapsed_ms))
#        _slow_timestamp = dt.now()

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
        _ext_clock = ExternalClock(_config)
        _ext_clock.add_callback(ext_callback_method)
#       _ext_clock.add_slow_callback(ext_slow_callback_method)
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

