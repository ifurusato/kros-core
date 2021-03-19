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

from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.async_message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.publisher import Publisher
from lib.subscriber import Subscriber
from lib.event import Event

# main .........................................................................
def main():

    _log = Logger("main", Level.INFO)
    _log.info(Fore.BLUE + 'configuring pub-sub test...')

    _message_factory = MessageFactory(Level.INFO)

    _message_bus = MessageBus(Level.INFO)
    _publisher1  = Publisher('A', _message_bus, _message_factory, Level.INFO)
    _message_bus.register_publisher(_publisher1)
    _publisher2  = Publisher('B', _message_bus, _message_factory, Level.INFO)
    _message_bus.register_publisher(_publisher2)

    _subscriber1 = Subscriber('1-stop', Fore.YELLOW, _message_bus, [ Event.STOP, Event.SNIFF ], Level.INFO) # reacts to STOP
    _message_bus.register_subscriber(_subscriber1)
    _subscriber2 = Subscriber('2-infrared', Fore.MAGENTA, _message_bus, [ Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD ], Level.INFO) # reacts to IR
    _message_bus.register_subscriber(_subscriber2)
    _subscriber3 = Subscriber('3-bumper', Fore.GREEN, _message_bus, [ Event.SNIFF, Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD ], Level.INFO) # reacts to bumpers
    _message_bus.register_subscriber(_subscriber3)

    _message_bus.print_publishers()
    _message_bus.print_subscribers()

    try:
        _message_bus.enable()
    except KeyboardInterrupt:
        _log.info('publish-subscribe interrupted')
    except Exception as e:
        _log.error('error in publish-subscribe: {}'.format(e))
    finally:
        _message_bus.close()
        _log.info('successfully shutdown the message bus service.')

# ........................
if __name__ == "__main__":
    main()

