#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-16
# modified: 2021-07-12
#

import asyncio
import random
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.orient import Orientation
from core.event import Event, Group
from core.subscriber import Subscriber

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class BehaviourManager(Subscriber):

    CLASS_NAME='beh-mgr'

    '''
    Extends Subscriber as a manager of high-level, low-priority behaviours.
    This subscribes to all events grouped as an Event.BEHAVIOUR.

    :param name:         the subscriber name (for logging)
    :param config:       the application configuration
    :param message_bus:  the message bus
    :param level:        the logging level
    '''
    def __init__(self, config, message_bus, level=Level.INFO):
        Subscriber.__init__(self, BehaviourManager.CLASS_NAME, config, message_bus=message_bus, suppressed=False, enabled=True, level=Level.INFO)
        self._active_behaviour = None
        self._behaviours       = {}

#       methods = [func for func in dir(BehaviourManager) if callable(getattr(BehaviourManager, func)) and not func.startswith("__")]
#       methods = [func for func in dir(BehaviourManager) if callable(getattr(BehaviourManager, func))]
#       for method in methods:
#           print(method)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        for _key, _behaviour in self._behaviours.items():
            _behaviour.start()
            self._log.debug('started behaviour {}'.format(_behaviour.name))
        Subscriber.start(self)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable_all_behaviours(self):
        '''
        Enable all registered behaviours.
        '''
        if not self.closed:
            self._log.info('enable all behaviours...')
            for _key, _behaviour in self._behaviours.items():
                _behaviour.enable()
                self._log.info('{} behaviour enabled.'.format(_behaviour.name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable_all_behaviours(self):
        '''
        Disable all registered behaviours.
        '''
        self._log.info('disable all behaviours...')
        for _key, _behaviour in self._behaviours.items():
            _behaviour.disable()
            self._log.info('{} behaviour disabled.'.format(_behaviour.name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def suppress_all_behaviours(self):
        '''
        Suppress all registered behaviours.
        '''
        self._log.info('suppress all behaviours...')
        for _key, _behaviour in self._behaviours.items():
            _behaviour.suppress()
            self._log.info('{} behaviour suppressed.'.format(_behaviour.name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def release_all_behaviours(self):
        '''
        Release (un-suppress) all registered behaviours.
        '''
        if not self.closed:
            self._log.info('release all behaviours...')
            for _key, _behaviour in self._behaviours.items():
                _behaviour.release()
                self._log.info('{} behaviour released.'.format(_behaviour.name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close_all_behaviours(self):
        '''
        Permanently close all registered behaviours. They cannot be reopened
        or otherwise enabled after this.
        '''
        for _key, _behaviour in self._behaviours.items():
            _behaviour.close()
            self._log.info('{} behaviour closed.'.format(_behaviour.name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _register_behaviour(self, behaviour):
        '''
        Register a Behaviour with the manager, referenced by its trigger
        Event type.

        This is called by the Behaviour's constructor and should not be
        called directly.
        '''
        self._behaviours[behaviour.trigger_event] = behaviour
        self.add_event(behaviour.trigger_event)
        self._log.info('added behaviour \'{}\' linked to trigger event \'{}\' to manager.'.format(behaviour.name, behaviour.trigger_event))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_behavior_for_trigger_event(self, event):
        '''
        Return the behaviour corresponding to the (trigger) event type, null
        if no such behaviour has been registered with the manager.
        '''
        return self._behaviours.get(event)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def process_message(self, message):
        '''
        Process the message.

        :param message:  the message to process.
        '''
        _event = message.event
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
        self._log.info(Fore.MAGENTA + 'pre-processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.label))
        self._alter_behaviour(_event)

        self._log.debug('awaiting subscriber process_message {}.'.format(_event.name))
        await Subscriber.process_message(self, message)
        self._log.debug('complete: awaited subscriber process_message {}.'.format(_event.name))
        self._log.debug('post-processing message {}'.format(message.name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _alter_behaviour(self, event):
        '''
        Alters the Behaviour associated with the event.
        '''
        if not isinstance(event, Event):
            raise ValueError('expected event argument, not {}'.format(type(event)))
        # get behaviour for event type
        _behaviour = self._get_behavior_for_trigger_event(event)
        if _behaviour is None:
            self._log.warning('cannot act: no behaviour associated with event {}, from {:d} registered behaviours ({}).'.format(
                    event.label, len(self._behaviours), self._behaviours))
            return

        _trigger_behaviour = _behaviour.get_trigger_behaviour(event)
        self._log.info('designated trigger behaviour: ' + Fore.YELLOW + '{}'.format(_trigger_behaviour.name))

        if self._active_behaviour is None: # no current active behaviour so just release this one
            self._log.info('no current behaviour; releasing behaviour ' + Fore.YELLOW + '{}'.format(_behaviour.name))
            self._active_behaviour = _behaviour
            _behaviour.on_trigger(event)

        elif self._active_behaviour is _behaviour:
            # if the current active behaviour is already this one, we ignore the message
            self._log.info('the requested behaviour ' + Fore.YELLOW + '{}'.format(_behaviour.name) + Fore.CYAN + ' is already executing.')
            _behaviour.on_trigger(event)

        else:
            self._log.info('there is a behaviour ' + Fore.YELLOW + '{}'.format(self._active_behaviour.name)
                    + Fore.CYAN + ' already running; comparing...')
            _compare = event.compare_to_priority_of(self._active_behaviour.trigger_event)
            if _compare == 1:
                self._log.info('requested behaviour ' + Fore.YELLOW + '{}'.format(event.label) + Fore.CYAN
                        + ' is HIGHER priority than existing behaviour ' + Fore.YELLOW + '{}'.format(self._active_behaviour.name))
                # the current active behaviour is a lower priority so we suppress the existing and release the new one
                self._log.info('suppressing old behaviour ' + Fore.YELLOW + '{}'.format(self._active_behaviour.name))
                self._active_behaviour.suppress()
                self._log.info('setting new behaviour ' + Fore.YELLOW + '{}'.format(_behaviour.name) + Fore.CYAN + ' as active...')
                self._active_behaviour = _behaviour
                self._log.info('releasing new behaviour ' + Fore.YELLOW + '{}'.format(self._active_behaviour.name))
                self._active_behaviour.release()
                self._log.info('done.')
            elif _compare == -1:
                # the current active behaviour is a higher priority so we ignore the request to alter it
                self._log.info('requested behaviour ' + Fore.YELLOW + '{}'.format(event.label) + Fore.CYAN
                        + ' is LOWER priority than existing behaviour ' + Fore.YELLOW + '{}'.format(self._active_behaviour.name)
                        + Fore.CYAN + ' (no change)')
            else: # _compare == 0:
                # same priority, no change
                self._log.info('requested behaviour ' + Fore.YELLOW + '{}'.format(event.label) + Fore.CYAN
                        + ' has the SAME priority as existing behaviour ' + Fore.YELLOW + '{}'.format(self._active_behaviour.name)
                        + Fore.CYAN + ' (no change)')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable the behaviour manager and all behaviours.
        '''
        self._log.debug('disable behaviour manager and all behaviours...')
        self.suppress_all_behaviours()
        self.disable_all_behaviours()
        Subscriber.disable(self)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        '''
        Permanently close and disable the behaviour manager and all behaviours.
        '''
        if not self.closed:
            Subscriber.close(self) # will call disable
            self.close_all_behaviours()

#EOF
