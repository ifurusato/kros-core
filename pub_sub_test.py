#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2021-03-17
#
# See:          https://roguelynn.com/words/asyncio-true-concurrency/
# Source:       https://github.com/econchick/mayhem/blob/master/part-1/mayhem_10.py
# See also:     https://cheat.readthedocs.io/en/latest/python/asyncio.html
# And another:  https://codepr.github.io/posts/asyncio-pubsub/
#               https://gist.github.com/appeltel/fd3ddeeed6c330c7208502462639d2c9
#               https://www.oreilly.com/library/view/using-asyncio-in/9781492075325/ch04.html
#
# unrelated:
# Python Style Guide: https://www.python.org/dev/peps/pep-0008/
#

import pytest
import sys, traceback
from colorama import init, Fore, Style
init()

from core.config_loader import ConfigLoader
from core.logger import Logger, Level
from core.controller import Controller
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.publisher import Publisher
from core.subscriber import Subscriber
from core.event import Event

from mock.ifs_publisher import IfsPublisher
from mock.flood_publisher import FloodPublisher
#from mock.gamepad_publisher import GamepadPublisher

from mock.motor_configurer import MotorConfigurer
from mock.motors import Motors

# ..............................................................................
@pytest.mark.unit
def test_pub_sub():

    _message_bus = None
#   try:

    _log = Logger("test", Level.INFO)
    _log.info(Fore.BLUE + 'configuring pub-sub test...')

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _message_bus = MessageBus(Level.INFO)
    _message_factory = MessageFactory(_message_bus, Level.INFO)

    _controller = Controller(Level.INFO)
    _message_bus.register_controller(_controller)

    _publisher1  = IfsPublisher(_message_bus, _message_factory)
#   _publisher2  = FloodPublisher(_message_bus, _message_factory)
#   _publisher3  = GamepadPublisher(_config, _message_bus, _message_factory)

#   _subscriber1 = Subscriber('action', Fore.BLUE, _message_bus, Level.INFO)
#   _subscriber1.events = [ Event.SNIFF, Event.VIDEO ] # reacts to SNIFF and VIDEO

    _subscriber2 = Subscriber('infrared', Fore.GREEN, _message_bus, Level.INFO)
    _subscriber2.events = [ Event.INFRARED_PORT_SIDE, Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD, Event.INFRARED_STBD_SIDE ] # reacts to IR sensors

    _subscriber3 = Subscriber('bumper', Fore.YELLOW, _message_bus, Level.INFO)
    _subscriber3.events = [ Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD ] # reacts to bumpers

    _motors = None
    # add motor controller, reacts to STOP, HALT, BRAKE, INCREASE_SPEED and DECREASE_SPEED
#   _motor_configurer = MotorConfigurer(_config, _message_bus, enable_mock=True, level=Level.INFO)
#   _motors = _motor_configurer.get_motors()

    # ROAM is commonly accepted by all subscribers
#   _subscriber1.add_event(Event.ROAM)
    _subscriber2.add_event(Event.ROAM)
#   _subscriber3.add_event(Event.ROAM)
#   _motors.add_event(Event.ROAM)

#   _message_bus.print_publishers()
#   _message_bus.print_subscribers()

#   sys.exit(0)
#   if _motors:
#       _motors.enable()
    _message_bus.enable()

#   except Exception as e:
#       _log.error('error in pub-sub: {} / {}'.format(e, traceback.print_stack()))
#   finally:
    if _message_bus:
        _message_bus.close()
#       _log.info('successfully shutdown the message bus service.')

# main .........................................................................
def main():
    _log = Logger("main", Level.INFO)
#   try:
    test_pub_sub()
#   except KeyboardInterrupt:
#       _log.info('publish-subscribe interrupted')
#   except Exception as e:
#       _log.error('error in pub-sub: {} / {}'.format(e, traceback.print_stack()))
#   finally:
#       pass

# ........................
if __name__ == "__main__":
    main()

