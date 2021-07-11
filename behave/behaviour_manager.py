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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class BehaviourManager(Subscriber):

    CLASS_NAME='beh-mgr'

    '''
    Extends Subscriber as a manager of high-level, low-priority behaviours.
    This subscribes to all events grouped as an Event.BEHAVIOUR.

    :param name:         the subscriber name (for logging)
    :param config:       the application configuration
    :param message_bus:  the message bus
    :param color:        the color for messages
    :param level:        the logging level 
    '''
    def __init__(self, config, message_bus, level=Level.INFO):
        Subscriber.__init__(self, BehaviourManager.CLASS_NAME,
                config, message_bus=message_bus, color=Fore.CYAN + Style.DIM, suppressed=False, enabled=True, level=Level.INFO)
        self._active_behaviour = None
        self._behaviours       = {}

    # ..........................................................................
    def _register_behaviour(self, behaviour):
        '''
        Register a Behaviour with the manager, referenced by its trigger
        Event type.

        This is called by the Behaviour's constructor and should not be
        called directly.
        '''
        self._behaviours[behaviour.trigger_event] = behaviour
        self.add_event(behaviour.trigger_event)
        self._log.info('🥝 added behaviour \'{}\' linked to trigger event \'{}\' to manager.'.format(behaviour.name, behaviour.trigger_event))

    # ..........................................................................
    def get_behavior_for_trigger_event(self, event):
        '''
        Return the behaviour corresponding to the (trigger) event type, null
        if no such behaviour has been registered with the manager.
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
        Subscriber.start(self)

    # ..........................................................................
    def enable(self):
        self._log.debug('enable behaviours...')
        if not self.enabled:
            Subscriber.enable(self)
            for _key, _behaviour in self._behaviours.items():
                _behaviour.enable()

    # ..........................................................................
    def disable(self):
        self._log.debug('disable behaviours...')
        if self.enabled:
            for _key, _behaviour in self._behaviours.items():
                _behaviour.disable()
            Subscriber.disable(self)

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
            Subscriber.close(self)

    # ..........................................................................
    async def process_message(self, message):
        '''
        Process the message.

        :param message:  the message to process.
        '''
        _event = message.event
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
        self._log.debug('pre-processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.description) + Style.RESET_ALL)
#       breakpoint()
        self._alter_behaviour(_event)

        self._log.debug('awaiting subscriber process_message {}.'.format(_event.name))
        await Subscriber.process_message(self, message)
        self._log.debug('complete: awaited subscriber process_message {}.'.format(_event.name))
        self._log.debug('post-processing message {}'.format(message.name))

    # ..........................................................................
    def _alter_behaviour(self, event):
        '''
        Alters the Behaviour associated with the event.
        '''
        # get behaviour for event type
        _behaviour = self.get_behavior_for_trigger_event(event)
        if _behaviour is None:
            self._log.warning('🍀 cannot act: no behaviour associated with event {}.'.format(event.description))
            return

#       # otherwise alter behaviour
#       if not _behaviour.suppressed:
#           self._log.info('🍀 suppressing behaviour {}...'.format(_behaviour.name))
#           _behaviour.suppress()
#           if self._active_behaviour is _behaviour:
#               # then clear the active behavior
#               self._active_behaviour = None

        if self._active_behaviour is None: # no current active behaviour so just release this one
            self._log.info('🍀 no current behaviour; releasing behaviour {}...'.format(_behaviour.name))
            self._active_behaviour = _behaviour
            _behaviour.release()

        elif self._active_behaviour is _behaviour: # if the current active behaviour is already this one, we ignore the message
            self._log.info('🍀 this particular behaviour {} is already executing.'.format(_behaviour.name))

        else:
            self._log.info('🍀 there is a behaviour {} already running; comparing...'.format(self._active_behaviour.name))
            _compare = event.compare_to_priority_of(self._active_behaviour.event)
            if _compare == 1:
                self._log.info('🍀 new behaviour {} is HIGHER priority than existing behaviour {}.'.format(event.name, self._active_behaviour.name))
                # the current active behaviour is a lower priority so we suppress the existing and release the new one
                self._log.info('🍀 suppressing old behaviour {}...'.format(self._active_behaviour.name))
                self._active_behaviour.suppress()
                self._log.info('🍀 setting new behaviour as active {}...'.format(_behaviour.name))
                self._active_behaviour = _behaviour
                self._log.info('🍀 releasing new behaviour {}...'.format(self._active_behaviour.name))
                self._active_behaviour.release()
                self._log.info('🍀 done.')
            elif _compare == -1:
                self._log.info('🍀 new behaviour {} is LOWER priority than existing behaviour {}.'.format(event.name, self._active_behaviour.name))
                # the current active behaviour is a higher priority so we ignore the request to alter it
            else: # _compare == 0: 
                # same priority, no change
                self._log.info('🍀 new behaviour {} has SAME priority as existing behaviour {}.'.format(event.name, self._active_behaviour.name))

#EOF
