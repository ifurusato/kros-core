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

import datetime as dt
from asyncio.queues import PriorityQueue
from colorama import init, Fore, Style
init()

from core.logger import Logger 
from core.controller import Controller 

# ..............................................................................
class Arbitrator(object):
    '''
    Arbitrates a stream of events from a MessageBus according to priority,
    returning to a Controller when polled the highest priority of them.
    '''
    def __init__(self, level):
        super().__init__()
        self._log = Logger('arbitrator', level)
        self._queue       = PriorityQueue()
        self._suppressed  = False
        self._controllers = []
        self._log.info(Fore.MAGENTA + Style.DIM + 'ready.')

    # ..........................................................................
    def register_controller(self, controller: Controller):
        '''
        Registers the Controller with the Arbitrator. When a Payload appears
        from the MessageBus its callback(Payload) method is called.
        '''
        self._controllers.append(controller)
        self._log.info(Fore.MAGENTA + Style.DIM + 'registering controller: {}'.format(controller.name))

    # ..........................................................................
    def suppress(self, suppressed):
        '''
        When set True incoming events are suppressed.
        '''
        self._suppressed = suppressed
        self._log.info(Fore.MAGENTA + Style.DIM + 'suppressed: {}'.format(suppressed))

    # ..........................................................................
    async def arbitrate(self, payload):
        '''
        Arbitrates the addition of the payload into the priority queue.
        If suppressed the queue is cleared so that events don't accumulate.
        '''
        self._log.info(Fore.MAGENTA + Style.DIM + 'arbitrating payload: {}'.format(payload.event.name))
        if self._suppressed:
            self._queue.clear()
        else:
            _start_time = dt.datetime.now()
            self._log.info(Fore.MAGENTA + Style.DIM + 'putting payload: {} onto queue...'.format(payload.event.name))
            if len(self._controllers) > 0:
                await self._queue.put(( payload.priority, payload ))
                self._log.info(Fore.MAGENTA + Style.DIM + 'complete: put payload: {} onto queue: {} elements.'.format(payload.event.name, self._queue.qsize()))
                await self.trigger_callback()
                _delta = dt.datetime.now() - _start_time
                _elapsed_ms = int(_delta.total_seconds() * 1000)
                self._log.info(Fore.MAGENTA + Style.DIM + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
            else:
                self._log.info(Fore.MAGENTA + Style.DIM + 'no registered controllers: payload ignored.')

    # ..........................................................................
    async def trigger_callback(self):
        self._log.info(Fore.MAGENTA + Style.DIM + 'trigger callback.')
        _tuple = await self._queue.get()
        _payload = _tuple[1]
        for controller in self._controllers:
            controller.callback(_payload)

# EOF
