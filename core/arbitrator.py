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

import asyncio, heapq
import time
import datetime as dt

from asyncio.queues import Queue

from core.logger import Logger 
from core.event import Event

# ..............................................................................
class Arbitrator(object):
    '''
    Arbitrates a stream of events from a MessageBus according to priority,
    returning to a Controller when polled the highest priority of them.
    '''
    def __init__(self, level):
        super().__init__()
        self._log = Logger('arbitrator', level)
        self._queue      = asyncio.PriorityQueue()
        self._enabled    = True
        self._closed     = False
        self._suppressed = False
        self._log.info(Fore.BLUE + 'ready.')

    # ..........................................................................
    def suppress(self, suppressed):
        self._suppressed = suppressed
        self._log.info(Fore.BLUE + 'suppressed: {}'.format(suppressed))

    # ..........................................................................
    def enable(self):
        self._log.info(Fore.BLUE + 'enabled.')
        self._enabled = True

    # ..........................................................................
    def disable(self):
        self._log.info(Fore.BLUE + 'disabled.')
        self._enabled = False

    # ..........................................................................
    async def arbitrate(self, payload):
        self._log.info(Fore.BLUE + 'arbitrating payload: {}.'.format(payload.event.name))
        _start_time = dt.datetime.now()
        if self._suppressed:
            # if suppressed just clear the queue so events don't build up
            self._queue.clear()
        else:
            self._log.info(Fore.BLUE + 'putting payload: {} onto queue...'.format(payload.event.name))
            await self._queue.put(payload)
            _smallest = heapq.nsmallest(1, self._queue)
            _largest  = heapq.nlargest(1, self._queue)
            self._log.info(Fore.BLUE + 'complete: put payload: {} onto queue; smallest: {}; largest: {}'.format(payload.event.name, _smallest, _largest))

        _delta = dt.datetime.now() - _start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        self._log.info(Fore.BLUE + '{}ms elapsed.'.format(_elapsed_ms))

    # ..........................................................................
    def close(self):
        if self._closed:
            self._log.warning('already closed.')
            return
        self.disable()
        self._closed = False
        self._log.info(Fore.BLUE + 'closed.')

# EOF
