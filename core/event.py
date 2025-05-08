#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-02-21
# modified: 2025-05-07
#

from enum import Enum

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Group(Enum):
    #             num   name
    NONE       = (  0, "none" )
    SYSTEM     = (  1, "system" )
    BUMPER     = (  5, "bumper" )
    INFRARED   = (  6, "infrared" )
    IDLE       = ( 13, "idle" )
    OTHER      = ( 17, "other" )

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, num, name):
        self._num  = num
        self._name = name

    # properties ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def num(self):
        return self._num

    @property
    def name(self):
        return self._name

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Event(Enum):
    '''
    Events are used as part of a message Payload, which includes the Event
    as a type. The Payload may as well as contain a value.

    TODO: define priority as an Enum rather than an int.

    Messages are prioritised by their Event type, where the priority operates
    in reverse-order: the smaller the number the higher the priority.
    '''
    # name                     n   name                   priority   group
    # misc events ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    NOOP                   = ( 0, "no operation",            1000,   Group.NONE )

    # system events ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    SHUTDOWN               = ( 10, "shutdown",                  1,   Group.SYSTEM )
    BATTERY_LOW            = ( 11, "battery low",               1,   Group.SYSTEM )
    REGULATOR_5V_LOW       = ( 12, "regulator 5v low",          1,   Group.SYSTEM )
    REGULATOR_3V3_LOW      = ( 13, "regulator 3.3v low",        1,   Group.SYSTEM )
    HIGH_TEMPERATURE       = ( 14, "high temperature",          1,   Group.SYSTEM )
    OVER_CURRENT           = ( 15, "over current",              1,   Group.SYSTEM )
    NO_CONNECTION          = ( 16, "no connection",             1,   Group.SYSTEM )
    DISCONNECTED           = ( 17, "disconnected",              1,   Group.SYSTEM )

    # bumper ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    BUMPER_ANY             = ( 110, "any bumper",               4,   Group.BUMPER )
    BUMPER_MAST            = ( 111, "mast bumper",              4,   Group.BUMPER )
    BUMPER_PORT            = ( 112, "port bumper",              4,   Group.BUMPER )
    BUMPER_CNTR            = ( 113, "center bumper",            4,   Group.BUMPER )
    BUMPER_STBD            = ( 114, "starboard bumper",         4,   Group.BUMPER )
    BUMPER_PFWD            = ( 115, "port fwd bumper",          4,   Group.BUMPER )
    BUMPER_PAFT            = ( 116, "port aft bumper",          4,   Group.BUMPER )
    BUMPER_SFWD            = ( 117, "starboard fwd bumper",     4,   Group.BUMPER )
    BUMPER_SAFT            = ( 118, "starboard aft bumper",     4,   Group.BUMPER )
    BUMPER_FOBP            = ( 119, "fwd oblique port",        10,   Group.BUMPER )
    BUMPER_FOBS            = ( 120, "fwd oblique starboard",   10,   Group.BUMPER )

    # infrared ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    INFRARED_PORT          = ( 130, "infrared port",           51,   Group.INFRARED )
    INFRARED_CNTR          = ( 131, "infrared cntr",           50,   Group.INFRARED )
    INFRARED_STBD          = ( 132, "infrared stbd",           51,   Group.INFRARED )

    # idle ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    IDLE                   = ( 600, "idle",                   100,   Group.IDLE )

    # other events (> 900) ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    NO_ACTION              = ( 900, "no action",              998,   Group.OTHER )
    RGB                    = ( 909, "rgb",                    999,   Group.OTHER )
    ANY                    = ( 1000, "any",                  1000,   Group.OTHER )

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, num, name, priority, group, directive=None, speed=None):
        self._num       = num
        self._name      = name
        self._priority  = priority
        self._group     = group
        self._directive = directive
        self._speed     = speed

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def from_number(value):
        for e in Event:
            if value == e._num:
                return e
        raise NotImplementedError

    # properties ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def num(self):
        return self._num

    @property
    def name(self):
        return self._name

    @property
    def priority(self):
        return self._priority

    @property
    def group(self):
        return self._group

    @property
    def directive(self):
        return self._directive

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

    def __lt__(self, other):
        return self.__hash__() < other.__hash__()

    def __hash__(self):
        return hash(self._num)

    def __eq__(self, other):
        return isinstance(other, Event) and self.__hash__() is other.__hash__()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def from_string(value):
        for e in Event:
            if value.upper() == e.name:
                return e
        raise NotImplementedError

#EOF
