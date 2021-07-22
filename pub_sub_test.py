#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2021-07-06
#
#   A test of the publish-subscribe message bus. Ultimately this ends up
#   as functionality executed from within kros.py, so that's really where
#   it all comes together.
#
# See:          https://roguelynn.com/words/asyncio-true-concurrency/
# Source:       https://github.com/econchick/mayhem/blob/master/part-1/mayhem_10.py
# See also:     https://cheat.readthedocs.io/en/latest/python/asyncio.html
# And another:  https://codepr.github.io/posts/asyncio-pubsub/
#               https://gist.github.com/appeltel/fd3ddeeed6c330c7208502462639d2c9
#               https://www.oreilly.com/library/view/using-asyncio-in/9781492075325/ch04.html
# unrelated:
# Python Style Guide: https://www.python.org/dev/peps/pep-0008/
#

import sys, traceback
import pytest
from colorama import init, Fore, Style
init()

from core.config_loader import ConfigLoader
from core.logger import Logger, Level
from core.controller import Controller
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.publisher import Publisher
from core.subscriber import Subscriber, GarbageCollector
from core.event import Event

from mock.motor_configurer import MotorConfigurer
from mock.event_publisher import EventPublisher
from mock.motor_subscriber import MotorSubscriber
from mock.bumper_subscriber import BumperSubscriber
from mock.infrared_subscriber import InfraredSubscriber
#from mock.gamepad_publisher import GamepadPublisher
#from mock.gamepad_controller import GamepadController

#from behave.behaviour_manager import BehaviourManager
#from behave.roam import Roam
#from behave.moth import Moth
#from behave.sniff import Sniff
#from behave.idle import Idle

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_pub_sub():

    _message_bus = None

    _level = Level.INFO
    _log = Logger("test", _level)
    _log.info(Fore.BLUE + 'configuring pub-sub test...')
    # read YAML configuration
    _config = ConfigLoader().configure()
    _message_bus = MessageBus(Level.INFO)
    _message_factory = MessageFactory(_message_bus, Level.INFO)

    _controller = Controller(_message_bus, Level.INFO)
#    _gp_controller = GamepadController(Level.WARN)
#    _message_bus.register_controller(_gp_controller)

    # add motor controller
    _motor_configurer = MotorConfigurer(_config, _message_bus, enable_mock=True, level=Level.WARN)
    _motors = _motor_configurer.get_motors()

    _event_publisher = EventPublisher(_config, _message_bus, _message_factory, _motors, level=_level)
#   _gamepad_publisher = GamepadPublisher(_config, _message_bus, _message_factory)

    # create subscribers
    _mtr_sub = MotorSubscriber(_config, _message_bus, _motors, level=_level)
    _bmp_sub = BumperSubscriber(_config, _message_bus, _motors, level=_level) # reacts to bumpers
    _ir_sub  = InfraredSubscriber(_config, _message_bus, _motors, level=_level)
    _gc      = GarbageCollector(_config, _message_bus, level=_level)
#   _bm      = BehaviourManager(_message_bus, level=_level) # a specialised subscriber

    # create and register behaviours (these are listed in priority order)
#   _roam  = Roam(_config, _message_bus, _message_factory, _motors, _level)
#   _moth  = Moth(_config, _message_bus, _motors, _level)
#   _sniff = Sniff(_config, _message_bus, _motors, _level)
#   _idle  = Idle(_config, _message_bus, _motors, _level)

#   _message_bus.print_publishers()
#   _message_bus.print_subscribers()

    if _motors:
        _motors.enable()
    _message_bus.enable()

    if _message_bus:
        _message_bus.close()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():
    test_pub_sub()

if __name__ == "__main__":
    main()

#EOF
