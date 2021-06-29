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
from core.fsm import State
from core.subscriber import Subscriber
from core.behaviour import Behaviour
from core.subscriber import Subscriber

#from mock.indicator import Indicator
from mock.rgbmatrix import RgbMatrix, Color, DisplayType, WipeDirection

# ..............................................................................
class Roam(Subscriber, Behaviour):
    '''
    Implements a roaming behaviour. 

    This is also a Subscriber to INFRARED_CNTR events, altering the usage of
    the center analog IR sensor to no longer function solely for obstacle 
    avoidance, but instead set the robot's target velocity as a proportion to 
    the perceived distance. I.e., if the sensor sees nothing at its maximum 
    range the robot's forward target velocity will be set to its maximum. As 
    the sensed distance is lessened the target velocity is likewise, until the 
    robot reaches a minimum distance in which it stops and then goes into an 
    obstacle avoidance behaviour (handled elsewhere).

    An option is to set the maximum distance to roam, so that the robot
    accelerates to roaming speed, varies its speed as described above,
    then as it nears its target distance, decelerates to a stop at the
    target.

    :param config:         the application configuration
    :param message_bus:    the asynchronous message bus
    :param motors:         the motor controller
    :param level:          the optional log level
    '''
    def __init__(self, config, message_bus, motors, level=Level.INFO):
        if config is None:
            raise ValueError('null configuration argument.')
        self._config      = config
        cfg = config['kros'].get('roam')
        _loop_freq_hz = cfg.get('loop_freq_hz')
        Behaviour.__init__(self, 'roam', _loop_freq_hz, self._roam_callback, level)
        self._message_bus = message_bus
        self._motors      = motors
        Subscriber.__init__(self, 'roam', self._message_bus, Fore.GREEN, level)
        self._distance    = None
        self._rgbmatrix   = RgbMatrix(Level.INFO)
        self._rgbmatrix.set_display_type(DisplayType.RANDOM)
#       self._indicator = Indicator(Level.INFO)
#       self._indicator.set_display_type(DisplayType.RANDOM)
        self.events = [ Event.INFRARED_CNTR ]
        self._log.info('ready.')

    # ..........................................................................
    @property
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, distance):
        self._log.info('🍆 setting distance to: {}'.format(distance))
        self._distance = distance

    # ..........................................................................
    def enable(self):
        '''
        The necessary state machine call to enable the publisher.
        '''
        self._log.info(Fore.YELLOW + '🎾 1. enabled: {}'.format(self.enabled))
        super().enable()
        self._log.info(Fore.YELLOW + '🎾 2. enabled: {}'.format(self.enabled))
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
    async def process_message(self, message):
        '''
        We expect only INFRARED_CNTR messages and extract the distance value.
        '''
        # TODO only pay attention to messages if roam active and not suppressed 
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected.')
        # indicate that this subscriber has processed the message
        message.process(self)
        _payload = message.payload
        _event   = _payload.event
        if _event is Event.INFRARED_CNTR:
            self.distance = _payload.value
            self._log.info('🆎 processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.description) 
                    + Fore.GREEN + ' distance: {}'.format(self.distance))
        else:
            raise ValueError('expected INFRARED_CNTER event not: {}'.format(message.event.description))

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
        self._log.info('🌼 roam callback; distance: {}'.format(self.distance))

#   # ..........................................................................
    def start(self):
        '''
        The state machine call to start the roam behaviour. Because this method
        is part of both superclasses we need to only call it once.
        '''
        if self.state is not State.STARTED:
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
            self._log.info('🌼 roam loop execute; {};\t'.format(Subscriber.get_formatted_time('message age:', _elapsed_ms)) 
                    + 'distance: {}'.format(self.distance))

#   # ..........................................................................
#   def suppressed(self):
#   def suppress(self, mode):

#EOF
