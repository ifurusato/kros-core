#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-16
# modified: 2021-04-22
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

# ..............................................................................
class BehaviourManager(Subscriber):
    CLASS_NAME='beh-mgr'
    '''
    Extends Subscriber as a manager of high-level, low-priority behaviours.
    This subscribes to all events grouped as a Event.BEHAVIOUR.

    :param name:         the subscriber name (for logging)
    :param message_bus:  the message bus
    :param color:        the color for messages
    :param level:        the logging level 
    '''
    def __init__(self, message_bus, level=Level.INFO):
        Subscriber.__init__(self, BehaviourManager.CLASS_NAME, message_bus=message_bus, color=Fore.RED, suppressed=False, enabled=True, level=Level.INFO)
        self._active_behaviour = None
        self._behaviours       = {}

    # ..........................................................................
    def _register_behaviour(self, behaviour, callback):
        '''
        Register a Behaviour with the manager, referenced by its Event type.

        This is performed by the Behaviour's constructor and should not be
        called directly.
        '''
        # TODO attach callback to Ticker

        self._behaviours[behaviour.event] = behaviour
        self.add_event(behaviour.event)
        self._log.info('🈸 added behaviour \'{}\' linked to event \'{}\' to manager.'.format(behaviour.name, behaviour.event))

    # ..........................................................................
    def get_behavior_for_event(self, event):
        '''
        Return the behaviour corresponding to the event type, null if
        no such behaviour has been registered with the manager.
        '''
        return self._behaviours.get(event)

    # ..........................................................................
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        for _key, _behaviour in self._behaviours.items():
            _behaviour.start()
            self._log.debug('started behaviour {}'.format(_behaviour.name))
        super().start()

    # ..........................................................................
    def enable(self):
        self._log.debug('🍉 enable behaviours...')
        if not self.enabled:
            super().enable()
            for _key, _behaviour in self._behaviours.items():
                _behaviour.enable()

    # ..........................................................................
    def disable(self):
        self._log.debug('🍉 disable behaviours...')
        if self.enabled:
            for _key, _behaviour in self._behaviours.items():
                _behaviour.disable()
            super().disable()

    # ..........................................................................
    def close(self):
        '''
        Permanently close and disable the message bus.
        '''
        if self.enabled:
            self.disable()
        if not self.closed:
            for _key, _behaviour in self._behaviours.items():
                _behaviour.close()
            super().close()

    # ..........................................................................
    async def process_message(self, message):
        '''
        Process the message.

        :param message:  the message to process.
        '''
        _event = message.event
        self._log.info('🥝 PRE-pre-processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.description) + Style.RESET_ALL)
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
        self._log.info('🥝 pre-processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.description) + Style.RESET_ALL)
        # get behaviour for event type
        _behaviour = self.get_behavior_for_event(_event)
        if _behaviour is None:
            self._log.info('🥝 0. no behaviour associated with event {}.'.format(_event.description))
            # FIXME TODO how to associate INFRARED_CNTR to ROAM?
        elif not _behaviour.suppressed:
            self._log.info('🥝 1. suppressing behaviour {}...'.format(_behaviour.name))
            _behaviour.suppress()
            if self._active_behaviour is _behaviour:
                # then clear the active behavior
                self._active_behaviour = None
        elif self._active_behaviour is None: # no current active behaviour so just release this one
            self._log.info('🥝 2. releasing behaviour {}...'.format(_behaviour.name))
            self._active_behaviour = _behaviour
            _behaviour.release()
        elif self._active_behaviour is _behaviour: # if the current active behaviour is already this one, we ignore the message
            self._log.info('🥝 3. behaviour {} already released.'.format(_behaviour.name))
        else:
            self._log.info('🥝 4. there is a behaviour {} already running.'.format(self._active_behaviour.name))
            _compare = _event.compare_to_priority_of(self._active_behaviour.event)
            if _compare == 1:
                self._log.info('🥝 5. new behaviour {} is HIGHER priority than existing behaviour {}.'.format(_event.name, self._active_behaviour.name))
                # the current active behaviour is a lower priority so we suppress the existing and release the new one
                self._log.info('🥝 5a. suppressing old behaviour {}...'.format(self._active_behaviour.name))
                self._active_behaviour.suppress()
                self._log.info('🥝 5b. setting new behaviour as active {}...'.format(_behaviour.name))
                self._active_behaviour = _behaviour
                self._log.info('🥝 5c. releasing new behaviour {}...'.format(self._active_behaviour.name))
                self._active_behaviour.release()
                self._log.info('🥝 5d. done.')
            elif _compare == -1:
                self._log.info('🥝 6. new behaviour {} is LOWER priority than existing behaviour {}.'.format(_event.name, self._active_behaviour.name))
                # the current active behaviour is a higher priority so we ignore the request to alter it
            else: # _compare == 0: 
                # same priority, no change
                self._log.info('🥝 7. new behaviour {} has SAME priority as existing behaviour {}.'.format(_event.name, self._active_behaviour.name))

        await super().process_message(message)
        self._log.info('post-processing message {}'.format(message.name))

#EOF
