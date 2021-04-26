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

import time
import datetime as dt
from colorama import init, Fore, Style
init()

from core.event import Event
from core.logger import Logger, Level

# ..............................................................................
class Controller():
    '''
    A default controller class that receives callbacks (to the 'callback'
    method) when Events appear on the MessageBus' Arbitratror.
    '''
    def __init__(self, level):
        self._log = Logger('controller', level)
        self._enabled = True
        self._log.info('ready.')

    # ................................................................
    def enable(self):
        self._enabled = True
        self._log.info('enabled.')

    # ................................................................
    def disable(self):
        self._enabled = False
        self._log.info('disabled.')

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
        # 🍎 🍏 🍈  🍋 🍐 🍑 🍓  🥝 🥚 🥧 🧀
        self._log.info('🍥 callback with payload {}'.format(payload.event.name))
        if not self._enabled:
            self._log.warning('action ignored: controller disabled.')
            return

        _start_time = dt.datetime.now()

        _event = payload.event
        self._log.info(Fore.CYAN + 'act()' + Style.BRIGHT + ' event: {}.'.format(_event) + Fore.YELLOW)

        # no action ............................................................
        if _event is Event.NO_ACTION:
            self._log.info('event: no action.')
            pass

        # EVENT UNKNOWN: FAILURE ...............................................
        else:
            self._log.error('unrecognised event: {}'.format(_event))
            pass

        _delta = dt.datetime.now() - _start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        self._log.debug(Fore.MAGENTA + Style.DIM + 'elapsed: {}ms'.format(_elapsed_ms) + Style.DIM)

# EOF
