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

import time
from threading import Thread
from abc import ABC, abstractmethod
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event
from core.subscriber import Subscriber
from core.behaviour import Behaviour

#from mock.indicator import Indicator
from mock.rgbmatrix import RgbMatrix, Color, DisplayType, WipeDirection

# ...............................................................
class Roam(Behaviour):
    '''
    Implements a roaming behaviour.

    :param name:           the name of this behaviour
    :param loop_freq_hz:   the loop frequency in Hertz
    :param callback:       the optional callback function (can be added later)
    :param level:          the optional log level
    '''
    def __init__(self, config, message_bus, motors, level=Level.INFO):
        if config is None:
            raise ValueError('null configuration argument.')
        cfg = config['kros'].get('roam')
        _loop_freq_hz = cfg.get('loop_freq_hz')
        super().__init__('roam', _loop_freq_hz, self._roam_callback, level)
        self._config      = config
        self._message_bus = message_bus
        self._motors      = motors
        self._rgbmatrix = RgbMatrix(Level.INFO)
        self._rgbmatrix.set_display_type(DisplayType.RANDOM)
#       self._indicator = Indicator(Level.INFO)
#       self._indicator.set_display_type(DisplayType.RANDOM)
        self._log.info('ready.')

    # ..........................................................................
    def enable(self):
        '''
        The necessary state machine call to enable the publisher.
        '''
        super().enable()
#       self._indicator.enable()
        self._rgbmatrix.enable()

    # ..........................................................................
    def disable(self):
        '''
        The state machine call to disable the publisher.
        '''
        self._disable_rgbmatrix()
        super().disable()
#       self._indicator.disable()

    # ..........................................................................
    def _disable_rgbmatrix(self):
        self._rgbmatrix.set_color(Color.BLACK)
        time.sleep(0.2)
        self._rgbmatrix.clear()
        time.sleep(0.2)
        self._rgbmatrix.disable()

    # ..........................................................................
    @property
    def event(self):
        return Event.ROAM

    # ..........................................................................
    def _roam_callback(self):
        self._log.info('🌼 roam callback.')

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
        return 'roam'

    # ..........................................................................
    def execute(self):
        '''
        The method called upon each loop iteration. This does nothing in this
        abstract class and is meant to be extended by subclasses.
        '''
        _timestamp = self._message_bus.last_message_timestamp
        if _timestamp is None:
            self._log.info('🌼 roam loop execute; no previous messages.')
        else:
            _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
            self._log.info('🌼 roam loop execute; {}'.format(Subscriber.get_formatted_time('message age:', _elapsed_ms)))

#   # ..........................................................................
#   def suppressed(self):
#   def suppress(self, mode):

#EOF
