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
    '''
    Extends Subscriber as a manager of high-level ballistic behaviours.

    :param name:         the subscriber name (for logging)
    :param message_bus:  the message bus
    :param color:        the color for messages
    :param level:        the logging level 
    '''
    def __init__(self, config, message_bus, motors, color=Fore.MAGENTA, level=Level.INFO):
        super().__init__('bhv-mgr', message_bus, color, level)
        if config is None:
            raise ValueError('null configuration argument.')
        self._config = config
        self._motors = motors
        self._active_behaviour = None
        self.events      = []
        self._behaviours = {}
        self.add_event(Event.INFRARED_CNTR)
        self._log.info('behaviour manager ready.')

    # ..........................................................................
    def register_behaviour(self, behaviour):
        '''
        Register a Behaviour with the manager, referenced by its Event type.
        '''
        self._behaviours[behaviour.event] = behaviour
        self.events.append(behaviour.event)
        self._log.info('added behaviour {} linked to event {} to manager.'.format(behaviour.name, behaviour.event))

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
        if not self._enabled:
            for _key, _behaviour in self._behaviours.items():
                _behaviour.enable()
            super().enable()

    # ..........................................................................
    def disable(self):
        if self._enabled:
            for _key, _behaviour in self._behaviours.items():
                _behaviour.disable()
            super().disable()

    # ..........................................................................
    def close(self):
        '''
        Permanently close and disable the message bus.
        '''
        if not self._closed:
            for _key, _behaviour in self._behaviours.items():
                _behaviour.close()
            super().close()

    # ..........................................................................
    async def process_message(self, message):
        '''
        Process the message.

        :param message:  the message to process.
        '''
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
        _event = message.event
        self._log.info('🥝 pre-processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.description) + Style.RESET_ALL)

        # get behaviour for event type
        _behaviour = self.get_behavior_for_event(_event)
        if _behaviour is None:
            self._log.info('🥝 0. no behaviour associated with event {}.'.format(_event.description))
            # FIXME TODO how to associate INFRARED_CNTR to ROAM?
        elif _behaviour.enabled:
            self._log.info('🥝 1. disabling behaviour {}...'.format(_behaviour.name))
            _behaviour.disable()
            if self._active_behaviour is _behaviour:
                # then clear the active behavior
                self._active_behaviour = None
        elif self._active_behaviour is None: # no current active behaviour so just enable this one
            self._log.info('🥝 2. enabling behaviour {}...'.format(_behaviour.name))
            self._active_behaviour = _behaviour
            _behaviour.enable()
        elif self._active_behaviour is _behaviour: # if the current active behaviour is already this one, we ignore the message
            self._log.info('🥝 3. behaviour {} already running.'.format(_behaviour.name))
        else:
            self._log.info('🥝 4. there is a behaviour {} already running.'.format(self._active_behaviour.name))
            _compare = _event.compare_to_priority_of(self._active_behaviour.event)
            if _compare == 1:
                self._log.info('🥝 5. new behaviour {} is HIGHER priority than existing behaviour {}.'.format(_event.name, self._active_behaviour.name))
                # the current active behaviour is a lower priority so we disable the existing and enable the new one
                self._log.info('🥝 5a. disabling old behaviour {}...'.format(self._active_behaviour.name))
                self._active_behaviour.disable()
                self._log.info('🥝 5b. setting new behaviour as active {}...'.format(_behaviour.name))
                self._active_behaviour = _behaviour
                self._log.info('🥝 5c. enabling new behaviour {}...'.format(self._active_behaviour.name))
                self._active_behaviour.enable()
                self._log.info('🥝 5d. done.')
            elif _compare == -1:
                self._log.info('🥝 6. new behaviour {} is LOWER priority than existing behaviour {}.'.format(_event.name, self._active_behaviour.name))
                # the current active behaviour is a higher priority so we ignore the request to alter it
            else: # _compare == 0: 
                self._log.info('🥝 7. new behaviour {} has SAME priority as existing behaviour {}.'.format(_event.name, self._active_behaviour.name))
                # same priority, no change

#           self._active_behaviour = None

#       if _event is Event.ROAM:
#           self._log.info(Fore.YELLOW + 'ROAM: message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.description) + Style.RESET_ALL)
#           if self._roam.enabled:
#               self._roam.disable()
#           else:
#               self._roam.enable()
#           self._behaviour_handler.dispatch_roam_event(_event)
#       elif _event is Event.SNIFF:
#           self._log.info(Fore.YELLOW + 'SNIFF: message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.description) + Style.RESET_ALL)
#           if self._sniff.enabled:
#               self._sniff.disable()
#           else:
#               self._sniff.enable()
#       else:
#           self._log.warning('unrecognised message {} ({})'.format(message.name, message.event.description))

        await super().process_message(message)
        self._log.debug('post-processing message {}'.format(message.name))

#EOF
