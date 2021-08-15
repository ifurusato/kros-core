#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-15
# modified: 2021-08-15
#
# This is a test class for the Integrated Front Sensor publisher.
#

import pytest
import sys, numpy, time, traceback
from datetime import datetime as dt
from math import isclose
from colorama import init, Fore, Style
init()

from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.logger import Logger, Level
from core.config_loader import ConfigLoader
#from hardware.i2c_scanner import I2CScanner, DeviceNotFound
from hardware.ifs import IntegratedFrontSensor
from hardware.ifs_publisher import IfsPublisher

_log = Logger('test', Level.INFO)
_ifs = None

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_ifs_publisher():
    _test_start_time = dt.now()
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
#       _ifs = IfsPublisher(_config, _message_bus, _message_factory, Level.INFO)
        _log.info('creating ifs...')
        _ifs = IntegratedFrontSensor(_config, message_bus=_message_bus, message_factory=_message_factory, level=_level)
        _log.info('starting test loop...')
        while True:

            _start_time = dt.now()

            # ..............................................
            _stbd_bmp = _ifs.poll_stbd_bumper()

#           _center = _ifs.poll_center_infrared()
#           if _center:
#               _log.info(Fore.YELLOW + 'response: {}'.format(_center))
#           else:
#               _log.info(Fore.YELLOW + Style.DIM + 'no response.')

            _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
            _log.info(Fore.YELLOW + 'stbd bmp response: {}'.format(_stbd_bmp))
            _log.info(Fore.BLACK + Style.BRIGHT + 'elapsed: {:d}ms'.format(_elapsed_ms))
            # ..............................................

            time.sleep(1.0)
        _log.info('exited loop.')
        time.sleep(1.0)

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
    except Exception as e:
        _log.error('{} encountered, exiting: {}'.format(type(e), e))
    finally:
        if _ifs is not None:
            _ifs.disable()
        pass

    _elapsed_ms = round(( dt.now() - _test_start_time ).total_seconds() * 1000.0)
    _log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():
    try:
        test_ifs_publisher()
    except Exception as e:
        print(Fore.RED + 'error in motor test: {}'.format(e) + Style.RESET_ALL)
        traceback.print_exc(file=sys.stdout)
    finally:
        pass

if __name__== "__main__":
    main()

#EOF
