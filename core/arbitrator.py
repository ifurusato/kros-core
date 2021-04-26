#!/usr/bin/env python3
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-02
# modified: 2021-04-26
#

import time
import datetime as dt

from asyncio.queues import Queue

from lib.logger import Logger 
from lib.event import Event

# ..............................................................................
class Arbitrator(object):
    '''
    Arbitrates a stream of events from a MessageBus according to priority,
    returning to a Controller when polled the highest priority of them.
    '''
    def __init__(self, level):
        super().__init__()
        self._log = Logger('arbitrator', level)
        self._idle_loop_count = 0
        self._loop_delay_sec = self._config.get('loop_delay_sec')
        self._ballistic_loop_delay_sec = self._config.get('ballistic_loop_delay_sec')
        self._queue       = asyncio.PriorityQueue()
        self._enabled = True
        self._closed = False
        self._suppressed = False
        self._log.info('ready.')

    # ..........................................................................
    def set_suppressed(self, suppressed):
        self._suppressed = suppressed
        self._log.info('suppressed: {}'.format(suppressed))

    # ..........................................................................
    def enable(self):
        self._log.info('enabled.')
        self._enabled = True

    # ..........................................................................
    def disable(self):
        self._log.info('disabled.')
        self._enabled = False

    # ..........................................................................
    def run(self):
        self._log.info('arbitrating tasks...')
        while self._enabled:
            _start_time = dt.datetime.now()
            if self._suppressed:
                # if suppressed just clear the queue so events don't build up
                self._queue.clear()
            else:
                _message = await self._queue.get()
                self._log.info('received message: {}.'.format(_message.name))

            _delta = dt.datetime.now() - _start_time
            _elapsed_ms = int(_delta.total_seconds() * 1000)
            self._log.info('{}ms elapsed.'.format(_elapsed_ms))
            time.sleep(self._loop_delay_sec)

        self._log.info('loop end.')

    # ..........................................................................
    def close(self):
        if self._closed:
            self._log.warning('already closed.')
            return
        self.disable()
        self._closed = False
        self._log.info('closed.')

# EOF
