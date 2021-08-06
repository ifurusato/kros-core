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

from core.speed import Speed, Direction

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
#   CLOCK     = 11
    OTHER     = 12

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Event(Enum):
    '''
    Events are used as part of a message Payload, which includes the Event
    as a type. The Payload may as well as contain a value.

    Messages are prioritised by their Event type, where the priority operates
    in reverse-order: the smaller the number the higher the priority.
    '''
    # name                     n   label                  priority   group
    # misc events ...........................................................................
    NOOP                   = ( 0, "no operation",            1000,   Group.NONE )

    # system events .........................................................................
    SHUTDOWN               = ( 10, "shutdown",                  1,   Group.SYSTEM )
    BATTERY_LOW            = ( 11, "battery low",               1,   Group.SYSTEM )
    HIGH_TEMPERATURE       = ( 12, "high temperature",          1,   Group.SYSTEM )
    COLLISION_DETECT       = ( 13, "collision detect",          2,   Group.SYSTEM )
#   EMERGENCY_ASTERN       = ( 14, "emergency astern",          2,   Group.SYSTEM )

    # gamepad events ........................................................................
    GAMEPAD                = ( 40, "gamepad",                  10,   Group.GAMEPAD )

    # stopping and halting ..................................................................
    STOP                   = ( 50, "stop",                     12,   Group.STOP )
    HALT                   = ( 51, "halt",                     13,   Group.STOP )
    BRAKE                  = ( 52, "brake",                    14,   Group.STOP )
    STANDBY                = ( 53, "standby",                  15,   Group.STOP )
    BUTTON                 = ( 54, "button",                   16,   Group.STOP )

    # bumper ................................................................................
    BUMPER_PORT            = ( 110, "bumper port",             40,   Group.BUMPER )
    BUMPER_CNTR            = ( 111, "bumper center",           40,   Group.BUMPER )
    BUMPER_STBD            = ( 112, "bumper stbd",             40,   Group.BUMPER )

    # infrared ..............................................................................
    INFRARED_PORT_SIDE     = ( 120, "infrared port side",      50,   Group.INFRARED )
    INFRARED_PORT          = ( 121, "infrared port",           50,   Group.INFRARED )
    INFRARED_CNTR          = ( 122, "infrared cntr",           50,   Group.INFRARED )
    INFRARED_STBD          = ( 123, "infrared stbd",           50,   Group.INFRARED )
    INFRARED_STBD_SIDE     = ( 124, "infrared stbd side",      50,   Group.INFRARED )

    # velocity directives ...................................................................
    VELOCITY               = ( 200, "velocity",               100,   Group.VELOCITY ) # with value
    PORT_VELOCITY          = ( 201, "port velocity",          100,   Group.VELOCITY ) # with value
    STBD_VELOCITY          = ( 202, "stbd velocity",          100,   Group.VELOCITY ) # with value
    INCREASE_PORT_VELOCITY = ( 203, "increase port velocity", 100,   Group.VELOCITY )
    DECREASE_PORT_VELOCITY = ( 204, "decrease port velocity", 100,   Group.VELOCITY )
    INCREASE_STBD_VELOCITY = ( 205, "increase stbd velocity", 100,   Group.VELOCITY )
    DECREASE_STBD_VELOCITY = ( 206, "decrease stbd velocity", 100,   Group.VELOCITY )
    INCREASE_VELOCITY      = ( 207, "increase velocity",      100,   Group.VELOCITY )
    DECREASE_VELOCITY      = ( 208, "decrease velocity",      100,   Group.VELOCITY )

    # theta directives ......................................................................
    THETA                  = ( 300, "theta",                  100,   Group.THETA ) # with value
    PORT_THETA             = ( 301, "port theta",             100,   Group.THETA )
    STBD_THETA             = ( 302, "stbd theta",             100,   Group.THETA )
    EVEN                   = ( 303, "even",                   100,   Group.THETA )
    INCREASE_PORT_THETA    = ( 304, "increase port theta",    100,   Group.THETA )
    DECREASE_PORT_THETA    = ( 305, "decrease port theta",    100,   Group.THETA )
    INCREASE_STBD_THETA    = ( 306, "increase stbd theta",    100,   Group.THETA )
    DECREASE_STBD_THETA    = ( 307, "decrease stbd theta",    100,   Group.THETA )
    # port turns ...........
    TURN_AHEAD_PORT        = ( 310, "turn ahead port",        100,   Group.THETA )
    TURN_TO_PORT           = ( 311, "turn to port",           100,   Group.THETA ) # based on current avg direction
    TURN_ASTERN_PORT       = ( 312, "turn astern port",       100,   Group.THETA )
    SPIN_PORT              = ( 313, "spin port",              100,   Group.THETA )
    # starboard turns ......
    SPIN_STBD              = ( 320, "spin stbd",              100,   Group.THETA )
    TURN_ASTERN_STBD       = ( 321, "turn astern stbd",       100,   Group.THETA )
    TURN_TO_STBD           = ( 322, "turn to stbd",           100,   Group.THETA ) # based on current avg direction
    TURN_AHEAD_STBD        = ( 323, "turn ahead stbd",        100,   Group.THETA )

    # chadburn event ........................................................................
    # the num values here are fixed, and used in ./hardware/motors
    # astern ...............
    ASTERN                 = ( 400, "astern",                 100,   Group.CHADBURN, Direction.ASTERN ) # with value
    DEAD_SLOW_ASTERN       = ( 401, "dead slow astern",       100,   Group.CHADBURN, Direction.ASTERN, Speed.DEAD_SLOW )
    SLOW_ASTERN            = ( 402, "slow astern",            100,   Group.CHADBURN, Direction.ASTERN, Speed.SLOW )
    HALF_ASTERN            = ( 403, "half astern",            100,   Group.CHADBURN, Direction.ASTERN, Speed.HALF )
    FULL_ASTERN            = ( 404, "full astern",            100,   Group.CHADBURN, Direction.ASTERN, Speed.FULL )
    # ahead ................
    AHEAD                  = ( 410, "ahead",                  100,   Group.CHADBURN, Direction.AHEAD ) # with value
    DEAD_SLOW_AHEAD        = ( 411, "dead slow ahead",        100,   Group.CHADBURN, Direction.AHEAD, Speed.DEAD_SLOW )
    SLOW_AHEAD             = ( 412, "slow ahead",             100,   Group.CHADBURN, Direction.AHEAD, Speed.SLOW )
    HALF_AHEAD             = ( 413, "half ahead",             100,   Group.CHADBURN, Direction.AHEAD, Speed.HALF )
    FULL_AHEAD             = ( 414, "full ahead",             100,   Group.CHADBURN, Direction.AHEAD, Speed.FULL )

    # high level behaviours .................................................................
    AVOID                  = ( 500, "avoid",                  150,   Group.BEHAVIOUR )
    MOTION_DETECT          = ( 501, "motion detect",          151,   Group.BEHAVIOUR )
    ROAM                   = ( 502, "roam",                   160,   Group.BEHAVIOUR )
    MOTH                   = ( 503, "moth",                   161,   Group.BEHAVIOUR )
    SNIFF                  = ( 504, "sniff",                  162,   Group.BEHAVIOUR ) # A Button
    EVENT_L2               = ( 505, "L2",                     163,   Group.BEHAVIOUR ) # L2 Button
    EVENT_R1               = ( 506, "cruise",                 164,   Group.BEHAVIOUR ) # R1 Button
    LIGHTS                 = ( 507, "lights",                 165,   Group.BEHAVIOUR ) # R2 Button
    VIDEO                  = ( 508, "video",                  175,   Group.BEHAVIOUR ) # L1 Button
    IDLE                   = ( 509, "idle",                   180,   Group.BEHAVIOUR ) # A Button

    # other events (> 900) ..................................................................
    NO_ACTION              = ( 999, "no action",              999,   Group.OTHER )
    ANY                    = ( 1000, "any",                  1000,   Group.OTHER )

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, num, label, priority, group, direction=None, speed=None):
        self._num       = num
        self._label     = label
        self._priority  = priority
        self._group     = group
        self._direction = direction
        self._speed     = speed

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
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

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def is_system_event(event):
        return event.group is Group.SYSTEM

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def is_bumper_event(event):
        return event.group is Group.BUMPER

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def is_infrared_event(event):
        return event.group is Group.INFRARED

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def is_ifs_event(event):
        '''
        A convenience method that returns True for all bumper and
        infrared events.
        '''
        return Event.is_bumper_event(event) or Event.is_infrared_event(event)

    # properties ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def num(self):
        return self._num

    @property
    def label(self):
        return self._label

    @property
    def priority(self):
        return self._priority

    @property
    def group(self):
        return self._group

    @property
    def direction(self):
        return self._direction

    @property
    def speed(self):
        return self._speed

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
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

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
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

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def compare_to_priority_of(self, event):
        '''
        Returns 1 if the Event of the argument is a higher priority
        (lower number) than this Event; a -1 if the Event of the
        argument is a lower priority (higher number) than this Event;
        and 0 if they have the same priority.
        '''
        if not isinstance(event, Event):
            raise ValueError('expected event argument, not {}'.format(type(event)))
        elif self._priority < event.priority:
            return 1
        elif self._priority > event.priority:
            return -1
        else:
            return 0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __str__(self):
        '''
        Return the string value returned for an enum.
        '''
        return self.name

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def from_string(value):
        for e in Event:
            if value.upper() == e.name:
                return e
        raise NotImplementedError

#EOF
