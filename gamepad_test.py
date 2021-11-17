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
from hardware.gamepad_publisher import GamepadPublisher
from hardware.gamepad_controller import GamepadController

_log = Logger('gamepad-test', Level.INFO)
_gamepad_pub = None
_gamepad_controller = None

try:

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

#   _log.heading('test', 'starting gamepad demo...', None)

    _log.info('creating message bus...')
    _message_bus = MessageBus(_config, Level.INFO)
    _log.info('creating message factory...')
    _message_factory = MessageFactory(_message_bus, Level.INFO)

    _log.info('creating gamepad publisher...')
    _gamepad_pub = GamepadPublisher(_config, _message_bus, _message_factory, level=Level.INFO)

    _log.info('creating gamepad controller...')
    _gamepad_controller = GamepadController(_message_bus, Level.INFO)

    _log.info('enabling message bus...')
    _message_bus.enable()

    _log.info('enabling gamepad publisher...')
    _gamepad_pub.enable()
    while _gamepad_pub.enabled:
        time.sleep(1.0)
    _log.info('exited loop.')
    time.sleep(1.0)

except KeyboardInterrupt:
    _log.info('caught Ctrl-C; exiting...')
    if _gamepad_pub:
        _gamepad_pub.disable()
except OSError:
    _log.error('unable to connect to gamepad')
except Exception:
    _log.error('error processing gamepad events: {}'.format(traceback.format_exc()))
finally:
    _log.info('closing...')
    time.sleep(1.0)
    if _gamepad_pub:
        _gamepad_pub.disable()
        _gamepad_pub.close()
    if _gamepad_controller:
        _gamepad_controller.close()
    time.sleep(1.0)
    _log.info('complete.')

# EOF
