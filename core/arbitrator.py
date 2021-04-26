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
        self._log.info(Fore.MAGENTA + 'ready.')

    # ..........................................................................
    def register_controller(self, controller: Controller):
        '''
        Registers the Controller with the Arbitrator. When a Payload appears
        from the MessageBus its callback(Payload) method is called.
        '''
        self._controllers.append(controller)

    # ..........................................................................
    def suppress(self, suppressed):
        '''
        When set True incoming events are suppressed.
        '''
        self._suppressed = suppressed
        self._log.info(Fore.MAGENTA + 'suppressed: {}'.format(suppressed))

    # ..........................................................................
    async def arbitrate(self, payload):
        self._log.info(Fore.MAGENTA + 'arbitrating payload: {}.'.format(payload.event.name))
        _start_time = dt.datetime.now()
        if self._suppressed:
            # if suppressed just clear the queue so events don't build up
            self._queue.clear()
        else:
            self._log.info(Fore.MAGENTA + 'putting payload: {} onto queue...'.format(payload.event.name))
            if len(self._controllers > 0):
                await self._queue.put(( payload.priority, payload ))
                self._log.info(Fore.MAGENTA + 'complete: put payload: {} onto queue: {} elements.'.format(payload.event.name, self._queue.qsize()))
                trigger_callback()
            else:
                self._log.info(Fore.MAGENTA + 'no registered controllers: payload ignored.')


        _delta = dt.datetime.now() - _start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        self._log.info(Fore.MAGENTA + '{}ms elapsed.'.format(_elapsed_ms))

    # ..........................................................................
    def trigger_callback(self):
        self._log.info(Fore.MAGENTA + 'trigger callback.')
        _payload = self._queue.get()
        for controller in self._controllers:
            controller.callback(payload)

# EOF
