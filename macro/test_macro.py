#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2021-09-29
# modified: 2021-09-29
#
# Creates a test Macro from a haphazard list of Events interjected with
# lambdas.
#

import sys, traceback
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

import core.globals as globals
from core.logger import Logger, Level
from core.dequeue import DeQueue

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_test_log = Logger('test-macro', Level.ERROR)
_kros = globals.get('kros')
if _kros:
    _start_time = dt.now()
    try:
        _test_log.info('found KROS! begin loading macro...')

        _macro_publisher = _kros.get_macro_publisher()
        if _macro_publisher:

            _macro = _macro_publisher.create_macro('test', 'a test of the emergency broadcast system. Remember, this is only a test.')

            # load event queue
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
            _test_log.info('loading...')
            _steps = 5
            for i in range(_steps):
                _duration_ms = 1000 + ( i * 1000 )
                if i % 2:
                    _event = _event_queue.poll()
                    _macro.add_event(_event, _duration_ms)
                    _test_log.info('added event...')
                else:
                    _func = lambda: _test_log.info('n={}'.format(i))
                    _macro.add_function(_func, _duration_ms)
                    _test_log.info('added function...')

        else:
            _test_log.warning('macro processor not available..')

    except KeyboardInterrupt:
        _test_log.info('Ctrl-C caught; exiting...')
    except Exception as e:
        _test_log.error('{} encountered, exiting: {}'.format(type(e), e))
        traceback.print_exc(file=sys.stdout)
    finally:
        _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
        _test_log.info('complete: elapsed: {:d}ms'.format(_elapsed_ms))

else:
    _test_log.error('KROS not available.')

#EOF
