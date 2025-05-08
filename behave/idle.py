#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2025-05-08
#

from abc import ABC, abstractmethod
import itertools
import asyncio
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

import core.globals as globals
globals.init()

from core.logger import Logger, Level
from core.component import Component
from core.subscriber import Subscriber
from core.util import Util
from core.event import Event, Group
from core.fsm import State
from behave.behaviour import Behaviour
from core.publisher import Publisher
from behave.trigger_behaviour import TriggerBehaviour

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Idle(Behaviour, Publisher):

    CLASS_NAME = 'idle'
    _LISTENER_LOOP_NAME = '__idle_listener_loop'

    '''
    Extends both Behaviour and Publisher to implement a idle behaviour.
    This polls the MessageBus value for last message timestamp, and
    after a certain amount of time has passed with no sensor events it
    then triggers publication of an Event.IDLE message with a value of
    False (inactive).

    As a Behaviour, this is also a Subscriber to the MessageBus so that
    it can capture messages in order to subsequently publish an
    Event.IDLE message with a value of True (active).

    :param name:            the name of this behaviour
    :param config:          the application configuration
    :param message_bus:     the asynchronous message bus
    :param message_factory: the factory for messages
    :param level:           the optional log level
    '''
    def __init__(self, config, message_bus=None, message_factory=None, level=Level.INFO):
        self._is_idle             = False
        Behaviour.__init__(self, Idle.CLASS_NAME, config, message_bus, message_factory, suppressed=False, enabled=True, level=level)
        Publisher.__init__(self, Idle.CLASS_NAME, config, message_bus, message_factory, suppressed=False, level=level)
        # subscribe to all non-IDLE events
        self.add_events([member for member in Group if member not in (Group.NONE, Group.IDLE, Group.OTHER)])
        _cfg = self._config['kros'].get('behaviour').get('idle')
        self._idle_threshold_sec  = _cfg.get('idle_threshold_sec') # int value
        self._log.info('idle threshold: {:d} sec.'.format(self._idle_threshold_sec))
        _loop_freq_hz             = _cfg.get('loop_freq_hz')
        self._log.info('idle loop frequency: {:d}Hz.'.format(_loop_freq_hz))
        self._idle_loop_delay_sec = 1.0 / _loop_freq_hz
        self._counter = itertools.count()
        self._idle_loop_running   = False
        self._value               = None
        self._elapsed_sec         = 0.0
        # get queue publisher for initial message
        _component_registry = globals.get('component-registry')
        self._queue_publisher = _component_registry.get('pub:queue')
        if self._queue_publisher is None:
            raise Exception('no queue publisher available.')
        self._eyeballs = _component_registry.get('eyeballs')
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return Idle.CLASS_NAME

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def is_idle(self):
        return self._is_idle

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def elapsed_seconds(self):
        '''
        Return the number of elapsed seconds since the last message was
        received by the message bus.
        '''
        return self._elapsed_sec

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
        return TriggerBehaviour.IGNORE

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def trigger_event(self):
        '''
        This returns the event used to enable/disable the behaviour manually.

        Note: the priority of this event determines the priority of this
        Behaviour when compared to other Behaviours.
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
        if not self.enabled:
            Publisher.enable(self)
            if self._message_bus.get_task_by_name(Idle._LISTENER_LOOP_NAME) or self._idle_loop_running:
                self._log.warning('message bus already had idle task.')
            else:
                self._log.info('creating task for idle listener loop…')
                self._idle_loop_running = True
                self._message_bus.loop.create_task(self._idle_listener_loop(lambda: self.enabled), name=Idle._LISTENER_LOOP_NAME)
                self._log.info('enabled.')
        else:
            self._log.warning('already enabled idle publisher.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _idle_listener_loop(self, f_is_enabled):
        self._log.info('starting idle listener loop:\t' + Fore.YELLOW + 'idle threshold: {:d} sec'.format(self._idle_threshold_sec)
                + ( '; (suppressed, type \'u\' to release)' if self.suppressed else '.') )
#       self.suppress()
        self._hello()
        while f_is_enabled():
            _count = next(self._counter)
            self._log.debug('[{:005d}] begin idle loop…; suppressed? {}'.format(_count, self.suppressed))
            if not self.suppressed:
                # check for last message's timestamp
                _timestamp = self._message_bus.last_message_timestamp
                if _timestamp is None:
                    self._log.info('[{:005d}] idle inactive; '.format(_count) + Style.DIM + ' no previous messages.')
                else:
                    '''
                    If we've passed the idle threshold then send an IDLE message, which will toggle the
                    suppressed/released state of the Idle handler.
                    '''
                    _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
                    self._elapsed_sec = _elapsed_ms / 1000.0
#                   self._log.info(Style.DIM + 'elapsed: {:4.02f}s'.format(self._elapsed_sec))
                    if self._elapsed_sec > self._idle_threshold_sec:
                        if self._is_idle:
#                           self._log.info(Style.DIM + '[{:005d}] already idle.'.format(_count))
                            pass
                        else:
                            # change state only if not already idle
                            self._is_idle = True
                            self._log.info('[{:005d}] idle threshold met; '.format(_count)
                                    + Fore.YELLOW + '{}'.format(Util.get_formatted_time('elapsed time since last message:', _elapsed_ms)))

                            _message = self._message_factory.create_message(Event.IDLE, False)
                            self._log.info('idle publishing message for event: {}; value: {}'.format(_message.event.name, _message.value))

                            self._log.debug('key-publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.name))
                            await Publisher.publish(self, _message)
                            self._log.debug('key-published message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.name))
                            if self._eyeballs:
                                self._eyeballs.sleepy()
#                           Player.play(Sound.SIGH)

                    elif self._is_idle:
                        if _count % 10 == 0:
                            self._log.info(Style.DIM + '[{:005d}] idle; '.format(_count)
                                    + Style.DIM + '{}'.format(Util.get_formatted_time('elapsed time since last message:', _elapsed_ms)))
                    else:
                        if _count % 5 == 0:
                            self._log.info(Fore.BLUE + '[{:005d}] waiting; '.format(_count)
                                    + Style.DIM + '{}'.format(Util.get_formatted_time('elapsed time since last message:', _elapsed_ms)))
            else:
                self._log.info(Fore.BLACK + '[{:005d}] idle suppressed.'.format(_count))

            await asyncio.sleep(self._idle_loop_delay_sec)
            self._log.debug('[{:005d}] end idle loop.'.format(_count))

        self._log.info('idle loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _hello(self):
        '''
        Publishes an initial IDLE message so that it can be used to calculate
        the elapsed time, otherwise the idle process cannot begin.
        '''
        self._log.info('publishing initial idle message…')
        _message = self._message_factory.create_message(Event.IDLE, False)
        self._queue_publisher.put(_message)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def process_message(self, message):
        '''
        Process the message. If it's not an IDLE message this indicates activity.

        A Subscriber method.

        :param message:  the message to process.
        '''
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected.')
        _event = message.event
        if _event.group == Group.IDLE:
            self._log.warning('unexpected IDLE message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.name))
            # we shouldn't see this but do nothing
        else:
            if self._is_idle:
                # indicates a state-change activity, so publish an IDLE message
                self._is_idle = False
                self._log.debug('group: {}: message {}; '.format(_event.group.name, message.name) + Fore.YELLOW + ' event: {}'.format(_event.name))
                self._log.info(Fore.YELLOW + '🔶 activity after {:4.2f} seconds of being idle.'.format(self.elapsed_seconds))
                _message = self._message_factory.create_message(Event.IDLE, True)
                self._queue_publisher.put(_message)
                if self._eyeballs:
                    self._eyeballs.happy()
#               Player.play(Sound.GLITCH)

        await Subscriber.process_message(self, message)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def execute(self, message):
        '''
        The method called upon each loop iteration when in EXECUTE mode.

        :param message:  an optional Message passed along by the message bus
        '''
        self._log.info(Fore.YELLOW + 'idle execute…')
        if self.suppressed:
            self._log.info(Style.DIM + 'idle execute() SUPPRESSED; message: {}'.format(message.event.name))
        else:
            self._log.info('idle execute() RELEASED; message: {}'.format(message.event.name))
            _payload = message.payload
            _event   = _payload.event
            if _event.group is Group.IDLE:
                self._value = _payload.value
                if self.enabled:
#                   self._log.info('idle enabled.')
                    self._log.info('🦋 idle enabled; value: {}.'.format(self._value))
                else:
#                   self._log.info('idle disabled.')
                    self._log.info('🧈 idle disabled; value: {}.'.format(self._value))
            else:
                raise ValueError('expected IDLE event not: {}'.format(message.event.name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher.
        '''
        if self._eyeballs:
            self._eyeballs.clear()
        Behaviour.disable(self)
        Publisher.disable(self)
        self._log.info('disabled idle publisher.')

#EOF
