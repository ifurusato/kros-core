#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-02-21
# modified: 2021-04-26
#

import time, itertools
import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.event import Event

# ..............................................................................
class Controller(Component):
    '''
    A default controller class that receives callbacks (to the 'callback'
    method) when Events appear on the MessageBus' Arbitratror.
    '''
    def __init__(self, level):
        self._log = Logger('controller', level)
        Component.__init__(self, self._log, True)
        self._previous_payload     = None
        self._event_counter        = itertools.count()
        self._event_count          = next(self._event_counter)
        self._state_change_counter = itertools.count()
        self._state_change_count   = next(self._state_change_counter)
        self._log.info('ready.')

    # ..........................................................................
    def set_log_level(self, level):
        self._log.level = level

    # ................................................................
    @property
    def name(self):
        return 'def-controller'

    # ..........................................................................
    def get_current_message(self):
        return self._current_message

    # ..........................................................................
    def _clear_current_message(self):
        self._log.debug('clear current message  {}.'.format(self._current_message))
        self._current_message = None

    # ..........................................................................
    def callback(self, payload):
        '''
        Responds to the Event contained within the Payload.
        '''
        self._log.debug('callback with payload {}'.format(payload.event.name))
        if not self.enabled:
            self._log.warning('action ignored: controller disabled.')
            return
        self._event_count = next(self._event_counter)
        if self._previous_payload == None:
            self._log.info(Fore.CYAN + 'no previous payload.')
        elif payload == self._previous_payload:
            self._log.info(Fore.CYAN + 'no state change on event: ' + Style.BRIGHT + ' {}'.format(self._previous_payload.event.description)
                    + Fore.BLACK + Style.NORMAL + ' [{:d}/{:d}]'.format(self._state_change_count, self._event_count))
            self._log.info(Fore.GREEN + '🥒 payload: {}; previous payload: {}'.format(payload.value, self._previous_payload.value))
        else:
            if payload.event == self._previous_payload.event:
                self._log.info(Fore.CYAN + 'value {} changed on event: '.format(payload.value) + Style.BRIGHT + ' {}'.format(self._previous_payload.event.description)
                        + Fore.BLACK + Style.NORMAL + ' [{:d}/{:d}]'.format(self._state_change_count, self._event_count))
            else:
                self._log.info(Fore.CYAN + 'event changed on event: ' + Style.BRIGHT + ' {}'.format(self._previous_payload.event.description)
                        + Fore.BLACK + Style.NORMAL + ' [{:d}/{:d}]'.format(self._state_change_count, self._event_count))
            return

        self._previous_payload = payload
        self._state_change_count = next(self._state_change_counter)

        _start_time = dt.datetime.now()
        _event = payload.event
        self._log.info(Fore.CYAN + 'act on event: ' + Style.BRIGHT + ' {}'.format(_event.description)
                + Fore.BLACK + Style.NORMAL + ' [{:d}/{:d}]'.format(self._state_change_count, self._event_count))

        # name                                          n   description             priority  ballistic?
        # system events ....................
        if _event is Event.NOOP:                    # ( 0, "no operation",             0,     False)
           self._log.info('event: noop.')
        elif _event is Event.BATTERY_LOW:           # ( 1, "battery low",              0,     True)
           self._log.warning('event: battery low.')
        elif _event is Event.SHUTDOWN:              # ( 2, "shutdown",                 1,     True)
           self._log.info('event: shutdown.')
        elif _event is Event.HIGH_TEMPERATURE:      # ( 3, "high temperature",         1,     False)
           self._log.warning('event: high temperature.')

        # stopping and halting .............
        elif _event is Event.STOP:                  # ( 4, "stop",                     2,     True)
           self._log.info('event: stop.')
        elif _event is Event.HALT:                  # ( 5, "halt",                     3,     False)
           self._log.info('event: halt.')
        elif _event is Event.BRAKE:                 # ( 6, "brake",                    4,     False)
           self._log.info('event: brake.')
        elif _event is Event.BUTTON:                # ( 7, "button",                   5,     False)
           self._log.info('event: button press.')
        elif _event is Event.STANDBY:               # ( 8, "standby",                  6,     False)
           self._log.info('event: standby.')
        
        # bumper ...........................
        elif _event is Event.COLLISION_DETECT:      # ( 10, "collision detect",         9,   False)
           self._log.warning('event: collision detect.')
        elif _event is Event.BUMPER_PORT:           # ( 11, "bumper port",             10,    True)
           self._log.info('event: bumper-port.')
        elif _event is Event.BUMPER_CNTR:           # ( 12, "bumper center",           10,    True)
           self._log.info('event: bumper-center.')
        elif _event is Event.BUMPER_STBD:           # ( 13, "bumper starboard",        10,    True)
           self._log.info('event: bumper-starboard.')

        # infrared .........................
        elif _event is Event.INFRARED_PORT_SIDE:    # ( 20, "infrared port side",      20,    True)
           self._log.info('event: infrared-port-side.')
        elif _event is Event.INFRARED_PORT:         # ( 21, "infrared port",           20,    True)
           self._log.info('event: infrared-port.')
        elif _event is Event.INFRARED_CNTR:         # ( 22, "infrared cntr",           20,    True)
           self._log.info('event: infrared-center.')
        elif _event is Event.INFRARED_STBD:         # ( 23, "infrared stbd",           20,    True)
           self._log.info('event: infrared-starboard.')
        elif _event is Event.INFRARED_STBD_SIDE:    # ( 24, "infrared stbd side",      20,    True)
           self._log.info('event: infrared-starboard-side.')
        
        # emergency movements ..............
        elif _event is Event.EMERGENCY_ASTERN:      # ( 30, "emergency astern",        15,    True)
           self._log.info('event: emergency-astern.')

        # movement ahead ...................
        elif _event is Event.FULL_AHEAD:            # ( 45, "full ahead",              100,   False)
           self._log.info('event: full-ahead.')
        elif _event is Event.HALF_AHEAD:            # ( 46, "half ahead",              100,   False)
           self._log.info('event: half-ahead.')
        elif _event is Event.SLOW_AHEAD:            # ( 47, "slow ahead",              100,   False)
           self._log.info('event: slow-ahead')
        elif _event is Event.DEAD_SLOW_AHEAD:       # ( 48, "dead slow ahead",         100,   False)
           self._log.info('event: dead-slow-ahead.')
        elif _event is Event.AHEAD:                 # ( 49, "ahead",                   100,   False)
           self._log.info('event: ahead.')

        # movement astern ..................
        elif _event is Event.ASTERN:                # ( 50, "astern",                  100,   False)
           self._log.info('event: astern.')
        elif _event is Event.DEAD_SLOW_ASTERN:      # ( 51, "dead slow astern",        100,   False)
           self._log.info('event: dead-slow-astern.')
        elif _event is Event.SLOW_ASTERN:           # ( 52, "slow astern",             100,   False)
           self._log.info('event: slow-astern.')
        elif _event is Event.HALF_ASTERN:           # ( 53, "half astern",             100,   False)
           self._log.info('event: half-astern.')
        elif _event is Event.FULL_ASTERN:           # ( 54, "full astern",             100,   False)
           self._log.info('event: full-astern.')

        # relative change ..................
        elif _event is Event.INCREASE_VELOCITY:     # ( 60, "increase speed",          100,   False)
           self._log.info('event: increase-speed.')
        elif _event is Event.EVEN:                  # ( 61, "even",                    100,   False)
           self._log.info('event: even.')
        elif _event is Event.DECREASE_VELOCITY:     # ( 62, "decrease speed",          100,   False)
           self._log.info('event: decrease-speed.')

        # port turns .......................
        elif _event is Event.TURN_AHEAD_PORT:       # ( 70, "turn ahead port",         100,   False)
           self._log.info('event: turn-ahead-port.')
        elif _event is Event.TURN_TO_PORT:          # ( 71, "turn to port",            100,   False)
           self._log.info('event: turn-to-port.')
        elif _event is Event.TURN_ASTERN_PORT:      # ( 72, "turn astern port",        100,   False)
           self._log.info('event: astern-port.')
        elif _event is Event.SPIN_PORT:             # ( 73, "spin port",               100,   False)
           self._log.info('event: spin-port.')

        # starboard turns ..................
        elif _event is Event.SPIN_STBD:             # ( 80, "spin starboard",          100,   False)
           self._log.info('event: spin-starboard.')
        elif _event is Event.TURN_ASTERN_STBD:      # ( 81, "turn astern starboard",   100,   False)
           self._log.info('event: turn-astern-starboard.')
        elif _event is Event.TURN_TO_STBD:          # ( 82, "turn to starboard",       100,   False)
           self._log.info('event: turn-to-starboard.')
        elif _event is Event.TURN_AHEAD_STBD:       # ( 83, "turn ahead starboard",    100,   False)
           self._log.info('event: turn-ahead-starboard.')

        # high level behaviours ............
        elif _event is Event.ROAM:                  # ( 500, "roam",                    150,    True)
           self._log.info('event: roam.')
        elif _event is Event.MOTH:                  # ( 501, "moth",                    151,    True)
           self._log.info('event: moth.')
        elif _event is Event.SNIFF:                 # ( 502, "sniff",                   152,    True)
           self._log.info('event: sniff.')
        elif _event is Event.VIDEO:                 # ( 503, "L1: video",               153,   False) # L1 Button
           self._log.info('event: video.')
        elif _event is Event.EVENT_L2:              # ( 504, "L2",                      154,   False) # L2 Button
           self._log.info('event: L2.')
        elif _event is Event.EVENT_R1:              # ( 505, "R1: cruise",              155,   False) # R1 Button
           self._log.info('event: R1.')
        elif _event is Event.LIGHTS:                # ( 506, "R2: lights",              156,   False) # R2 Button
           self._log.info('event: lights.')
        elif _event is Event.MOTION_DETECT:         # ( 507, "motion detect",           157,   False)
           self._log.info('event: motion-detect.')
        elif _event is Event.IDLE:                  # ( 508, "R2: lights",              159,    True)
           self._log.info('event: idle.')
        
        # movement directives ..............
        elif _event is Event.VELOCITY:              # ( 101, "forward velocity",       200,   False)
           self._log.info('event: velocity.')
        elif _event is Event.THETA:                 # ( 102, "theta",                  200,   False)
           self._log.info('event: theta.')
        elif _event is Event.PORT_VELOCITY:         # ( 103, "port velocity",          200,   False)
           self._log.info('event: port-velocity.')
        elif _event is Event.PORT_THETA:            # ( 104, "port theta",             200,   False)
           self._log.info('event: port-theta.')
        elif _event is Event.STBD_VELOCITY:         # ( 105, "starboard velocity",     200,   False)
           self._log.info('event: starboard-velocity.')
        elif _event is Event.STBD_THETA:            # ( 106, "starboard theta",        200,   False)
           self._log.info('event: starboard-theta.')
        
        # other behaviours (> 500) .........
        elif _event is Event.NO_ACTION:             # ( 500, "no action",              500,   False)
           self._log.info('event: no action.')
        elif _event is Event.CLOCK_TICK:            # ( 501, "tick",                   500,   False)
           self._log.info('event: tick.')
        elif _event is Event.CLOCK_TOCK:            # ( 502, "tock",                   500,   False)
           self._log.info('event: tock.')

        # unrecognised event  ..................................................
        else:
            self._log.error('unrecognised event: {}'.format(_event))

        _delta = dt.datetime.now() - _start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        self._log.debug(Fore.MAGENTA + Style.DIM + 'elapsed: {}ms'.format(_elapsed_ms) + Style.DIM)

    # ..........................................................................
    def print_statistics(self):
        self._log.info('{}:'.format(self.name) + Fore.YELLOW + '\t{} events; {} state changes.'.format(self._event_count, self._state_change_count))

# EOF
