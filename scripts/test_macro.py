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
# Creates a test Script from a haphazard list of Events interjected with
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
_log = Logger('test-macro', Level.INFO)
_kros = globals.get('kros')
if _kros:
    _start_time = dt.now()
    try:
        _log.info('found KROS! begin loading script...')

        _macro_publisher = _kros.get_macro_publisher()
        if _macro_publisher:

            _script = _macro_publisher.create_script('test', 'a test of the emergency broadcast system. Remember, this is only a test.')

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
            _log.info('loading...')
            _steps = 5
            for i in range(_steps):
                _duration_ms = 1000 + ( i * 1000 )
                if i % 2:
                    _event = _event_queue.poll()
                    _script.add_event(_event, _duration_ms)
                    _log.info('added event...')
                else:
                    _func = lambda: _log.info('n={}'.format(i))
                    _script.add_function(_func, _duration_ms)
                    _log.info('added function...')

        else:
            _log.warning('macro processor not available..')

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
    except Exception as e:
        _log.error('{} encountered, exiting: {}'.format(type(e), e))
        traceback.print_exc(file=sys.stdout)
    finally:
        _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
        _log.info('complete: elapsed: {:d}ms'.format(_elapsed_ms))

else:
    _log.error('KROS not available.')

#EOF
