#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-07-21
#
# _Getch at bottom.
#

import sys, time, itertools, random, traceback
import select, tty, termios # used by _Getch
import select
import asyncio
import concurrent.futures
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.message_factory import MessageFactory
from core.logger import Logger, Level
from core.event import Event
from core.component import Component

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MockPotentiometer(Component):

    _LISTENER_LOOP_NAME = '__pot_listener_loop'

    '''
    A mocked digital potentiometer.

    :param level:             the log level
    '''
    def __init__(self, config, callback=None, level=Level.INFO):
        self._log = Logger('mock-pot', level)
        Component.__init__(self, self._log, False, True)
        self._level           = level
        self._callback        = callback
        self._out_min         = 0
        self._out_max         = 0
        self._counter         = itertools.count()
        self._getch           = _Getch()
        self._value           = 0
        self._loop            = asyncio.get_event_loop()
        # configuration ....................................
        _cfg = config['kros'].get('mock').get('potentiometer')
        self._loop_delay_sec  = _cfg.get('loop_delay_sec')
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_output_limits(out_min, out_max):
        if not isinstance(out_min, float):
            raise ValueError('wrong type for out_min argument: {}'.format(type(out_min)))
        self._out_min = out_min
        if not isinstance(out_max, float):
            raise ValueError('wrong type for out_max argument: {}'.format(type(out_max)))
        self._out_max = out_max
        self._log.info('output range:\t{:>5.2f}-{:<5.2f}'.format(self._out_min, self._out_max))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        if not self.closed:
            Component.enable(self)
            # this call will block
            self._get_event_loop()
            self._log.info('exited forever loop.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_event_loop(self):
        '''
        Return the asyncio event loop, starting it if it is not already running.

        Calling this method will start the potentiometer, blocking until disabled.
        '''
        if not self._loop:
            self._log.info('creating asyncio task loop...')
            self._loop = asyncio.get_event_loop()
            if self._log.level is Level.DEBUG:
                self._loop.set_debug(True) # also set asyncio debug
            # may want to catch other signals too
            signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
            for s in signals:
                self._loop.add_signal_handler(
                    s, lambda s = s: asyncio.create_task(self.shutdown(s), name='shutdown'),)
            self._loop.set_exception_handler(self.handle_exception)
#           self._loop.create_task(self._start_consuming(), name='__event_loop__')
            self._loop.create_task(self._key_listener_loop(lambda: self.enabled), name=MockPotentiometer._LISTENER_LOOP_NAME)
        if not self._loop.is_running():
            self._log.debug('starting asyncio task loop...')
            self._loop.run_forever()
        return self._loop

    # shutdown ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def shutdown(self, signal=None):
        '''
        Cleanup tasks tied to the service's shutdown.
        '''
        if signal:
            self._log.info('received exit signal {}...'.format(signal))
        self._log.info(Fore.RED + 'nacking outstanding tasks...')
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        self._log.info(Fore.RED + 'cancelling {:d} outstanding tasks...'.format(len(tasks)))
        _result = await asyncio.gather(*tasks, return_exceptions=True)
        self._log.info(Fore.RED + 'stopping loop...; result: {}'.format(_result))
        self._loop.stop()
        self._log.info(Fore.RED + 'shutting down...')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def value(self):
        return self._value

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_scaled_value(self, update_led=True):
        return self._value

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _key_listener_loop(self, f_is_enabled):
        self._log.info('starting key listener loop:\t' + Fore.YELLOW + 'type \'?\' for help, \'q\' or Ctrl-C to exit.')
        try:
            while f_is_enabled():
                _count = next(self._counter)
                self._log.debug('[{:03d}] BEGIN loop...'.format(_count))
                _event = None
                if self._getch.available():
                    ch = self._getch.readchar()
                    if ch != None and ch != '':
                        och = ord(ch)
                        self._log.debug('key "{}" ({}) pressed, processing...'.format(ch, och))
                        _event = None
                        if och == 104 or och == 47 or och == 63: # 'h' or '/' or '?' for help
                            self.print_help()
                            continue
                        elif och == 44 : # '<'
                            _event = Event.DECREASE_VELOCITY
                            decrementValue()
                        elif och == 46 : # '>'
                            _event = Event.INCREASE_VELOCITY
                            incrementValue()
                        elif och == 3 or och == 113: # 'q'
                            self.disable()
                            self._log.info('exiting on \'q\' or Ctrl-C...')
                        # otherwise handle as event
                        if _event is not None:
                            self._log.info('key \'{}\' ({}) pressed; publishing message for event: {}'.format(ch, och, _event))
                            if self._callback:
                                self._callback(_event)
                        else:
                            self._log.warning('unmapped key \'{}\' ({}) pressed.'.format(ch, och))
                        await asyncio.sleep(self._publish_delay_sec)
                    else:
                        self._log.warning('readchar returned null.')
                else:
                    # nothing happening...
                    self._log.debug('[{:03d}] waiting for key press...'.format(_count))
                    await asyncio.sleep(self._loop_delay_sec)

                self._log.debug('[{:03d}] END loop.'.format(_count))
            self._log.info('publish loop complete.')
        finally:
            if self._getch:
                self._getch.close()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def incrementValue():
        if self._value < self._out_max:
            self._value += 1

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def decrementValue():
        if self._value > self._out_min:
            self._value -= 1

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_help(self):
        self._log.info('''key map:

        Arrow UP:   increase target velocity
        Arrow DOWN: decrease target velocity

        ''')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable the mock potentiometer as well as shut down the message bus.
        '''
        if self._loop and self._loop.is_running():
            self._loop.stop()
        Component.disable(self)
        self._log.info('disabled mock potentiometer.')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class _Getch():
    '''
    Provides non-blocking key input from stdin.
    '''
    def __init__(self):
        self._old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

    def available(self):
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

    def readchar(self):
        return sys.stdin.read(1)

    def close(self):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)

#EOF
