#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2021-09-23
# modified: 2021-99-23
#

#from collections import deque as Deque
import sys
import time
from datetime import datetime as dt
from colorama import init, Fore, Style
init(autoreset=True)

#from upy.queue import Queue
from core.dequeue import DeQueue
from core.event import Event
from core.rate import Rate


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Statement(object):
    '''
    Documentation.
    '''
    def __init__(self, label, duration_ms, command):
        '''
        Command can be either a lambda or an Event.
        '''
        self._label       = label
        self._duration_ms = duration_ms
        if isinstance(command, Event):
            self._event   = command
        elif callable(command): # is lambda
            self._event   = Event.LAMBDA
            # LAMBDA = ( 20, "lambda function", 5,   Group.LAMBDA ) # with lambda as value
        else:
            raise TypeError('expected an event or a lambda as an argument, not a {}'.format(type(command)))

    @property
    def label(self):
        return self._label

    @property
    def duration_ms(self):
        return self._duration_ms

    @property
    def event(self):
        return self._event
       
    def __lt__(self, other):
        return self.__hash__() < other.__hash__()

    def __hash__(self):
        return hash(self._event)

    def __eq__(self, other):
        return isinstance(other, Statement) and self.__hash__() is other.__hash__()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MacroProcessor(object):
    '''
    Documentation.
    '''
    def __init__(self):
        pass



# main .........................................................................

print(Fore.CYAN + '🍓 begin.' )

_event_queue = DeQueue(mode=DeQueue.QUEUE)
#_event_queue.put(Event.SLOW_AHEAD)
#_event_queue.put(Event.STOP)
#_event_queue.put(Event.SPIN_STBD)
#_event_queue.put(Event.EVEN)
#_event_queue.put(Event.HALT)
#_event_queue.put(Event.SHUTDOWN)
_event_queue.put(Event.EXPERIMENT_1)
_event_queue.put(Event.EXPERIMENT_2)
_event_queue.put(Event.EXPERIMENT_3)
_event_queue.put(Event.EXPERIMENT_4)
_event_queue.put(Event.EXPERIMENT_5)

#while not _event_queue.empty():
#    _peeked = _event_queue.peek()
#    _ev     = _event_queue.pop()
#    _ev     = _event_queue.get()
#    _ev     = _event_queue.poll()
#    print('peeked: {}; popped: {}'.format(_peeked.label, _ev.label))
#sys.exit(0)

_queue_limit = 20
_queue = DeQueue(maxsize=_queue_limit, mode=DeQueue.QUEUE)

_wait_limit_ms = 5000 # the longest we will ever wait for anything (because we are impatient)

_hertz = 1
_rate = Rate(_hertz)

print(Fore.CYAN + '🍓 2.' )
_steps = 5
for i in range(_steps):
    print(Fore.CYAN + '🍓 3.' )
    _duration_ms = 1000 + ( i * 1000 )
    if i % 2:
        _func = _event_queue.poll()
    else:
        _func = lambda: print('n={}'.format(i))


#     # name      n   label       priority  group
#     LAMBDA = ( 20, "lambda function", 5,  Group.LAMBDA )


    _statement = Statement('cmd-{:d}'.format(i), _duration_ms, _func)
    _queue.put(_statement)

print(Fore.CYAN + '🍓 4.' )

while not _queue.empty():

    print(Fore.CYAN + '🍓 5.' )
    # poll queue and wait until elaped time is greater than the value of the statement
    _stmt = _queue.poll()
    _duration_ms = _stmt.duration_ms
    print(Fore.CYAN + 'command:                  ' + Fore.YELLOW + '{}:\t'.format(_stmt.label) + Fore.MAGENTA + 'duration: {:5.2f}ms'.format(_duration_ms))

    # now loop until the elapsed time has passed
    _start_time = dt.now()
    _elapsed_ms = (dt.now() - _start_time).total_seconds() * 1000.0
    print(Fore.CYAN + Style.DIM + '1st waiting on command:   ' + Fore.YELLOW + '{}:\t'.format(_stmt.label) + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
    while _elapsed_ms < _duration_ms and _elapsed_ms < _wait_limit_ms:
        _elapsed_ms = (dt.now() - _start_time).total_seconds() * 1000.0
        print(Fore.CYAN + Style.DIM + 'still waiting on command: ' + Fore.YELLOW + '{}:\t'.format(_stmt.label) + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
        _rate.wait()

    _func = _stmt.command
    if isinstance(_func, Event): 
        print(Fore.GREEN + 'executing event:          ' + Fore.YELLOW + '{}:  \t'.format(_func.label) + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
    else:
        print(Fore.GREEN + 'executing command:        ' + Fore.YELLOW + '{}:\t'.format(_stmt.label) + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
        _func()

    # end loop ...................................

print(Fore.CYAN + 'complete.' )

