#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-09-10
# modified: 2021-09-10
#
# Tests the TinyPICO being used as an external bumper handler using BHIP.
#

import pytest
import sys, itertools, traceback
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.orient import Orientation
from core.rate import Rate
from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from hardware.ext_bmp_publisher import ExternalBumperPublisher

_log = Logger('test', Level.INFO)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_external_bumper_publisher():

    _ebp = None
    _start_time = dt.now()

    try:

        # read YAML configuration
        _level = Level.INFO
        _loader = ConfigLoader(_level)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _log.info('creating message bus...')
        _message_bus = MessageBus(_config, _level)
        _log.info('creating message factory...')
        _message_factory = MessageFactory(_message_bus, _level)

        _ebp = ExternalBumperPublisher(_config, _message_bus, _message_factory, Level.INFO)
        _ebp._init()
 
        _log.info(Fore.YELLOW + '🌼 send enable...')
        _ebp.send_enable()
#       _ebp.enable()

#       _ebp.send_ack()

#       _log.info('starting message bus...')
#       _message_bus.enable()

        # ..............................
        _log.info('starting test...')
        _count = 0
        _counter = itertools.count()
        _hz = 1
        _rate = Rate(_hz, Level.ERROR)
        _port = _stbd = 0
        while True:
            _count = next(_counter)
#           _log.info(Fore.BLUE + '[{:d}] loop: port: {:5.2f}; stbd: {:5.2f} steps.'.format(_count, _port, _stbd))
            _log.info(Fore.BLACK + '[{:d}] loop.'.format(_count))
            _rate.wait()

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
    except Exception as e:
        _log.error('{} encountered, exiting: {}'.format(type(e), e))
    finally:
#       if _port_motor != None:
#           _port_motor.set_motor_power(0.0)
#       if _stbd_motor != None:
#           _stbd_motor.set_motor_power(0.0)
        if _ebp:
            _ebp.close()
        pass

    _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
    _log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():
    try:
        test_external_bumper_publisher()
    except Exception as e:
        print(Fore.RED + 'error in motor test: {}'.format(e) + Style.RESET_ALL)
        traceback.print_exc(file=sys.stdout)
    finally:
        pass

if __name__== "__main__":
    main()

#EOF
