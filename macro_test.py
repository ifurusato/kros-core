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
import sys, signal, traceback
from datetime import datetime as dt
from colorama import init, Fore, Style

from core.logger import Logger, Level
from core.dequeue import DeQueue
from core.event import Event
from core.config_loader import ConfigLoader
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.macro_publisher import MacroPublisher

# exception handler ............................................................
def signal_handler(signal, frame):
    global _message_bus
    print(Fore.RED + '🍇 Ctrl-C caught: exiting...' + Style.RESET_ALL)
    if _message_bus:
        _message_bus.disable()
        _message_bus.close()
    else:
        print('signal_handler() no message bus available!')
    print(Fore.CYAN + 'exit.' + Style.RESET_ALL)
    sys.exit(0)

def close_message_bus():
#   print('🍉 closing message bus...')
#   signal_handler(None, None)
    global _message_bus
    if _message_bus and _message_bus.is_running:
#       print('closing...')
        _message_bus.disable()
        _message_bus.close()
#       print('closed.')
    else:
        print('close() message bus already closed or not available!')
#   print('🍉 closed messag bus.')
#   sys.exit(0)

# ..............................................................................
@pytest.mark.unit
def test_macro_publisher():
    global _message_bus

    _log = Logger('macro-pub-test', Level.INFO)
    _log.info('begin.')
    
    _start_time = dt.now()

    try:

        # read YAML configuration
        _level = Level.INFO
        _loader = ConfigLoader(_level)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _log.info('creating message bus...')
        _message_bus = MessageBus(_config, _level)
        _log.info('🍅 creating message factory...')
        _message_factory = MessageFactory(_message_bus, _level)

        _macro_publisher = MacroPublisher(_config, _message_bus, _message_factory, callback=close_message_bus, level=Level.INFO)
        _script = _macro_publisher.create_script('test')
        
        _event_queue = DeQueue(mode=DeQueue.QUEUE)
    
        _event_queue.put(Event.SLOW_AHEAD)
        _event_queue.put(Event.STOP)
        _event_queue.put(Event.SPIN_STBD)
        _event_queue.put(Event.EVEN)
        _event_queue.put(Event.HALT)
        _event_queue.put(Event.SHUTDOWN)
        _event_queue.put(Event.EXPERIMENT_1)
        _event_queue.put(Event.EXPERIMENT_2)
        _event_queue.put(Event.EXPERIMENT_3)
        _event_queue.put(Event.EXPERIMENT_4)
        _event_queue.put(Event.EXPERIMENT_5)
        
        # alternately loads events and lambdas...
        _log.info('🍅 loading...')
        _steps = 5
        for i in range(_steps):
            _duration_ms = 1000 + ( i * 1000 )
            if i % 2:
                _event = _event_queue.poll()
                _script.add_event(_event, _duration_ms)
                _log.info('🍅 added event...')
            else:
                _func = lambda: _log.info('n={}'.format(i))
                _script.add_function(_func, _duration_ms)
                _log.info('🍅 added function...')

        _macro_publisher.queue_script(_script)

        _log.info('🍅 enabling message bus...')
        _message_bus.enable()

#       _log.info('🍅 queue loaded; enabling macro processor...')
#       _macro_publisher.enable()

        if _message_bus:
            _message_bus.close()

#       _log.info('queue loaded; starting process...')
#       _macro_publisher.start()

    except KeyboardInterrupt:
        _log.info('🍅 Ctrl-C caught; exiting...')
    except Exception as e:
        _log.error('🍅 {} encountered, exiting: {}'.format(type(e), e))
        traceback.print_exc(file=sys.stdout)
    finally:
        _log.info('🍅 finally.')
        close_message_bus()

    _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
    _log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))
    
    _log.info('🍅 complete.')

# call main ......................................

def main():

    signal.signal(signal.SIGINT, signal_handler)

    test_macro_publisher()

if __name__== "__main__":
    main()

#EOF
