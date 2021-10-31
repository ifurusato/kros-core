#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-10-30
# modified: 2021-10-31
#

from core.stringbuilder import StringBuilder
from core.message import Payload
from core.orientation import Orientation
from core.direction import Direction
from core.speed import Speed

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MotorDirective(Payload):
    '''
    A Message's payload when used as a motor directive, containing the Event
    (with priority) and a specialised value with an Orientation, a Speed and
    a Direction. Not all directives will have values for all three parameters.
    If queried for its value it will return a tuple containing the three
    parameters, with additional property getters for each.

    :param orientation:   the Orientation of the motor (i.e., which motor)
    :param direction:     the Direction, ahead (forward) or astern (reverse)
    :param speed:         the Speed of the directive
    '''
    def __init__(self, event, orientation, direction, speed):
        if not isinstance(orientation, Orientation):
            raise TypeError('expected Orientation, not {}'.format(type(orientation)))
        if not isinstance(direction, Direction):
            raise TypeError('expected Direction, not {}'.format(type(direction)))
        if not isinstance(speed, Speed):
            raise TypeError('expected Speed, not {}'.format(type(speed)))
        Payload.__init__(self, event, ( orientation, direction, speed ))

    # priority ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def priority(self):
        return self._event.priority

    # event ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def event(self):
        return self._event

    # orientation ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def orientation(self):
        return self._value[0]

    # direction ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def direction(self):
        return self._value[1]

    # speed ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def speed(self):
        return self._value[2]

    # value ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __hash__(self):
        return hash((self._event, self._value))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __eq__(self, other):
        return isinstance(other, MotorDirective) and self.__hash__() == other.__hash__()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __str__(self):
        _sb = StringBuilder('MotorDirective[', indent=6, delim='\n')
        _sb.append('id={}'.format(id(self)))
        _sb.append('hash={}'.format(hash(self)))
        _sb.append('priority={}'.format(self.priority))
        _sb.append('event={}'.format(self.event))
        _sb.append('direction={}'.format(self.direction))
        _sb.append('speed={}'.format(self.speed))
        _sb.append(']', indent=4, delim=StringBuilder.NONE)
        return _sb.to_string()

    # not equals ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#  def __ne__(self, other):
#       return not self == other

#EOF
