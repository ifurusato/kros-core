#!/usr/bin/env python3 # -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-02-21
# modified: 2020-03-26
#

from enum import Enum

# ..............................................................................
class Group(Enum):
    NONE      = 0
    SYSTEM    = 1
    GAMEPAD   = 2
    STOP      = 3
    BUMPER    = 4
    INFRARED  = 5
#   SENSOR    = 6
    VELOCITY  = 7
    THETA     = 8
    CHADBURN  = 9
    BEHAVIOUR = 10
    CLOCK     = 11
    OTHER     = 12

# ..............................................................................
class Event(Enum):
    '''
    Ballistic behaviours cannot be interrupted, and are not therefore
    implemented as a separate thread.

    The specific response for a behaviour is provided by the Controller,
    which receives an Event-laden Message from the Arbitrator, which
    prioritises the Messages it receives from the MessageQueue. Note
    that priority operates in reverse-order: the smaller the number the
    higher the priority.

    For non-ballistic behaviours the response is generally an ongoing
    setting a pair of motor speeds.

    For ballistic behaviours the Controller's script for a given
    behaviour is meant to be uninterruptable. The goal here is to
    permit interruptions from *higher* priority events.
    '''
    # name                     n   description            priority   group         ballistic?
    # system events .........................................................................
    NOOP                   = ( 0, "no operation",            1000,   Group.SYSTEM,     False)
    BATTERY_LOW            = ( 10, "battery low",               1,   Group.SYSTEM,      True)
    SHUTDOWN               = ( 11, "shutdown",                  1,   Group.SYSTEM,      True)
    HIGH_TEMPERATURE       = ( 12, "high temperature",          1,   Group.SYSTEM,     False)
    COLLISION_DETECT       = ( 13, "collision detect",          2,   Group.SYSTEM,     False)
    EMERGENCY_ASTERN       = ( 14, "emergency astern",          2,   Group.SYSTEM,      True)

    # gamepad events ........................................................................
    GAMEPAD                = ( 40, "gamepad",                  10,   Group.GAMEPAD,    False)

    # stopping and halting ..................................................................
    STOP                   = ( 50, "stop",                     12,   Group.STOP,       False)
    HALT                   = ( 51, "halt",                     13,   Group.STOP,       False)
    BRAKE                  = ( 52, "brake",                    14,   Group.STOP,       False)
    STANDBY                = ( 53, "standby",                  15,   Group.STOP,       False)
    BUTTON                 = ( 54, "button",                   16,   Group.STOP,       False)

    # bumper ................................................................................
    BUMPER_PORT            = ( 110, "bumper port",             40,   Group.BUMPER,     False)
    BUMPER_CNTR            = ( 111, "bumper center",           40,   Group.BUMPER,     False)
    BUMPER_STBD            = ( 112, "bumper stbd",             40,   Group.BUMPER,     False)

    # infrared ..............................................................................
    INFRARED_PORT_SIDE     = ( 120, "infrared port side",      50,   Group.INFRARED,   False)
    INFRARED_PORT          = ( 121, "infrared port",           50,   Group.INFRARED,   False)
    INFRARED_CNTR          = ( 122, "infrared cntr",           50,   Group.INFRARED,   False)
    INFRARED_STBD          = ( 123, "infrared stbd",           50,   Group.INFRARED,   False)
    INFRARED_STBD_SIDE     = ( 124, "infrared stbd side",      50,   Group.INFRARED,   False)

    # velocity directives ...................................................................
    VELOCITY               = ( 200, "velocity",               100,   Group.VELOCITY,   False) # with value
    PORT_VELOCITY          = ( 201, "port velocity",          100,   Group.VELOCITY,   False) # with value
    STBD_VELOCITY          = ( 202, "stbd velocity",          100,   Group.VELOCITY,   False) # with value
    INCREASE_PORT_VELOCITY = ( 203, "increase port velocity", 100,   Group.VELOCITY,   False)
    DECREASE_PORT_VELOCITY = ( 204, "decrease port velocity", 100,   Group.VELOCITY,   False)
    INCREASE_STBD_VELOCITY = ( 205, "increase stbd velocity", 100,   Group.VELOCITY,   False)
    DECREASE_STBD_VELOCITY = ( 206, "decrease stbd velocity", 100,   Group.VELOCITY,   False)
    INCREASE_VELOCITY      = ( 207, "increase velocity",      100,   Group.VELOCITY,   False)
    DECREASE_VELOCITY      = ( 208, "decrease velocity",      100,   Group.VELOCITY,   False)

    # theta directives ......................................................................
    THETA                  = ( 300, "theta",                  100,   Group.THETA,      False) # with value
    PORT_THETA             = ( 301, "port theta",             100,   Group.THETA,      False)
    STBD_THETA             = ( 302, "stbd theta",             100,   Group.THETA,      False)
    EVEN                   = ( 303, "even",                   100,   Group.THETA,      False)
    INCREASE_PORT_THETA    = ( 304, "increase port theta",    100,   Group.THETA,      False)
    DECREASE_PORT_THETA    = ( 305, "decrease port theta",    100,   Group.THETA,      False)
    INCREASE_STBD_THETA    = ( 306, "increase stbd theta",    100,   Group.THETA,      False)
    DECREASE_STBD_THETA    = ( 307, "decrease stbd theta",    100,   Group.THETA,      False)
    # port turns ...........
    TURN_AHEAD_PORT        = ( 310, "turn ahead port",        100,   Group.THETA,      False)
    TURN_TO_PORT           = ( 311, "turn to port",           100,   Group.THETA,      False)
    TURN_ASTERN_PORT       = ( 312, "turn astern port",       100,   Group.THETA,      False)
    SPIN_PORT              = ( 313, "spin port",              100,   Group.THETA,      False)
    # starboard turns ......
    SPIN_STBD              = ( 320, "spin stbd",              100,   Group.THETA,      False)
    TURN_ASTERN_STBD       = ( 321, "turn astern stbd",       100,   Group.THETA,      False)
    TURN_TO_STBD           = ( 322, "turn to stbd",           100,   Group.THETA,      False)
    TURN_AHEAD_STBD        = ( 323, "turn ahead stbd",        100,   Group.THETA,      False)

    # chadburn event ........................................................................
    # astern ...............
    FULL_ASTERN            = ( 400, "full astern",            100,   Group.CHADBURN,   False)
    HALF_ASTERN            = ( 401, "half astern",            100,   Group.CHADBURN,   False)
    SLOW_ASTERN            = ( 402, "slow astern",            100,   Group.CHADBURN,   False)
    DEAD_SLOW_ASTERN       = ( 403, "dead slow astern",       100,   Group.CHADBURN,   False)
    ASTERN                 = ( 404, "astern",                 100,   Group.CHADBURN,   False) # with value
    # ahead ................
    AHEAD                  = ( 410, "ahead",                  100,   Group.CHADBURN,   False) # with value
    DEAD_SLOW_AHEAD        = ( 411, "dead slow ahead",        100,   Group.CHADBURN,   False)
    SLOW_AHEAD             = ( 412, "slow ahead",             100,   Group.CHADBURN,   False)
    HALF_AHEAD             = ( 413, "half ahead",             100,   Group.CHADBURN,   False)
    FULL_AHEAD             = ( 414, "full ahead",             100,   Group.CHADBURN,   False)

    # high level behaviours .................................................................
    ROAM                   = ( 500, "roam",                   150,   Group.BEHAVIOUR,   True)
    MOTH                   = ( 501, "moth",                   151,   Group.BEHAVIOUR,   True)
    SNIFF                  = ( 502, "sniff",                  152,   Group.BEHAVIOUR,   True) # A Button
    VIDEO                  = ( 503, "video",                  153,   Group.BEHAVIOUR,  False) # L1 Button
    EVENT_L2               = ( 504, "L2",                     154,   Group.BEHAVIOUR,  False) # L2 Button
    EVENT_R1               = ( 505, "cruise",                 155,   Group.BEHAVIOUR,  False) # R1 Button
    LIGHTS                 = ( 506, "lights",                 156,   Group.BEHAVIOUR,  False) # R2 Button
    MOTION_DETECT          = ( 507, "motion detect",          157,   Group.BEHAVIOUR,  False)
    IDLE                   = ( 508, "idle",                   159,   Group.BEHAVIOUR,   True) # A Button

    CLOCK_TICK             = ( 601, "tick",                   400,   Group.CLOCK,      False)
    CLOCK_TOCK             = ( 602, "tock",                   400,   Group.CLOCK,      False)

    # other events (> 500) ..................................................................
    NO_ACTION              = ( 999, "no action",              999,   Group.OTHER,      False)


    @property
    def is_ignoreable(self):
        '''
        Returns true if the priority of this event is 500 or greater.
        By definition this includes NO_ACTION, CLOCK_TICK and CLOCK_TOCK.
        '''
        return self._priority >= 500

    # ..................................
    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, num, description, priority, group, is_ballistic):
        self._description  = description
        self._priority     = priority
        self._group        = group
        self._is_ballistic = is_ballistic

    # ................................................................
    @staticmethod
    def is_clock_event(event):
        return ( event.group is Group.CLOCK )

    # ................................................................
    @staticmethod
    def is_motor_event(event):
        '''
        A convenience method to determine if the event is directly
        related to motor control. This includes stopping, velocity,
        theta (turning), and Chadburn (engine order telegraph) events.
        '''
        return ( event.group is Group.STOP ) \
                or ( event.group is Group.VELOCITY ) \
                or ( event.group is Group.THETA ) \
                or ( event.group is Group.CHADBURN )

    # ..................................
    @staticmethod
    def is_bumper_event(event):
        return event.group is Group.BUMPER

    # ..................................
    @staticmethod
    def is_infrared_event(event):
        return event.group is Group.INFRARED

    # ................................................................
    @staticmethod
    def is_ifs_event(event):
        '''
        A convenience method that returns True for all bumper and
        infrared events.
        '''
        return Event.is_bumper_event(event) or Event.is_infrared_event(event)

    # ................................................................
    @property
    def description(self):
        return self._description

    @property
    def priority(self):
        return self._priority

    def compare_to_priority_of(self, event):
        '''
        Returns 1 if the Event of the argument is a higher priority
        (lower number) than this Event; a -1 if the Event of the
        argument is a lower priority (higher number) than this Event;
        and 0 if they have the same priority.
        '''
        if self._priority < event.priority:
            return 1
        elif self._priority > event.priority:
            return -1
        else:
            return 0

    @property
    def group(self):
        return self._group

    @staticmethod
    def by_group(gid):
        '''
        Return all Events belonging to the requested Group.
        '''
        _list = []
        for _event in Event:
            if _event.group is gid:
                _list.append(_event)
        return _list

    @staticmethod
    def by_groups(gids):
        '''
        Return the accumulated Events belonging to all the requested Groups.
        '''
        _list = []
        for _gid in gids:
            _events = Event.by_group(_gid)
            _list.append(_events)
        return _list

    @property
    def is_ballistic(self):
        return self._is_ballistic

    # the normal value returned for an enum
    def __str__(self):
        return self.name

    @staticmethod
    def from_str(label):
        # system events ....................
        if label.upper() == 'NOOP':
            return Event.NOOP
        # emergency events .................
        elif label.upper() == 'BATTERY_LOW':
            return Event.BATTERY_LOW
        elif label.upper() == 'SHUTDOWN':
            return Event.SHUTDOWN
        elif label.upper() == 'HIGH_TEMPERATURE':
            return Event.HIGH_TEMPERATURE
        elif label.upper() == 'COLLISION_DETECT':
            return Event.COLLISION_DETECT
        elif label.upper() == 'EMERGENCY_ASTERN':
            return Event.EMERGENCY_ASTERN
        # gamepad events ...................
        elif label.upper() == 'GAMEPAD':
            return Event.GAMEPAD
        # stopping and halting .............
        elif label.upper() == 'STOP':
            return Event.STOP
        elif label.upper() == 'HALT':
            return Event.HALT
        elif label.upper() == 'BRAKE':
            return Event.BRAKE
        elif label.upper() == 'BUTTON':
            return Event.BUTTON
        elif label.upper() == 'STANDBY':
            return Event.STANDBY
        # bumper ...........................
        elif label.upper() == 'BUMPER_PORT':
            return Event.BUMPER_PORT
        elif label.upper() == 'BUMPER_CNTR':
            return Event.BUMPER_CNTR
        elif label.upper() == 'BUMPER_STBD':
            return Event.BUMPER_STBD
        # infrared .........................
        elif label.upper() == 'INFRARED_PORT_SIDE':
            return Event.INFRARED_PORT_SIDE
        elif label.upper() == 'INFRARED_PORT':
            return Event.INFRARED_PORT
        elif label.upper() == 'INFRARED_CNTR':
            return Event.INFRARED_CNTR
        elif label.upper() == 'INFRARED_STBD':
            return Event.INFRARED_STBD
        elif label.upper() == 'INFRARED_STBD_SIDE':
            return Event.INFRARED_STBD_SIDE
        # movement ahead ...................
        elif label.upper() == 'FULL_AHEAD':
            return Event.FULL_AHEAD
        elif label.upper() == 'HALF_AHEAD':
            return Event.HALF_AHEAD
        elif label.upper() == 'SLOW_AHEAD':
            return Event.SLOW_AHEAD
        elif label.upper() == 'DEAD_SLOW_AHEAD':
            return Event.DEAD_SLOW_AHEAD
        elif label.upper() == 'AHEAD':
            return Event.AHEAD
        # movement astern ..................
        elif label.upper() == 'ASTERN':
            return Event.ASTERN
        elif label.upper() == 'DEAD_SLOW_ASTERN':
            return Event.DEAD_SLOW_ASTERN
        elif label.upper() == 'SLOW_ASTERN':
            return Event.SLOW_ASTERN
        elif label.upper() == 'HALF_ASTERN':
            return Event.HALF_ASTERN
        elif label.upper() == 'FULL_ASTERN':
            return Event.FULL_ASTERN
        # relative change ..................
        elif label.upper() == 'INCREASE_VELOCITY':
            return Event.INCREASE_VELOCITY
        elif label.upper() == 'EVEN':
            return Event.EVEN
        elif label.upper() == 'DECREASE_VELOCITY':
            return Event.DECREASE_VELOCITY
        # movement directives ..............
        elif label.upper() == 'VELOCITY':
            return Event.VELOCITY
        elif label.upper() == 'THETA':
            return Event.THETA
        elif label.upper() == 'PORT_VELOCITY':
            return Event.PORT_VELOCITY
        elif label.upper() == 'PORT_THETA':
            return Event.PORT_THETA
        elif label.upper() == 'STBD_VELOCITY':
            return Event.STBD_VELOCITY
        elif label.upper() == 'STBD_THETA':
            return Event.STBD_THETA
        elif label.upper() == 'INCREASE_PORT_VELOCITY':
            return Event.INCREASE_PORT_VELOCITY
        elif label.upper() == 'DECREASE_PORT_VELOCITY':
            return Event.DECREASE_PORT_VELOCITY
        elif label.upper() == 'INCREASE_STBD_VELOCITY':
            return Event.INCREASE_STBD_VELOCITY
        elif label.upper() == 'DECREASE_STBD_VELOCITY':
            return Event.DECREASE_STBD_VELOCITY
        elif label.upper() == 'INCREASE_PORT_THETA':
            return Event.INCREASE_PORT_THETA
        elif label.upper() == 'DECREASE_PORT_THETA':
            return Event.DECREASE_PORT_THETA
        elif label.upper() == 'INCREASE_STBD_THETA':
            return Event.INCREASE_STBD_THETA
        elif label.upper() == 'DECREASE_STBD_THETA':
            return Event.DECREASE_STBD_THETA
        # port turns .......................
        elif label.upper() == 'TURN_AHEAD_PORT':
            return Event.TURN_AHEAD_PORT
        elif label.upper() == 'TURN_TO_PORT':
            return Event.TURN_TO_PORT
        elif label.upper() == 'TURN_ASTERN_PORT':
            return Event.TURN_ASTERN_PORT
        elif label.upper() == 'SPIN_PORT':
            return Event.SPIN_PORT
        # starboard turns ..................
        elif label.upper() == 'SPIN_STBD':
            return Event.SPIN_STBD
        elif label.upper() == 'TURN_ASTERN_STBD':
            return Event.TURN_ASTERN_STBD
        elif label.upper() == 'TURN_TO_STBD':
            return Event.TURN_TO_STBD
        elif label.upper() == 'TURN_AHEAD_STBD':
            return Event.TURN_AHEAD_STBD
        # high level behaviours ............
        elif label.upper() == 'ROAM':
            return Event.ROAM
        elif label.upper() == 'SNIFF':
            return Event.SNIFF
        elif label.upper() == 'VIDEO':
            return Event.VIDEO
        elif label.upper() == 'EVENT_L2':
            return Event.EVENT_L2
        elif label.upper() == 'EVENT_R1':
            return Event.EVENT_R1
        elif label.upper() == 'LIGHTS':
            return Event.LIGHTS
        elif label.upper() == 'MOTION_DETECT':
            return Event.MOTION_DETECT
        # other behaviours (> 500) .........
        elif label.upper() == 'NO_ACTION':
            return Event.NO_ACTION
        elif label.upper() == 'CLOCK_TICK':
            return Event.CLOCK_TICK
        elif label.upper() == 'CLOCK_TOCK':
            return Event.CLOCK_TOCK
        else:
            raise NotImplementedError

#EOF
