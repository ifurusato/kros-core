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
# A example template for a Script. Copy and modify this file.
#

import sys, traceback

import core.globals as globals
from core.logger import Logger, Level

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_log = Logger('avoid-macro', Level.INFO)
_kros = globals.get('kros')
if _kros:
    try:
        _log.info('found KROS! begin loading script...')
        _macro_publisher = _kros.get_macro_publisher()
        if _macro_publisher:

            _script_name = 'avoid'
            _script_description = 'a simple avoidance behaviour.' # optional
            _script = _macro_publisher.create_script(_script_name, _script_description)

            # come to a stop for 1 second
            _script.add_event(Event.STOP, 1000)
            # move half astern for 3 seconds (duration argument is in milliseconds)
            _script.add_event(Event.HALF_ASTERN, 3000)
            # slow the reversing of the port motor to turn to starboard for a half second
            _script.add_event(Event.INCREASE_PORT_VELOCITY, 500)
            # come to a halt for 2.5 seconds
            _script.add_event(Event.HALT, 2500)
            # print an emoji via a lambda function
            _func = lambda: _log.info('😥')
            _script.add_function(_func, 1)
            _log.info('loaded.')

        else:
            _log.warning('macro processor not available..')

    except Exception as e:
        _log.error('{} encountered, exiting: {}'.format(type(e), e))
        traceback.print_exc(file=sys.stdout)
    finally:
        pass
else:
    _log.error('KROS not available.')

#EOF
