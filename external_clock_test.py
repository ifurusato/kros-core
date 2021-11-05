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
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from hardware.external_clock import ExternalClock
from hardware.clock_subscriber import ClockSubscriber

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Recipient():
    def __init__(self, name, ext_clock):
        self._name = name
        self._ext_clock   = ext_clock
        self._log = Logger(name, Level.INFO)
        self._counter     = itertools.count()
        self._timestamp_a = dt.now()
        self._timestamp_b = dt.now()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def callback_a(self):
        _elapsed_ms = (dt.now() - self._timestamp_a).total_seconds() * 1000.0
#       _count = next(self._counter)
#       self._log.info('🍍 [{:d}] external callback A;\t'.format(_count) + Fore.YELLOW + ' {:7.4f}ms elapsed.'.format(_elapsed_ms))
        self._log.info('🍍 external callback A:\t' + Fore.YELLOW + ' {:7.4f}ms elapsed.'.format(_elapsed_ms))
        self._timestamp_a = dt.now()

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   def callback_b(self):
#       _elapsed_ms = (dt.now() - self._timestamp_b).total_seconds() * 1000.0
#       _count = next(self._counter)
#       self._log.info('🍒 [{:d}] external callback A;\t'.format(_count) + Fore.YELLOW + ' {:7.4f}ms elapsed.'.format(_elapsed_ms))
#       self._timestamp_b = dt.now()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def start_callback(self):
        self._log.info('🍐 start callback...')
        self._ext_clock.enable()


# main ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

def main():

    _ext_clock   = None
    _message_bus = None
    _log = Logger('ext-clock-test', Level.INFO)
    _log.info('starting test...')

    try:

        # read YAML configuration
        _level = Level.INFO
        _loader = ConfigLoader(_level)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _log.info('creating message bus...')
        _message_bus = MessageBus(_config, Level.INFO)
        _log.info('creating message factory...')
        _message_factory = MessageFactory(_message_bus, Level.INFO)

        _log.info('🌞 1. creating external clock...')
        _ext_clock = ExternalClock(_config, _message_bus, _message_factory, Level.INFO)

        _rx = Recipient('rx', _ext_clock)
        _log.info('🌞 2. creating clock subscribers...')
        _clock_sub_a = ClockSubscriber(_config, 'rxa', _message_bus, _rx.callback_a, Level.INFO)
#       _clock_sub_b = ClockSubscriber(_config, 'rxb', _message_bus, _rx.callback_b, Level.INFO)
#       _log.info('🌞 3. enabling subscribers...')
        _clock_sub_a.enable()
#       _clock_sub_b.enable()

#       _log.info('🌞 4. enabling external clock...')
#       _ext_clock.enable()

        _log.info('🌞 5. adding start callbacks...')
        _message_bus.add_callback_on_start(_rx.start_callback)

        _log.info('🌞 6. enabling message bus...')
        _message_bus.enable()
        _log.info('🌞 7. message bus enabled.')

#       while True:
#           _log.info(Fore.BLACK + 'waiting for clock toggle.')
#           time.sleep(5.0)

    except KeyboardInterrupt:
        _log.info(Fore.RED + "🍅 caught Ctrl-C.")
        if _message_bus:
            _message_bus.disable()
            _message_bus.close()
    finally:
        if _ext_clock:
            _log.info("closing external clock...")
            if _ext_clock:
                _ext_clock.close()

if __name__== "__main__":
    main()

