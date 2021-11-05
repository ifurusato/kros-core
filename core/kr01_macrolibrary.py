#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2021-09-23
# modified: 2021-10-30
#
# Macro instances used for the KR01 robot.
#

from colorama import init, Fore, Style
init(autoreset=True)

import core.globals as globals
globals.init()

from core.logger import Logger, Level
from core.event import Event
from core.orientation import Orientation
from core.direction import Direction
from core.speed import Speed
from core.macros import Macro, MacroLibrary

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class KR01MacroLibrary(MacroLibrary):
    '''
    The MacroLibrary for the KR01.

    Commands directly contained within the Macro are executed as the Macro is
    parsed, which can be used to initialise features but is otherwise not
    executed again.

    Commands to be executed when the Macro is triggered must either be added
    as Events (using the add_event() method) or as lambda functions (using
    the add_function() method).
    '''
    def __init__(self, macro_publisher, level=Level.INFO):
        MacroLibrary.__init__(self, 'kr01', level)
        self._macro_publisher = macro_publisher
        # now create instances of the Macro subclasses in this class.
        self.put(AvoidMacro())
        self.put(TestMacro())
        self._log.info('ready.')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class AvoidMacro(Macro):

    def __init__(self, *args):
        Macro.__init__(self, name='avoid', description='a simple avoidance behaviour')
#       self._macro_publisher = macro_publisher

        # notify on start of macro via a lambda function
        self.add_function(lambda: globals.get('macro-publisher').on_begin('🍏 BEGIN!'))

        # come to a stop for 500ms
        self.add_event(Event.STOP, duration_ms=500)

        # move half astern for 2.5 seconds (duration argument is in milliseconds)
        self.add_event(Event.HALF_ASTERN, duration_ms=200)

        # slow the reversing of the port motor to turn to starboard for a half second
        self.add_event(Event.PORT_VELOCITY, (Orientation.PORT, Direction.ASTERN, Speed.DEAD_SLOW))
        self.add_event(Event.STBD_VELOCITY, (Orientation.STBD, Direction.ASTERN, Speed.STOP))

        # come to a halt for 1 second
        self.add_event(Event.HALT, duration_ms=500)

        # print an emoji to the KROS log console
        self.add_function(lambda: globals.get('kros').get_logger().info('🍊 message logged!'))

        # notify on completion of macro via a lambda function
        self.add_function(lambda: globals.get('macro-publisher').on_completion('🍎 COMPLETE!'))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestMacro(Macro):

    def __init__(self, *args):
        Macro.__init__(self, name='test', description='a simple test macro')
#       self._macro_publisher = macro_publisher
        # notify on start of macro via a lambda function
        self.add_function(lambda: globals.get('macro-publisher').on_begin('🍏 BEGIN!'))

        # 1. event with duration in milliseconds ...............................

        # come to a stop
#       self.add_event(Event.STOP, duration_ms=123)

        # 2. event with direction and speed ....................................

        self.add_event(Event.PORT_VELOCITY, (Direction.ASTERN, Speed.DEAD_SLOW))

        # 3. event with direction, speed, and duration .........................

#       self.add_event(Event.STBD_VELOCITY, (Direction.AHEAD, Speed.DEAD_SLOW), duration_ms=333)

        # 4. event with current state event ....................................

        # TODO

        # notify on completion of macro via a lambda function
#       self.add_function(lambda: globals.get('macro-publisher').on_completion('🍎 COMPLETE!'))

#EOF
