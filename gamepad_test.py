#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-05
# modified: 2020-08-08
#
# This is a test class using the 8BitDo N30 Pro Gamepad, a paired Bluetooth 
# device to control the KR01.
#

import sys, time, traceback, threading
from colorama import init, Fore, Style
init()

from core.config_loader import ConfigLoader
from core.logger import Logger, Level
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from mock.gamepad_publisher import GamepadPublisher

_log = Logger('gamepad-test', Level.INFO)
_gamepad_pub = None

try:

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _log.heading('test', 'starting gamepad demo...', None)

    _message_bus = MessageBus(Level.INFO)
    _message_factory = MessageFactory(_message_bus, Level.INFO)

    _gamepad_pub = GamepadPublisher(_config, _message_bus, _message_factory, Level.INFO)
    _gamepad_pub.enable()
    while _gamepad_pub.enabled:
        time.sleep(1.0)
    _log.info('exited loop.')
    time.sleep(1.0)

except KeyboardInterrupt:
    _log.info('caught Ctrl-C; exiting...')
    if _gamepad_pub is not None:
        _gamepad_pub.disable()
except OSError:
    _log.error('unable to connect to gamepad')
except Exception:
    _log.error('error processing gamepad events: {}'.format(traceback.format_exc()))
finally:
    _log.info('closing...')
    time.sleep(1.0)
    if _gamepad_pub is not None:
        _gamepad_pub.disable()
        _gamepad_pub.close()
    time.sleep(1.0)
    _log.info('complete.')

# EOF
