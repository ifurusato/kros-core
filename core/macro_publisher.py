#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2021-09-23
# modified: 2021-10-15
#

import importlib
import sys, os, asyncio, itertools
from copy import deepcopy
from pathlib import Path
from datetime import datetime as dt
from colorama import init, Fore, Style
init(autoreset=True)

import core.globals as globals # needed for lambda support
globals.init()

from core.logger import Logger, Level
from core.system import System
from core.util import Util
from core.event import Event
from core.message import Message, Payload
from core.publisher import Publisher
from core.macros import MacroLibrary, Macros, Macro, Statement

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MacroPublisher(Publisher):

    CLASS_NAME = 'macro'
    _LISTENER_LOOP_NAME = '__macro_listener_loop'

    '''
    A macro publisher/processor that schedules the future publication of a
    queue of pre-loaded Events. This can include existing Event types or
    lambda functions wrapped in Events.

    :param config:            the application configuration
    :param message_bus:       the asynchronous message bus
    :param message_factory:   the factory for creating messages
    :param queue_publisher:   the queue publisher used to publish completion messages
    :param callback:          the optional callback to trigger upon completion
    :param level:             the log level
    '''
    def __init__(self, config, message_bus, message_factory, queue_publisher, callback=None, level=Level.INFO):
        if not isinstance(level, Level):
            raise ValueError('wrong type for log level argument: {}'.format(type(level)))
        self.__callbacks        = []
        if callback:
            self.add_callback(callback)
        self._level             = level
        Publisher.__init__(self, MacroPublisher.CLASS_NAME, config, message_bus, message_factory, level=self._level)
        self._queue_publisher   = queue_publisher
        _cfg = config['kros'].get('publisher').get('macro')
        _loop_freq_hz           = _cfg.get('loop_freq_hz')
        self._loop_delay_sec = 1.0 / _loop_freq_hz
        self._log.info('loop frequency: {} Hz.'.format(_loop_freq_hz))
        _quiescent_loop_freq_hz = _cfg.get('quiescent_loop_freq_hz')
        self._quiescent_delay_sec = 1.0 / _quiescent_loop_freq_hz
        self._log.info('quiescent loop frequency: {} Hz.'.format(_quiescent_loop_freq_hz))
        self._wait_limit_ms     = _cfg.get('wait_limit_ms') # the longest we will ever wait for anything
        self._log.info('wait limit: {:d}ms.'.format(self._wait_limit_ms))
        self._load_macros       = _cfg.get('load_macros')
        self._log.info('load macros? {}'.format(self._load_macros))
        self._macro_path        = _cfg.get('macro_path')
        self._log.info('macro path: {}'.format(self._macro_path))
        self._library           = MacroLibrary()
        self._macros            = Macros()
        self._counter           = itertools.count()
        # loop variables
        self._macro             = None
        self._statement         = None # placeholder
        self._start_time        = dt.now()
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'macro'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_info(self):
        self._library.print_info()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def create_macro(self, name, description=None):
        '''
        Creates a new, empty macro with the provided name, returning it to be
        populated. This automatically adds it to the macro library.
        '''
        _macro = Macro(name, description)
#       if self._log.level == Level.DEBUG:
        self._log.info('created macro: ' + Fore.YELLOW + '{}'.format(name))
#       self._log.info('created macro: ' + Fore.YELLOW + '{}:\n'.format(name) + Fore.CYAN + '{}'.format(_macro))
        self.add_macro_to_library(_macro)
        return _macro

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_macro_to_library(self, macro):
        '''
        Adds the macro to the macro library.
        '''
        if isinstance(macro, Macro):
            self._log.info('adding macro {} to library; {:d} items in library.'.format(macro.name, self._library.size))
            self._library.put(macro)
        else:
            raise TypeError('expected macro.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def queue_macro_by_name(self, name, payload=None):
        '''
        Adds the macro (referenced by name) to the executable queue/stack.

        :param name:      the name of the macro to queue from the library
        :param payload:   the optional message payload to attach to the macro
                          as an execution argument
        '''
        self._log.info('queueing macro: "{}"; '.format(name) + Fore.YELLOW + '{:d} items in library.'.format(self._library.size))
        self._original_macro = None
        self._original_macro = self._library.get(name)
        if self._original_macro:
            _copied_macro = deepcopy(self._original_macro)
            if _copied_macro.size != self._original_macro.size:
                self._log.warning('deep copy of macro failed: copy: {} != macro: {}'.format(_copied_macro.size, self._original_macro.size))
            else:
                if payload:
                    _copied_macro.set_payload(payload)
                self.queue_macro(_copied_macro)
                self._log.info('queued macro \'{}\': {:d} statements.'.format(_copied_macro.name, _copied_macro.size))
        else:
            self._log.warning('could not find macro \'{}\''.format(name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def has_macro(self, name):
        '''
        Returns True if a macro with the provided name is available.
        '''
        _macro = self._library.get(name)
        return _macro != None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def queue_macro(self, macro):
        '''
        Adds the macro to the executable queue/stack.
        '''
        self._macros.put(macro)

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
    def load_macro_files(self):
        '''
        Loads the *.py macro files from the ./macro/ directory by executing
        the files. If the macros use the create_macro() method the new macro
        will automatically be added to the macro library, otherwise the
        add_macro_to_library() method must be called.

        If called subsequently this will overwrite macros in the library
        using the same name since the library is backed by a dictionary.
        '''
        self._log.info('loading macros from path: {}'.format(self._macro_path))
        for _file in Path(self._macro_path).glob('*.py'):
#           self._log.heading('Load Macro', 'Loading file: {}'.format(_file))
            self._log.info(Fore.WHITE + Style.BRIGHT + '{}'.format(Util.repeat('━', 72)))
            self._log.info('loading macro file: ' + Fore.YELLOW + '{} '.format(_file)
                    + Fore.WHITE + Style.BRIGHT + '{}'.format(Util.repeat('┈', 50 - len(str(_file)))))
            try:
                _split = os.path.split(_file)
                _name = os.path.splitext(_split[1])[0]
                exec(open(_file).read())
                self._log.info('loaded macro: ' + Fore.YELLOW + '{} '.format(_name)
                        + Fore.WHITE + Style.BRIGHT + '{}\n'.format(Util.repeat('┈', 56 - len(_name))))
            except Exception as e:
                self._log.error('{} importing macro: {}'.format(type(e), _file))
        self._log.info('loading complete: {} macros in library'.format(self._library.size))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        if not self.enabled:
            if self._message_bus.get_task_by_name(MacroPublisher._LISTENER_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                self._log.info('enabling...')
                Publisher.enable(self)
                if self._load_macros:
                    self.load_macro_files()
                self._log.info('creating task for macro processor loop... (enabled? {})'.format(self.enabled))
                self._message_bus.loop.create_task(self._macro_listener_loop(lambda: self.enabled), name=MacroPublisher._LISTENER_LOOP_NAME)
                self._log.info('enabled: macro loop task created.')
        else:
            self._log.warning('already enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_executing_macro(self):
        '''
        Return the currently-executing Macro or None if unavailable.
        '''
        return self._macro

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def on_completion(self, args):
        self._log.info('🍉 on completion: {}'.format(args))
        _exec_macro = self.get_executing_macro()
        if _exec_macro:
            self._log.info('🍉 😷 has executing macro!')
            if _exec_macro.payload:
                _payload = _exec_macro.payload
                if isinstance(_payload, Message):
                    _message = _payload
                    _actual_payload = _message.payload
                    self._log.info('🍉 publishing Message {} with Event {} from payload:\n'.format(_message.name, _message.event.name) + Fore.YELLOW + '{}'.format(_actual_payload))
                    # TODO publish this message now!
                    self._queue_publisher.put(_message)

                elif isinstance(_payload, Payload):
                    self._log.info('🍉 has Payload:\n' + Fore.YELLOW + '{}'.format(_payload))
                    # TODO
                else:
                    self._log.info('🍉 has unknown payload:\n' + Fore.YELLOW + '{}'.format(_payload))
                    # TODO
            else:
                self._log.info('🍉 💩 has NO payload!')
        else:
            self._log.info('🍉 💩 has NO executing macro!')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _macro_listener_loop(self, f_is_enabled):
        '''
        We poll the queue for statement, and then wait until the requisite
        amount of time has passed, then either publish the Statement's Event
        or process its lambda.
        '''
        self._log.info('🐰 starting macro listener loop.')
        while f_is_enabled():
            # check if there's either a running macro or one available
            if self._macro or not self._macros.empty(): # either we have a macro or there is one available
                _count = next(self._counter)
                if not self._macro: # if we don't have a current macro, pop one from the stack
                    self._macro = self._macros.get()
                    if self._macro:
                        _payload = self._macro.payload
                        self._log.info('🐰 macro {} payload: '.format(self._macro.name) + Fore.YELLOW + '{}'.format(_payload))
                # otherwise continue to execute the existing macro...
                if not self._statement: # if no existing statement, poll one from the macro.
                    if not self._macro.empty():
                        self._statement = self._macro.poll()
                        self._log.info('🐰 event: ' + Fore.YELLOW + '{}:\t'.format(self._statement.label)
                                + Fore.MAGENTA + 'duration: {:5.2f}ms'.format(self._statement.duration_ms))
                        self._start_time = dt.now()
                # if there is an active statement waiting...
                if self._statement:
                    # then process this statement...
                    _elapsed_ms = (dt.now() - self._start_time).total_seconds() * 1000.0
                    if _elapsed_ms < self._statement.duration_ms and _elapsed_ms < self._wait_limit_ms:
                        # if the elapsed time is less than the required delay keep waiting...
                        _elapsed_ms = (dt.now() - self._start_time).total_seconds() * 1000.0
                        self._log.info(Fore.CYAN + Style.DIM + '🐰 e. still waiting on event: ' + Fore.YELLOW + '{}:\t'.format(self._statement.label)
                                + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
                    else:
                        # then execute the statement...
                        if self._statement.is_lambda:
                            _func = self._statement.function
                            self._log.info(Fore.GREEN + '🐰 executing lambda: ' + Fore.YELLOW + '{}: (type: {})\t'.format(self._statement.label, type(_func))
                                    + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
                            _func()
                        else:
                            _event = self._statement.event
                            self._log.info(Fore.GREEN + '🐰 publishing event:  ' + Fore.YELLOW + '{}:\t'.format(self._statement.label)
                                    + Fore.MAGENTA + '{:5.2f}ms elapsed.'.format(_elapsed_ms))
                            _message = self.message_factory.create_message(_event, self._statement.duration_ms)
                            if _message is not None:
                                self._log.info(Style.BRIGHT + '🐰 macro-publishing message:' + Fore.WHITE + Style.NORMAL + ' {}'.format(_message.name)
                                        + Fore.CYAN + ' event: {}; '.format(_message.event.label) + Fore.YELLOW + 'timestamp: {}'.format(_message.value))
                                await Publisher.publish(self, _message)
                                self._log.info(Style.BRIGHT + '🐰 macro-published message:' + Fore.WHITE + Style.NORMAL + ' {}'.format(_message.name)
                                        + Fore.CYAN + ' event: {}; '.format(_message.event.label) + Fore.YELLOW + 'timestamp: {}'.format(_message.value))
                        # end loop
                        self._statement = None

                else: # no statement so we do nothing...
                    self._log.info(Style.DIM + '🐰 no active statement.')
                    pass

                if not self._statement and self._macro.empty():
                    # we're finished with that macro, so execute any callbacks...
                    for _callback in self.__callbacks:
                        self._log.info('🐰 executing callback...')
                        _callback()
                    self.__callbacks.clear()
                    self._macro = None

                # loop sleep ............................
                await asyncio.sleep(self._loop_delay_sec)
            else:
                # we just wait quietly for a macro to show up.
                await asyncio.sleep(self._quiescent_delay_sec)

        # end of while loop ........................
        self._log.info('🐰 macro publish loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher as well as shut down the message bus.
        '''
        Publisher.disable(self)
        self._log.info('disabled macro processor.')

#EOF