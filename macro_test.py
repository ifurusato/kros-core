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
from datetime import datetime as dt
from colorama import init, Fore, Style

from core.logger import Logger, Level
from core.dequeue import DeQueue
from core.event import Event
from core.config_loader import ConfigLoader
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.macro import MacroProcessor

# ..............................................................................
@pytest.mark.unit
def test_macro_processor():

    _log = Logger('macro-test', Level.INFO)
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
        _log.info('creating message factory...')
        _message_factory = MessageFactory(_message_bus, _level)

        _mp = MacroProcessor(_config, _message_bus, _message_factory, statement_limit=-1, callback=None, level=Level.INFO)
        
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
        _log.info('loading...')
        _steps = 5
        for i in range(_steps):
            _duration_ms = 1000 + ( i * 1000 )
            if i % 2:
                _event = _event_queue.poll()
                _mp.add_event(_event, _duration_ms)
                _log.info('added event...')
            else:
                _func = lambda: _log.info('n={}'.format(i))
                _mp.add_function(_func, _duration_ms)
                _log.info('added function...')
        
        _log.info('queue loaded; starting process...')
        _mp.start()

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
    except DeviceNotFound as e:
        _log.error('no potentiometer found, exiting.')
    except Exception as e:
        _log.error('{} encountered, exiting: {}'.format(type(e), e))
    finally:
        pass

    _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
    _log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))
    
    _log.info('complete.')

# call main ......................................

def main():

    test_macro_processor()

if __name__== "__main__":
    main()

#EOF
