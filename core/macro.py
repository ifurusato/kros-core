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
from datetime import datetime as dt
from colorama import init, Fore, Style
init(autoreset=True)

from core.logger import Logger, Level
from core.dequeue import DeQueue
from core.event import Event
from core.rate import Rate
from core.publisher import Publisher

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MacroProcessor(Publisher):

    CLASS_NAME = 'macro'
    _LISTENER_LOOP_NAME = '__macro_listener_loop'

    '''
    A macro processor that schedules the future publication of a queue of
    pre-loaded Events. This can include existing Event types or lambda 
    functions wrapped in Events.

    :param config:            the application configuration
    :param message_bus:       the asynchronous message bus
    :param message_factory:   the factory for creating messages
    :param statement_limit:   optionally limits the size of the queue
    :param callback:          the optional callback to trigger upon completion
    :param level:             the log level
    '''
    def __init__(self, config, message_bus, message_factory, statement_limit=-1, callback=None, level=Level.INFO):
        if not isinstance(level, Level):
            raise ValueError('wrong type for log level argument: {}'.format(type(level)))
        self._level = level
        Publisher.__init__(self, MacroProcessor.CLASS_NAME, config, message_bus, message_factory, level=self._level)
#       self._log = Logger('macro', level)
        _cfg = config['kros'].get('publisher').get('macro')
        _loop_freq_hz           = _cfg.get('loop_freq_hz')
        self._publish_delay_sec = 1.0 / _loop_freq_hz
        self._log.info('publish loop frequency: {} Hz.'.format(_loop_freq_hz))
        _macro_loop_freq_hz     = _cfg.get('macro_loop_freq_hz')
        self._rate              = Rate(_macro_loop_freq_hz)
        self._log.info('macro loop frequency: {} Hz.'.format(_macro_loop_freq_hz))
        self._wait_limit_ms     = _cfg.get('wait_limit_ms') # the longest we will ever wait for anything
        self._log.info('wait limit: {:d}ms.'.format(self._wait_limit_ms))
        self._queue = DeQueue(maxsize=statement_limit, mode=DeQueue.QUEUE)
        self._statement         = None # placeholder
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if self._message_bus.get_task_by_name(MacroProcessor._LISTENER_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                self._log.info('creating task for macro processor loop...')
                self._message_bus.loop.create_task(self._macro_listener_loop(lambda: self.enabled), name=MacroProcessor._LISTENER_LOOP_NAME)
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable macro processor.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _macro_listener_loop(self, f_is_enabled):
        '''
        We poll the queue for statement, and then wait until the requisite
        amount of time has passed, then either publish the Statement's Event
        or process its lambda.
        '''
        self._log.info('starting macro listener loop.')
        while f_is_enabled():
            _count = next(self._counter)
            self._log.info('[{:d}] start processing queue...'.format(_count))

            if not self._statement:
                # poll queue and wait until elaped time is greater than the value of the statement
                self._statement = self._queue.poll()
                _duration_ms = self._statement.duration_ms
                self._log.info(Fore.CYAN + 'event: ' + Fore.YELLOW + '{}:\t'.format(self._statement.label) + Fore.MAGENTA + 'duration: {:5.2f}ms'.format(_duration_ms))
                # now loop until the elapsed time has passed
                _start_time = dt.now()
                _elapsed_ms = (dt.now() - _start_time).total_seconds() * 1000.0
                self._log.info(Fore.CYAN + Style.DIM + '1st waiting on event:   ' + Fore.YELLOW + '{}:\t'.format(self._statement.label) 
                        + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
            else:
                pass


            while _elapsed_ms < _duration_ms and _elapsed_ms < self._wait_limit_ms:
                _elapsed_ms = (dt.now() - _start_time).total_seconds() * 1000.0
                self._log.info(Fore.CYAN + Style.DIM + 'still waiting on event: ' + Fore.YELLOW + '{}:\t'.format(self._statement.label) 
                        + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
                self._rate.wait()


            _func = self._statement.event
            if self._statement.is_lambda:
                self._log.info(Fore.GREEN + 'executing lambda: ' + Fore.YELLOW + '{}:  \t'.format(_func.label) + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
        #       _func()
            else:
                self._log.info(Fore.GREEN + 'executing event:  ' + Fore.YELLOW + '{}:\t'.format(self._statement.label) + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
        #       _func()
            # end loop ...................................



            _message = self.message_factory.create_message(Event.BUMPER_MAST, self._mast_triggered)

            if _message is not None:
                self._log.info(Style.BRIGHT + 'bmp-publishing message:' + Fore.WHITE + Style.NORMAL + ' {}'.format(_message.name)
                        + Fore.CYAN + ' event: {}; '.format(_message.event.label) + Fore.YELLOW + 'timestamp: {}'.format(_message.value))
                await Publisher.publish(self, _message)

            await asyncio.sleep(self._publish_delay_sec)
            self._log.info('end of loop...')

        self._log.info('macro publish loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher as well as shut down the message bus.
        '''
        Publisher.disable(self)
        self._log.info('disabled macro processor.')

    # macro-specific methods ┈┈┈ ┈┈┈ ┈┈┈ ┈┈┈ ┈┈┈ ┈┈┈ ┈┈┈ ┈┈┈ ┈┈┈ ┈┈┈ ┈┈┈ ┈┈┈ ┈┈┈

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_event(self, event, duration_ms):
        '''
        '''
        _id = self._queue.size
        _statement = Statement('stmt-{:d}'.format(_id), event, duration_ms)
        self._queue.put(_statement)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_function(self, function, duration_ms):
        '''
        #     # name      n   label       priority  group
        #     LAMBDA = ( 20, "lambda function", 5,  Group.LAMBDA )
        '''
        _id = self._queue.size
        _statement = Statement('stmt-{:d}'.format(_id), function, duration_ms)
        self._queue.put(_statement)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def start(self):
        '''
        Starts processing the queue according to its schedule.
        '''
        self._log.info('start processing queue...')
        if self._queue.empty():
            self._log.warning('empty queue!')
            return
        while not self._queue.empty():
            self._log.info('start processing queue...')
            # poll queue and wait until elaped time is greater than the value of the statement
            _stmt = self._queue.poll()
            _duration_ms = _stmt.duration_ms
            self._log.info(Fore.CYAN + 'event: ' + Fore.YELLOW + '{}:\t'.format(_stmt.label) + Fore.MAGENTA + 'duration: {:5.2f}ms'.format(_duration_ms))
            # now loop until the elapsed time has passed
            _start_time = dt.now()
            _elapsed_ms = (dt.now() - _start_time).total_seconds() * 1000.0
            self._log.info(Fore.CYAN + Style.DIM + '1st waiting on event:   ' + Fore.YELLOW + '{}:\t'.format(_stmt.label) + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
            while _elapsed_ms < _duration_ms and _elapsed_ms < self._wait_limit_ms:
                _elapsed_ms = (dt.now() - _start_time).total_seconds() * 1000.0
                self._log.info(Fore.CYAN + Style.DIM + 'still waiting on event: ' + Fore.YELLOW + '{}:\t'.format(_stmt.label) 
                        + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
                self._rate.wait()
            _func = _stmt.event
            if _stmt.is_lambda:
                self._log.info(Fore.GREEN + 'executing lambda: ' + Fore.YELLOW + '{}:  \t'.format(_func.label) + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
        #       _func()
            else:
                self._log.info(Fore.GREEN + 'executing event:  ' + Fore.YELLOW + '{}:\t'.format(_stmt.label) + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
        #       _func()
            # end loop ...................................

        self._log.info('end of queue.')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Statement(object):
    '''
    Documentation.
    '''
    def __init__(self, label, command, duration_ms):
        '''
        Command can be either a lambda or an Event.
        '''
        self._label       = label
        self._duration_ms = duration_ms
        if isinstance(command, Event):
            self._is_lambda = False
            self._event   = command
        elif callable(command): # is lambda
            self._is_lambda = True
            self._event   = Event.LAMBDA
            # LAMBDA = ( 20, "lambda function", 5,   Group.LAMBDA ) # with lambda as value
        else:
            raise TypeError('expected an event or a lambda as an argument, not a {}'.format(type(command)))

    @property
    def label(self):
        return self._label

    @property
    def is_lambda(self):
        return self._is_lambda

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

#EOF
