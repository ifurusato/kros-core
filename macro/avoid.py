#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2021-09-29
# modified: 2021-09-29
#
# A example template for a Macro. Copy and modify this file.
#

import sys, traceback

import core.globals as globals
from core.logger import Logger, Level
from core.system import System

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_avoid_log = Logger('avoid-macro', Level.ERROR)
_kros = globals.get('kros')
if _kros:
    try:
        _avoid_log.info('found KROS! begin loading macro...')
        _avoid_log.heading('Avoid Macro', 'An avoidance behaviour that backs away from an obstacle and turns.')
        _macro_publisher = _kros.get_macro_publisher()
        if _macro_publisher:

            _macro_name = 'avoid'
            _macro_description = 'a simple avoidance behaviour.' # optional
            _macro = _macro_publisher.create_macro(_macro_name, _macro_description)

            # print an emoji to the KROS log console
            _func1 = lambda: globals.get('kros').get_logger().info('😈 AVOID begin!')
            _macro.add_function(_func1)

            # come to a stop for 1 second
            _macro.add_event(Event.STOP, 1000)
            # move half astern for 2.5 seconds (duration argument is in milliseconds)
            _macro.add_event(Event.HALF_ASTERN, 100)
            # slow the reversing of the port motor to turn to starboard for a half second
#           _macro.add_event(Event.INCREASE_PORT_VELOCITY, 100)
#           _macro.add_event(Event.INCREASE_PORT_VELOCITY, 100)
            _macro.add_event(Event.INCREASE_PORT_VELOCITY, 100)
            # come to a halt for 2 seconds
            _macro.add_event(Event.HALT, 1000)
            _macro.add_event(Event.STOP, 50)

            # notify on completion of macro via a lambda function
            _func2 = lambda: globals.get('kros').get_macro_publisher().on_completion('😃 COMPLETE!')
            _macro.add_function(_func2)

            # print an emoji to the KROS log console
            _func3 = lambda: globals.get('kros').get_logger().info('💀 Done!')
            _macro.add_function(_func3)

            _avoid_log.info('loaded.')

        else:
            _avoid_log.error('😥 macro processor not available..')

    except Exception as e:
        _avoid_log.error('😨 {} encountered, exiting: {}'.format(type(e), e))
        traceback.print_exc(file=sys.stdout)
    finally:
        pass
else:
    _avoid_log.error('KROS not available.')

#EOF
