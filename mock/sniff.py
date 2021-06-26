#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-06-26
#

from threading import Thread
from abc import ABC, abstractmethod
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event
from core.subscriber import Subscriber
from core.behaviour import Behaviour

# ...............................................................
class Sniff(Behaviour):
    '''
    Implements a sniffing behaviour.

    :param name:           the name of this behaviour
    :param loop_freq_hz:   the loop frequency in Hertz
    :param callback:       the optional callback function (can be added later)
    :param level:          the optional log level
    '''
    def __init__(self, config, message_bus, motors, level=Level.INFO):
        if config is None:
            raise ValueError('null configuration argument.')
        cfg = config['kros'].get('sniff')
        _loop_freq_hz = cfg.get('loop_freq_hz')
        super().__init__('sniff', _loop_freq_hz, self._sniff_callback, level)
        self._config      = config
        self._message_bus = message_bus
        self._motors      = motors
        self._log.info('ready.')

    # ..........................................................................
    @property
    def event(self):
        return Event.SNIFF

    # ..........................................................................
    def _sniff_callback(self):
        self._log.info('🌺 sniff callback.')

#   # ..........................................................................
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        super().start()

    # ..........................................................................
    @property
    def name(self):
        return 'sniff'

    # ..........................................................................
    def execute(self):
        '''
        The method called upon each loop iteration. This does nothing in this
        abstract class and is meant to be extended by subclasses.
        '''
        _timestamp = self._message_bus.last_message_timestamp
        if _timestamp is None:
            self._log.info('🌺 sniff loop execute; no previous messages.')
        else:
            _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
            self._log.info('🌺 sniff loop execute; {}'.format(Subscriber.get_formatted_time('message age:', _elapsed_ms)))

#   # ..........................................................................
#   def suppressed(self):
#   def suppress(self, mode):

#EOF
