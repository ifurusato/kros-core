#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2021-09-29
# modified: 2021-10-06
#
# A example template for a Macro. Copy and modify this file.
#
# Be careful defining global variables!
#

import sys, traceback

import core.globals as globals
from core.logger import Logger, Level

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_template_log = Logger('template-macro', Level.ERROR)
_kros = globals.get('kros')
if _kros:
    try:
        _template_log.info('found KROS! begin loading macro...')
        _macro_publisher = _kros.get_macro_publisher()
        if _macro_publisher:

            _macro_name = 'template'
            _macro_description = 'a macro template.' # optional
            _macro = _macro_publisher.create_macro(_macro_name, _macro_description)

            # move slow ahead for 3 seconds (duration argument is in milliseconds)
            _macro.add_event(Event.SLOW_AHEAD, 3000)
            # come to a halt for 2.5 seconds
            _macro.add_event(Event.HALT, 2500)
            # print an emoji via a lambda function
            _func = lambda: globals.get('kros').get_logger().info('🤣 Done!')
            _macro.add_function(_func, 1000)
            _template_log.info('loaded.')

        else:
            _template_log.warning('macro processor not available..')

    except Exception as e:
        _template_log.error('{} encountered, exiting: {}'.format(type(e), e))
        traceback.print_exc(file=sys.stdout)
    finally:
        pass
else:
    _template_log.error('KROS not available.')

#EOF
