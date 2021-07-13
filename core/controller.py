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
    def __init__(self, message_bus, level):
        self._log = Logger('controller', level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        self._message_bus          = message_bus
        self._previous_payload     = None
        self._event_counter        = itertools.count()
        self._event_count          = next(self._event_counter)
        self._state_change_counter = itertools.count()
        self._state_change_count   = next(self._state_change_counter)
        self._message_bus.register_controller(self)
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
        self._log.info('callback with payload {}'.format(payload.event.label))
        if not self.enabled:
            self._log.warning('action ignored: controller disabled.')
            return
        self._event_count = next(self._event_counter)
        if self._previous_payload == None:
            self._log.debug(Fore.CYAN + 'no previous payload.')
        elif payload == self._previous_payload:
            self._log.info(Fore.CYAN + 'no state change on event: ' + Style.BRIGHT + ' {}'.format(self._previous_payload.event.label)
                    + Fore.BLACK + Style.NORMAL + ' [{:d}/{:d}]'.format(self._state_change_count, self._event_count))
            self._log.info(Fore.GREEN + 'payload: {}; previous payload: {}'.format(payload.value, self._previous_payload.value))
        else:
            if payload.event == self._previous_payload.event:
                self._log.info(Fore.CYAN + 'value {} changed on event: '.format(payload.value) + Style.BRIGHT + ' {}'.format(self._previous_payload.event.label)
                        + Fore.BLACK + Style.NORMAL + ' [{:d}/{:d}]'.format(self._state_change_count, self._event_count))
            else:
                self._log.info(Fore.CYAN + 'state change from event: ' + Style.BRIGHT + ' {}'.format(self._previous_payload.event.label)
                        + Style.NORMAL + ' to event: {} ' + Style.BRIGHT + ' {}'.format(payload.event.label)
                        + Fore.BLACK + Style.NORMAL + ' [{:d}/{:d}]'.format(self._state_change_count, self._event_count))
#           return

        self._previous_payload = payload
        self._state_change_count = next(self._state_change_counter)

        _start_time = dt.datetime.now()
        _event = payload.event
        self._log.info(Fore.CYAN + 'act on event: ' + Style.BRIGHT + ' {}'.format(_event.label)
                + Fore.BLACK + Style.NORMAL + ' [{:d}/{:d}]'.format(self._state_change_count, self._event_count))

        # system events ........................................................
        if _event is Event.NOOP:                           # 0, "no operation"
           self._log.info('event: "no operation"')
        elif _event is Event.BATTERY_LOW:                  # 10, "battery low"
           self._log.info('event: "battery low"')
        elif _event is Event.SHUTDOWN:                     # 11, "shutdown"
           self._log.info('event: "shutdown"')
        elif _event is Event.HIGH_TEMPERATURE:             # 12, "high temperature"
           self._log.info('event: "high temperature"')
        elif _event is Event.COLLISION_DETECT:             # 13, "collision detect"
           self._log.info('event: "collision detect"')
        elif _event is Event.EMERGENCY_ASTERN:             # 14, "emergency astern"
           self._log.info('event: "emergency astern"')

        # gamepad events .......................................................
        elif _event is Event.GAMEPAD:                      # 40, "gamepad"
           self._log.info('event: "gamepad"')

        # stopping and halting .................................................
        elif _event is Event.STOP:                         # 50, "stop"
           self._log.info('event: "stop"')
        elif _event is Event.HALT:                         # 51, "halt"
           self._log.info('event: "halt"')
        elif _event is Event.BRAKE:                        # 52, "brake"
           self._log.info('event: "brake"')
        elif _event is Event.STANDBY:                      # 53, "standby"
           self._log.info('event: "standby"')
        elif _event is Event.BUTTON:                       # 54, "button"
           self._log.info('event: "button"')

    # bumper ................................................................................
        elif _event is Event.BUMPER_PORT:                  # 110, "bumper port"
           self._log.info('event: "bumper port"')
        elif _event is Event.BUMPER_CNTR:                  # 111, "bumper center"
           self._log.info('event: "bumper center"')
        elif _event is Event.BUMPER_STBD:                  # 112, "bumper stbd"
           self._log.info('event: "bumper stbd"')

    # infrared ..............................................................................
        elif _event is Event.INFRARED_PORT_SIDE:           # 120, "infrared port side"
           self._log.info('event: "infrared port side"')
        elif _event is Event.INFRARED_PORT:                # 121, "infrared port"
           self._log.info('event: "infrared port"')
        elif _event is Event.INFRARED_CNTR:                # 122, "infrared cntr"
           self._log.info('event: "infrared cntr"')
        elif _event is Event.INFRARED_STBD:                # 123, "infrared stbd"
           self._log.info('event: "infrared stbd"')
        elif _event is Event.INFRARED_STBD_SIDE:           # 124, "infrared stbd side"
           self._log.info('event: "infrared stbd side"')

    # velocity directives ...................................................................
        elif _event is Event.VELOCITY:                     # 200, "velocity"
           self._log.info('event: "velocity"')
        elif _event is Event.PORT_VELOCITY:                # 201, "port velocity"
           self._log.info('event: "port velocity"')
        elif _event is Event.STBD_VELOCITY:                # 202, "stbd velocity"
           self._log.info('event: "stbd velocity"')
        elif _event is Event.INCREASE_PORT_VELOCITY:       # 203, "increase port velocity"
           self._log.info('event: "increase port velocity"')
        elif _event is Event.DECREASE_PORT_VELOCITY:       # 204, "decrease port velocity"
           self._log.info('event: "decrease port velocity"')
        elif _event is Event.INCREASE_STBD_VELOCITY:       # 205, "increase stbd velocity"
           self._log.info('event: "increase stbd velocity"')
        elif _event is Event.DECREASE_STBD_VELOCITY:       # 206, "decrease stbd velocity"
           self._log.info('event: "decrease stbd velocity"')
        elif _event is Event.INCREASE_VELOCITY:            # 207, "increase velocity"
           self._log.info('event: "increase velocity"')
        elif _event is Event.DECREASE_VELOCITY:            # 208, "decrease velocity"
           self._log.info('event: "decrease velocity"')

    # theta directives ......................................................................
        elif _event is Event.THETA:                        # 300, "theta"
           self._log.info('event: "theta"')
        elif _event is Event.PORT_THETA:                   # 301, "port theta"
           self._log.info('event: "port theta"')
        elif _event is Event.STBD_THETA:                   # 302, "stbd theta"
           self._log.info('event: "stbd theta"')
        elif _event is Event.EVEN:                         # 303, "even"
           self._log.info('event: "even"')
        elif _event is Event.INCREASE_PORT_THETA:          # 304, "increase port theta"
           self._log.info('event: "increase port theta"')
        elif _event is Event.DECREASE_PORT_THETA:          # 305, "decrease port theta"
           self._log.info('event: "decrease port theta"')
        elif _event is Event.INCREASE_STBD_THETA:          # 306, "increase stbd theta"
           self._log.info('event: "increase stbd theta"')
        elif _event is Event.DECREASE_STBD_THETA:          # 307, "decrease stbd theta"
           self._log.info('event: "decrease stbd theta"')
    # port turns ...........
        elif _event is Event.TURN_AHEAD_PORT:              # 310, "turn ahead port"
           self._log.info('event: "turn ahead port"')
        elif _event is Event.TURN_TO_PORT:                 # 311, "turn to port"
           self._log.info('event: "turn to port"')
        elif _event is Event.TURN_ASTERN_PORT:             # 312, "turn astern port"
           self._log.info('event: "turn astern port"')
        elif _event is Event.SPIN_PORT:                    # 313, "spin port"
           self._log.info('event: "spin port"')
    # starboard turns ......
        elif _event is Event.SPIN_STBD:                    # 320, "spin stbd"
           self._log.info('event: "spin stbd"')
        elif _event is Event.TURN_ASTERN_STBD:             # 321, "turn astern stbd"
           self._log.info('event: "turn astern stbd"')
        elif _event is Event.TURN_TO_STBD:                 # 322, "turn to stbd"
           self._log.info('event: "turn to stbd"')
        elif _event is Event.TURN_AHEAD_STBD:              # 323, "turn ahead stbd"
           self._log.info('event: "turn ahead stbd"')

    # chadburn event ........................................................................
    # astern ...............
        elif _event is Event.FULL_ASTERN:                  # 400, "full astern"
           self._log.info('event: "full astern"')
        elif _event is Event.HALF_ASTERN:                  # 401, "half astern"
           self._log.info('event: "half astern"')
        elif _event is Event.SLOW_ASTERN:                  # 402, "slow astern"
           self._log.info('event: "slow astern"')
        elif _event is Event.DEAD_SLOW_ASTERN:             # 403, "dead slow astern"
           self._log.info('event: "dead slow astern"')
        elif _event is Event.ASTERN:                       # 404, "astern"
           self._log.info('event: "astern"')
    # ahead ................
        elif _event is Event.AHEAD:                        # 410, "ahead"
           self._log.info('event: "ahead"')
        elif _event is Event.DEAD_SLOW_AHEAD:              # 411, "dead slow ahead"
           self._log.info('event: "dead slow ahead"')
        elif _event is Event.SLOW_AHEAD:                   # 412, "slow ahead"
           self._log.info('event: "slow ahead"')
        elif _event is Event.HALF_AHEAD:                   # 413, "half ahead"
           self._log.info('event: "half ahead"')
        elif _event is Event.FULL_AHEAD:                   # 414, "full ahead"
           self._log.info('event: "full ahead"')

    # high level behaviours .................................................................
        elif _event is Event.AVOID:                        # 500, "roam"
           self._log.info('event: "avoid"')
        elif _event is Event.ROAM:                         # 501, "roam"
           self._log.info('event: "roam"')
        elif _event is Event.MOTH:                         # 502, "moth"
           self._log.info('event: "moth"')
        elif _event is Event.SNIFF:                        # 503, "sniff"
           self._log.info('event: "sniff"')
        elif _event is Event.VIDEO:                        # 504, "video"
           self._log.info('event: "video"')
        elif _event is Event.EVENT_L2:                     # 505, "L2"
           self._log.info('event: "L2"')
        elif _event is Event.EVENT_R1:                     # 506, "cruise"
           self._log.info('event: "cruise"')
        elif _event is Event.LIGHTS:                       # 507, "lights"
           self._log.info('event: "lights"')
        elif _event is Event.MOTION_DETECT:                # 508, "motion detect"
           self._log.info('event: "motion detect"')
        elif _event is Event.IDLE:                         # 509, "idle"
           self._log.info('event: "idle"')

    # other events (> 900) ..................................................................
        elif _event is Event.NO_ACTION:                    # 999, "no action"
           self._log.info('event: "no action"')
        elif _event is Event.ANY:                          # 1000, "any"
           self._log.info('event: "any"')

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
