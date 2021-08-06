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
from core.publisher import Publisher

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MockPotPublisher(Publisher):

    _LISTENER_LOOP_NAME = '__pot_listener_loop'

    '''
    A mocked digital potentiometer.

    :param config:            the application configuration
    :param message_bus:       the asynchronous message bus
    :param message_factory:   the factory for creating messages
    :param level:             the log level
    '''
    def __init__(self, config, message_bus, message_factory, level=Level.INFO):
        Publisher.__init__(self, 'pot', config, message_bus, message_factory, level=level)
        self._level           = level
        self._counter         = itertools.count()
        self._getch           = _Getch()
        # configuration ....................................
        _cfg = config['kros'].get('mock').get('event_publisher')
        self._publish_delay_sec = _cfg.get('publish_delay_sec') # delay after IFS event
        self._loop_delay_sec  = _cfg.get('noop_loop_delay_sec') # delay on noop loop
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if self._message_bus.get_task_by_name(MockPotPublisher._LISTENER_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                self._log.info('creating task for key listener loop...')
                self._message_bus.loop.create_task(self._key_listener_loop(lambda: self.enabled), name=MockPotPublisher._LISTENER_LOOP_NAME)
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable publisher.')

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
                        elif och == 46 : # '>'
                            _event = Event.INCREASE_VELOCITY
                        elif och == 3 or och == 113: # 'q'
                            self.disable()
                            self._log.info('exiting on \'q\' or Ctrl-C...')
                        # otherwise handle as event
                        if _event is not None:
                            self._log.info('key \'{}\' ({}) pressed; publishing message for event: {}'.format(ch, och, _event))
                            _message = self._message_factory.create_message(_event, True)
                            _message.value = dt.now() # we use a timestamp to guarantee each message is different
                            self._log.debug('key-publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.label))
                            await Publisher.publish(self, _message)
                            self._log.debug('key-published message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.label))

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
    def print_help(self):
        self._log.info('''key map:

        Arrow UP:   increase target velocity
        Arrow DOWN: decrease target velocity

        ''')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher as well as shut down the message bus.
        '''
        self._message_bus.disable()
        Publisher.disable(self)
        self._log.info('disabled publisher.')

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
