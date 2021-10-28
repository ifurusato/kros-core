#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2021-09-23
# modified: 2021-09-28
#

import pytest
import sys, signal, time, traceback
from datetime import datetime as dt
from colorama import init, Fore, Style
init(autoreset=True)

from core.logger import Logger, Level
from core.dequeue import DeQueue
from core.event import Event
from core.queue_publisher import QueuePublisher
from core.config_loader import ConfigLoader
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.macro_publisher import MacroPublisher

from core.kr01_macrolibrary import KR01MacroLibrary


# main logger
_log = Logger('main', Level.INFO)

# exception handler ............................................................
def signal_handler(signal, frame):
    global _message_bus
    _log.info('🍇 Ctrl-C caught: exiting...')
    if _message_bus:
        _message_bus.close()
    else:
        _log.warning('🍇 signal_handler() no message bus available!')
    _log.info(Fore.CYAN + '🍇 exit.')
    sys.exit(0)

def callback_method():
    global _enabled, _message_bus
    _enabled = False
    _log.info('🍒 callback method: closing message bus...')
    if _message_bus:
        _message_bus.close()
        _log.info('🍒 message bus closed.')
    else:
        _log.warning('signal_handler() no message bus available!')

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def __blink__(message_bus):
    global _enabled
    _enabled = True
    _log.info(Fore.YELLOW + '🍋 blink: message bus enabled: {}; suppressed: {}'.format(message_bus.enabled, message_bus.suppressed))
    message_bus.enable()
    _log.info('🍋 blink complete.')

# ..............................................................................
@pytest.mark.unit
def test_macro_publisher():
    global _enabled, _message_bus

    _log = Logger('macro-pub-test', Level.INFO)
    _log.info('begin.')

    _start_time = dt.now()

    _enabled = True

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
        _queue_publisher = QueuePublisher(_config, _message_bus, _message_factory, _level)

        _macro_publisher = MacroPublisher(_config, _message_bus, _message_factory, _queue_publisher, callback=callback_method, level=Level.INFO)
        _loop_freq_hz = 1
        _macro_publisher.set_loop_frequency(_loop_freq_hz)

        _library = KR01MacroLibrary(_macro_publisher)
        _macro_publisher.set_macro_library(_library)
        
        _log.info(Fore.YELLOW + 'message bus enabled: {}; suppressed: {}'.format(_message_bus.enabled, _message_bus.suppressed))
        _log.info(Fore.YELLOW + 'macro publisher enabled: {}; suppressed: {}'.format(_macro_publisher.enabled, _macro_publisher.suppressed))

        _macro_name = 'test'
        _log.info('queuing \'{}\' macro...'.format(_macro_name))
        _macro_publisher.queue_macro_by_name(_macro_name)

        _message_bus.enable()

        _log.info('enabled, continuing...')

        while _enabled:
            _log.info(Fore.BLACK + 'waiting...')
            time.sleep(2.0)

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
    except Exception as e:
        _log.error('{} encountered, exiting: {}'.format(type(e), e))
        traceback.print_exc(file=sys.stdout)
    finally:
        _enabled = False
        _log.info('finally.')
        sys.exit(0)

    _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
    _log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))

    _log.info('complete.')

# call main ......................................

def main():

    signal.signal(signal.SIGINT, signal_handler)

    test_macro_publisher()

if __name__== "__main__":
    main()

#EOF
