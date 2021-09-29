#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2021-09-23
# modified: 2021-09-23
#

#from collections import deque as Deque
import asyncio
import itertools
from datetime import datetime as dt
from colorama import init, Fore, Style
init(autoreset=True)

from core.logger import Logger, Level
from core.scripts import Scripts, Script, Statement
from core.event import Event
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
    :param callback:          the optional callback to trigger upon completion
    :param level:             the log level
    '''
    def __init__(self, config, message_bus, message_factory, callback=None, level=Level.INFO):
        if not isinstance(level, Level):
            raise ValueError('wrong type for log level argument: {}'.format(type(level)))
        self.__callbacks        = []
        self.__scripts          = {}
        if callback:
            self.add_callback(callback)
        self._level             = level
        Publisher.__init__(self, MacroProcessor.CLASS_NAME, config, message_bus, message_factory, level=self._level)
        _cfg = config['kros'].get('publisher').get('macro')
        _loop_freq_hz           = _cfg.get('loop_freq_hz')
        self._loop_delay_sec = 1.0 / _loop_freq_hz
        self._log.info('loop frequency: {} Hz.'.format(_loop_freq_hz))
        _quiescent_loop_freq_hz = _cfg.get('quiescent_loop_freq_hz')
        self._quiescent_delay_sec = 1.0 / _quiescent_loop_freq_hz
        self._log.info('quiescent loop frequency: {} Hz.'.format(_quiescent_loop_freq_hz))
        self._wait_limit_ms     = _cfg.get('wait_limit_ms') # the longest we will ever wait for anything
        self._log.info('wait limit: {:d}ms.'.format(self._wait_limit_ms))
        self._scripts           = Scripts()
        self._counter           = itertools.count()
        # loop variables
        self._script            = None
        self._statement         = None # placeholder
        self._start_time        = dt.now()
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'macro'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def create_script(self, name):
        '''
        Creates a new, empty script with the provided name, returning it to be
        populated.
        '''
        return Script(name)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def queue_script(self, script):
        '''
        Adds the script to the executable queue/stack.
        '''
        self._scripts.put(script)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_callback(self, callback):
        '''
        Adds a callback to those triggered at the end of a macro.
        '''
        self.__callbacks.append(callback)

     # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def remove_callback(self, callback):
        '''
        Removes a callback from those triggered at the end of a macro.
        '''
        self.__callbacks.remove(callback)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        self._log.warning('🌸 enable...')
        Publisher.enable(self)
        if self.enabled:
            if self._message_bus.get_task_by_name(MacroProcessor._LISTENER_LOOP_NAME):
                self._log.warning('🌸 already enabled.')
            else:
                self._log.info('🌸 creating task for macro processor loop... (enabled? {})'.format(self.enabled))
                self._message_bus.loop.create_task(self._macro_listener_loop(lambda: self.enabled), name=MacroProcessor._LISTENER_LOOP_NAME)
                self._log.info('🌸 enabled: macro loop task created.')
        else:
            self._log.warning('🌸 failed to enable macro processor.')
        self._log.warning('🌸 enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _macro_listener_loop(self, f_is_enabled):
        '''
        We poll the queue for statement, and then wait until the requisite
        amount of time has passed, then either publish the Statement's Event
        or process its lambda.
        '''
        self._log.info('🌸 starting macro listener loop.')
        while f_is_enabled():

            # check if there's either a running script or one available
            if self._script or not self._scripts.empty(): # either we have a script or there is one available
                _count = next(self._counter)
                if not self._script: # if we don't have a current script, pop one from the stack
                    self._script = self._scripts.get()
                # otherwise continue to execute the existing script...
                if not self._statement: # if no existing statement, poll one from the script.
                    self._statement = self._script.poll()
                    self._log.info(Fore.CYAN + 'event: ' + Fore.YELLOW + '{}:\t'.format(self._statement.label) + Fore.MAGENTA + 'duration: {:5.2f}ms'.format(self._statement.duration_ms))
                    self._start_time = dt.now()
                # if there is an active statement waiting...
                if self._statement:
                    # then process this statement...
                    _elapsed_ms = (dt.now() - self._start_time).total_seconds() * 1000.0
                    if _elapsed_ms < self._statement.duration_ms and _elapsed_ms < self._wait_limit_ms:
                        # if the elapsed time is less than the required delay keep waiting...
                        _elapsed_ms = (dt.now() - self._start_time).total_seconds() * 1000.0
                        self._log.info(Fore.CYAN + Style.DIM + 'e. still waiting on event: ' + Fore.YELLOW + '{}:\t'.format(self._statement.label)
                                + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
                    else:
                        # then execute the statement...
                        if self._statement.is_lambda:
                            _func = self._statement.function
                            self._log.info(Fore.GREEN + '🌸 f. executing lambda: ' + Fore.YELLOW + '{}: (type: {})\t'.format(self._statement.label, type(_func)) + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
                            _func()
                        else:
                            _event = self._statement.event
                            self._log.info(Fore.GREEN + '🌸 g. publishing event:  ' + Fore.YELLOW + '{}:\t'.format(self._statement.label) + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
                            _message = self.message_factory.create_message(_event, self._statement.duration_ms)
                            if _message is not None:
                                self._log.info(Style.BRIGHT + '🌸 h. macro-publishing message:' + Fore.WHITE + Style.NORMAL + ' {}'.format(_message.name)
                                        + Fore.CYAN + ' event: {}; '.format(_message.event.label) + Fore.YELLOW + 'timestamp: {}'.format(_message.value))
                                await Publisher.publish(self, _message)
                                self._log.info(Style.BRIGHT + '🌸 i. macro-published message:' + Fore.WHITE + Style.NORMAL + ' {}'.format(_message.name)
                                        + Fore.CYAN + ' event: {}; '.format(_message.event.label) + Fore.YELLOW + 'timestamp: {}'.format(_message.value))
                        # end loop
                        self._statement = None
                else: # no statement so we do nothing...
                    self._log.info(Fore.BLUE + '🌸 l. no active statement.')
                    pass

                if not self._statement and self._script.empty():
                    # we're finished with that script, so execute any callbacks...
                    for _callback in self.__callbacks:
                        self._log.info('⛅ n. executing callback...')
                        _callback()
                    self.__callbacks.clear()
                    self._script = None

                # loop sleep ............................
                await asyncio.sleep(self._loop_delay_sec)
            else:
                # we just wait quietly for a script to show up.
                await asyncio.sleep(self._quiescent_delay_sec)

        # end of while loop ........................
        self._log.info('🍙 z. macro publish loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher as well as shut down the message bus.
        '''
        Publisher.disable(self)
        self._log.info('disabled macro processor.')

#EOF
