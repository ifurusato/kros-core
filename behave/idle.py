#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-06-26
#

from abc import ABC, abstractmethod
import itertools
import asyncio
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.util import Util
from core.event import Event, Group
from core.fsm import State
from behave.behaviour import Behaviour
from core.publisher import Publisher
from behave.trigger_behaviour import TriggerBehaviour

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Idle(Behaviour, Publisher):

    _LISTENER_LOOP_NAME = '__idle_listener_loop'

    '''
    Extends both Behaviour and Publisher to implement a idle
    behaviour. This polls the MessageBus value for last message
    timestamp, and after a certain amount of time has passed
    with no sensor events it then triggers publication of an
    IDLE event message.

    :param name:            the name of this behaviour
    :param config:          the application configuration
    :param message_bus:     the asynchronous message bus
    :param message_factory: the factory for messages
    :param level:           the optional log level
    '''
    def __init__(self, config, message_bus, message_factory, level=Level.INFO):
        Behaviour.__init__(self, 'idle', config, message_bus, message_factory, level)
        Publisher.__init__(self, 'idle', config, message_bus, message_factory, suppressed=True, level=level)
        _cfg = self._config['kros'].get('behaviour').get('idle')
        self._idle_threshold_sec = _cfg.get('idle_threshold_sec') # int value
        self._log.info('idle threshold: {:d} sec.'.format(self._idle_threshold_sec))
        _loop_freq_hz            = _cfg.get('loop_freq_hz')
        self._log.info('idle loop frequency: {:d}Hz.'.format(_loop_freq_hz))
        self._idle_loop_delay_sec = 1.0 / _loop_freq_hz
        self._idle_loop_running = False
        self._counter = itertools.count()
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def release(self):
        Component.release(self)
        self._log.debug('released.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def suppress(self):
        Component.suppress(self)
        self._log.debug('suppressed.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_trigger_behaviour(self, event):
        return TriggerBehaviour.TOGGLE

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def trigger_event(self):
        '''
        This returns the event used to enable/disable the behaviour manually.

        The priority of this event determines the priority of this Behaviour
        when compared to other Behaviours.
        '''
        return Event.IDLE

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        if self.state is not State.STARTED:
            Publisher.start(self)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if self._message_bus.get_task_by_name(Idle._LISTENER_LOOP_NAME) or self._idle_loop_running:
                raise Exception('already enabled.')
#               self._log.warning('already enabled.')
            else:
                self._log.info('creating task for idle listener loop...')
                self._idle_loop_running = True
                self._message_bus.loop.create_task(self._idle_listener_loop(lambda: self.enabled), name=Idle._LISTENER_LOOP_NAME)
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable idle publisher.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _idle_listener_loop(self, f_is_enabled):
        self._log.info('starting idle listener loop:\t' + Fore.YELLOW + 'idle threshold: {:d} sec'.format(self._idle_threshold_sec)
                + ( '; (suppressed, type \'u\' to release)' if self.suppressed else '.') )
        while f_is_enabled():
            _count = next(self._counter)
            self._log.debug('[{:03d}] begin idle loop...'.format(_count))
            if not self.suppressed:
                # check for last message's timestamp
                _timestamp = self._message_bus.last_message_timestamp
                if _timestamp is None:
                    self._log.info(Fore.CYAN + '[{:03d}] idle inactive; '.format(_count) + Style.DIM + ' no previous messages.')
                else:
                    _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
                    if ( _elapsed_ms / 1000.0 ) > self._idle_threshold_sec:
                        self._log.info('[{:03d}] idle threshold met; '.format(_count)
                                + Fore.YELLOW + '{}'.format(Util.get_formatted_time('elapsed time since last message:', _elapsed_ms)))

                        _message = self._message_factory.create_message(Event.ROAM, dt.now())
                        self._log.info('idle publishing message for event: {}; value: {}'.format(_message.event.label, _message.value))

                        self._log.debug('key-publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.label))
                        await Publisher.publish(self, _message)
                        self._log.debug('key-published message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.label))
                    else:
                        self._log.info('[{:03d}] idle active; '.format(_count)
                                + Style.DIM + '{}'.format(Util.get_formatted_time('elapsed time since last message:', _elapsed_ms)))
                        pass

            else:
                self._log.debug(Fore.BLACK + '[{:03d}] idle suppressed.'.format(_count))

            await asyncio.sleep(self._idle_loop_delay_sec)
            self._log.debug('[{:03d}] end idle loop.'.format(_count))

        self._log.info('idle loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def execute(self, message):
        '''
        The method called upon each loop iteration.

        :param message:  an optional Message passed along by the message bus
        '''
        self._log.info(Fore.YELLOW + 'idle execute()...')
        if self.suppressed:
            self._log.info(Style.DIM + 'idle execute() SUPPRESSED; message: {}'.format(message.event.label))
        else:
            self._log.info('idle execute() RELEASED; message: {}'.format(message.event.label))
            _payload = message.payload
            _event   = _payload.event
            if _event is Event.IDLE:
                self.distance = _payload.value
                if self.enabled:
                    self._log.info('idle enabled.')
                else:
                    self._log.info('idle disabled.')
            else:
                raise ValueError('expected IDLE event not: {}'.format(message.event.label))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher.
        '''
        Behaviour.disable(self)
        Publisher.disable(self)
        self._log.info('disabled idle publisher.')

#EOF
