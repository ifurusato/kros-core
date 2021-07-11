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
from core.util import Util
from core.event import Event, Group
from core.fsm import State
from core.publisher import Publisher

# ...............................................................
class Idle(Publisher):

    _LISTENER_LOOP_NAME = '__idle_listener_loop'

    '''
    Extends Publisher to implement a idle behaviour. This polls
    the MessageBus' value for last message timestamp, and after
    a certain amount of time has passed with no sensor events it
    then triggers publication of an IDLE event message.

    :param name:            the name of this behaviour
    :param config:          the application configuration
    :param message_bus:     the asynchronous message bus
    :param message_factory: the factory for messages
    :param level:           the optional log level
    '''
    def __init__(self, config, message_bus, message_factory, level=Level.INFO):
        Publisher.__init__(self, 'idle', config, message_bus, message_factory, level)
        _cfg = self._config['kros'].get('behaviour').get('idle')
        self._idle_threshold_sec = _cfg.get('idle_threshold_sec') # int value
        self._log.info('idle threshold: {:d} sec.'.format(self._idle_threshold_sec))
        self._idle_loop_delay_sec = _cfg.get('idle_loop_delay_sec')
        self._log.info('idle loop delay: {:4.2f} sec.'.format(self._idle_threshold_sec)) # float value
        self._idle_loop_running = False
        self._counter = itertools.count()
#       self.add_events([ Group.INFRARED, Group.BUMPER ])
        self._log.info('ready.')

    # ..........................................................................
#   @property
#   def trigger_event(self):
#       '''
#       This returns the event used to enable/disable the behaviour manually.
#       '''
#       return Event.IDLE

    # ..........................................................................
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        if self.state is not State.STARTED:
            Publisher.start(self)

    # ................................................................
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

    # ................................................................
    async def _idle_listener_loop(self, f_is_enabled):
        self._log.info('starting idle listener loop: ' + Fore.YELLOW + 'type \'?\' for help, \'q\' or Ctrl-C to exit.')
        while f_is_enabled():
            _count = next(self._counter)
            self._log.info('[{:03d}] BEGIN idle loop...'.format(_count))
            if not self.suppressed:
                # check for last message's timestamp
                _timestamp = self._message_bus.last_message_timestamp
                if _timestamp is None:
                    self._log.info(Fore.BLACK + '[{:03d}] idle loop execute; no previous messages.'.format(_count))
                else:
                    _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
                    if ( _elapsed_ms / 1000.0 ) > self._idle_threshold_sec:
                        self._log.info('[{:03d}] idle loop execute; {}'.format(_count, Util.get_formatted_time('message age:', _elapsed_ms)) 
                                + Fore.YELLOW + ' type: {}'.format(type(_elapsed_ms)))
    
                        _message = self._message_factory.get_message(Event.ROAM, True)
                        _message.value = dt.now()
                        self._log.info('publishing message for event: {}; value: {}'.format(_message.event.description, _message.value))

                        self._log.info('key-publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
                        await Publisher.publish(self, _message)
                        self._log.info('key-published message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
    
                    else:
                        self._log.info('idle loop execute; {}'.format(Util.get_formatted_time('message age:', _elapsed_ms)) 
                                + Fore.BLUE + ' type: {}'.format(type(_elapsed_ms)))
            else:
                self._log.info('[{:03d}] idle suppressed.'.format(_count))

            await asyncio.sleep(self._idle_loop_delay_sec)
            self._log.info('[{:03d}] END idle loop.'.format(_count))

        self._log.info('idle loop complete.')

#   # ..........................................................................
#   def callback(self):
#       '''
#       This is the loop that's going to be called at 1Hz. Create a modulo
#       variable such that even nth call we'd check for the last message,
#       and if none have occurred recently we'd trigger an IDLE message, or
#       we'd call ROAM or something. The current trigger_even of IDLE is 
#       probably wrong. This should be running all the time unless suppressed,
#       as it is an idle behaviour.
#       '''
#       self._log.info('❄️  idle callback.')
#       _timestamp = self._message_bus.last_message_timestamp
#       if _timestamp is None:
#           self._log.info('❄️  idle loop execute; no previous messages.')
#       else:
#           _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
#           if ( _elapsed_ms / 1000.0 ) > self._idle_threshold_sec:
#               self._log.info('❄️  idle loop execute; {}'.format(Util.get_formatted_time('message age:', _elapsed_ms)) 
#                       + Fore.GREEN + ' type: {}'.format(type(_elapsed_ms)))
#           else:
#               self._log.info('❄️  idle loop execute; {}'.format(Util.get_formatted_time('message age:', _elapsed_ms)) 
#                       + Fore.YELLOW + ' type: {}'.format(type(_elapsed_ms)))

#   # ..........................................................................
#   def execute(self, message):
#       '''
#       The method called upon each loop iteration.
#
#       :param message:  an optional Message passed along by the message bus
#       '''
#       if self.suppressed:
#           self._log.info(Style.DIM + '🌜 idle execute() SUPPRESSED; message: {}'.format(message.event.description))
#       else:
#           self._log.info('🌜 idle execute() RELEASED; message: {}'.format(message.event.description))
#           _timestamp = self._message_bus.last_message_timestamp
#           if _timestamp is None:
#               self._log.info('🌜 idle loop execute; no previous messages.')
#           else:
#               _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
#               if ( _elapsed_ms / 1000.0 ) > self._idle_threshold_sec:
#                   self._log.info('🌜 idle loop execute; {}'.format(Util.get_formatted_time('message age:', _elapsed_ms)) 
#                           + Fore.GREEN + ' type: {}'.format(type(_elapsed_ms)))
#               else:
#                   self._log.info('🌜 idle loop execute; {}'.format(Util.get_formatted_time('message age:', _elapsed_ms)) 
#                           + Fore.YELLOW + ' type: {}'.format(type(_elapsed_ms)))

    # ..........................................................................
    def disable(self):
        '''
        Disable this publisher.
        '''
        Publisher.disable(self)
        self._log.info('disabled idle publisher.')

#EOF
