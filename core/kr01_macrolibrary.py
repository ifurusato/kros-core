#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2021-09-23
# modified: 2021-10-15
#
# Macro instances used for the KR01 robot.
#

from colorama import init, Fore, Style
init(autoreset=True)

import core.globals as globals
globals.init()

from core.logger import Logger, Level
from core.event import Event
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
        self.put(AvoidMacro(self._macro_publisher))
        self._log.info('ready.')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class AvoidMacro(Macro):

    def __init__(self, macro_publisher):
        Macro.__init__(self, name='avoid', description='a simple avoidance behaviour')
        self._macro_publisher = macro_publisher
        # come to a stop for 500ms
        self.add_event(Event.STOP, 500)

        self.add_function(lambda: globals.get('kros').get_macro_publisher().on_poot('🍊 POOT!'))

        # move half astern for 2.5 seconds (duration argument is in milliseconds)
        self.add_event(Event.HALF_ASTERN, 300)

        # slow the reversing of the port motor to turn to starboard for a half second
        self.add_event(Event.PORT_VELOCITY, (Direction.ASTERN, Speed.DEAD_SLOW))
        self.add_event(Event.STBD_VELOCITY, (Direction.ASTERN, Speed.ONE_THIRD))

        # come to a halt for 1 second
        self.add_event(Event.HALT, 1000)

        # notify on completion of macro via a lambda function
        self.add_function(lambda: globals.get('kros').get_macro_publisher().on_completion('🍅 COMPLETE!'))


        # print an emoji to the KROS log console
        _func5 = lambda: globals.get('kros').get_logger().info('⛔ Done!')
        self.add_function(_func5)

#EOF
