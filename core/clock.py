#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-06-30
#
# A system clock that ticks and tocks.
#

import sys, time, itertools
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.message import Message
from core.logger import Logger, Level
from core.event import Event
from core.rate import Rate

from core.publisher import Publisher

# ...............................................................
class Clock(Publisher):

    _PUBLISH_LOOP_NAME = '__clock_loop__'

    '''
    A system clock that creates a "TICK" message every loop, 
    alternating with a "TOCK" message every modulo-nth loop.
    Note that the TOCK message replaces the TICK, i.e., every 
    nth loop there is no TICK, only a TOCK.
    '''
    def __init__(self, config, message_bus, message_factory, level):
        Publisher.__init__(self, 'clock', message_bus, message_factory, level)
        self._log = Logger("clock", level)
        if message_bus is None:
            raise ValueError('null message bus argument.')
        self._message_bus = message_bus
        if message_factory is None:
            raise ValueError('null message factory argument.')
        self._message_factory = message_factory
        if config is None:
            raise ValueError('null configuration argument.')
        _config            = config['kros'].get('clock')
        self._loop_freq_hz = _config.get('loop_freq_hz')
        self._tock_modulo  = _config.get('tock_modulo')
        self._log.info('tock modulo: {:d}'.format(self._tock_modulo))
        self._counter      = itertools.count()
        self._rate         = Rate(self._loop_freq_hz)
        self._log.info('tick frequency: {:d}Hz'.format(self._loop_freq_hz))
        self._log.info('tock frequency: {:d}Hz'.format(round(self._loop_freq_hz / self._tock_modulo)))
        self._log.info('ready.')

    # ..........................................................................
    @property
    def freq_hz(self):
        '''
        Returns the loop frequency in hertz.
        The value is returned from the configured value.
        '''
        return self._loop_freq_hz

    # ..........................................................................
    @property
    def dt_ms(self):
        '''
        Returns the time loop delay in milliseconds.
        The value is returned from Rate.
        '''
        return self._rate.dt_ms

    # ..........................................................................
    async def _clock_loop(self, f_is_enabled):
        '''
        The clock loop, which executes while the f_is_enabled flag is True. 
        '''
        while f_is_enabled():
            _now = dt.now()
            _count = next(self._counter)
            if (( _count % self._tock_modulo ) == 0 ):
                _message = self._message_factory.get_message(Event.CLOCK_TOCK, _count)
            else:
                _message = self._message_factory.get_message(Event.CLOCK_TICK, _count)
            self._log.debug('publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
            await super().publish(_message)
            # TODO may need an asyncio-based Rate here
            self._rate.wait()
#           await asyncio.sleep(self._publish_delay_sec)

        self._log.info('exited clock loop.')

    # ................................................................
    def enable(self):
        if not self.enabled:
            super().enable()
            if self._message_bus.get_task_by_name(Clock._PUBLISH_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                self._log.info('creating task for clock loop...')
                self._message_bus.loop.create_task(self._clock_loop(lambda: self.enabled), name=Clock._PUBLISH_LOOP_NAME)
                self._log.info('enabled.')
        else:
            self._log.warning('clock already enabled.')

#EOF
