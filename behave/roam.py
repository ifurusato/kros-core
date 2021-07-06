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
from abc import ABC, abstractmethod
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event
from core.orient import Orientation
from core.fsm import State
from behave.behaviour import Behaviour

#from mock.rgbmatrix import RgbMatrix, Color, DisplayType, WipeDirection

# ..............................................................................
class Roam(Behaviour):
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
    :param message_factory: the factory for messages
    :param motors:         the motor controller
    :param level:          the optional log level
    '''
    def __init__(self, config, message_bus, message_factory, motors, level=Level.INFO):
        Behaviour.__init__(self, 'roam', config, message_bus, message_factory, self.execute, level)
        self._motors       = motors
        self._distance     = None
        self._speed_limit  = None
        self._min_distance = 20.0 # cm
        self._max_distance = 200.0 # cm
        self._min_speed    = 0.0
        self._max_speed    = 100.0
#       self._rgbmatrix    = RgbMatrix(Level.INFO)
#       self._rgbmatrix.set_display_type(DisplayType.RANDOM)
        self.add_event(Event.INFRARED_CNTR)
        self._last_dt   = None
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
    @property
    def speed_limit(self):
        return self._speed_limit

    @speed_limit.setter
    def speed_limit(self, speed_limit):
        self._log.info('setting speed_limit to: {:5.2f}'.format(speed_limit))
        self._speed_limit = speed_limit

    # ..........................................................................
    def _convert_to_max_speed(self, distance):
        '''
        Converts a range of distances to a range of speeds. 
        When the distance is greater than or equal to max_distance, returns max_speed.
        When the distance is less than min_distance, returns min_speed.
        Otherwise returns a ratio of distance to speed.
        '''
#       self._min_distance = 20.0 # cm
#       self._max_distance = 200.0 # cm
#       self._min_speed   = 0.0
#       self._max_speed   = 100.0
        _distance_range = self._max_distance - self._min_distance # (180)
        _speed_range    = self._max_speed - self._min_speed # (100)
        _ratio = _speed_range / _distance_range
        if distance >= self._max_distance:
            return self._max_speed
        elif distance < self._min_distance:
            return self._min_speed
        else: # otherwise return a ratio of distance to speed
            # at 200cm return 100.0
            # at 100cm return 50.0
            # at 20cm return 0.0
            # distance range = 200 - 20 (180)
            # speed range = 100 - 0 (100)
            # ratio = 180:100 or 100:180
            return distance * _ratio

    # ..........................................................................
    def enable(self):
        '''
        The necessary state machine call to enable the publisher.
        '''
        Behaviour.enable(self)
#       self._rgbmatrix.enable()

    # ..........................................................................
    def disable(self):
        '''
        The state machine call to disable the publisher.
        '''
#       self._disable_rgbmatrix()
#       super().disable()
        Behaviour.disable(self)

    # ..........................................................................
    async def process_message(self, message):
        '''
        We expect only INFRARED_CNTR messages and extract the distance value.
        '''
        self._log.info('🚧 Roam: process_message {}; '.format(message.name) )
        # TODO only pay attention to messages if roam active and not suppressed 
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected.')
        # indicate that this subscriber has processed the message
        message.process(self)
        _payload = message.payload
        _event   = _payload.event
        if _event is Event.INFRARED_CNTR:
            self.distance = _payload.value
            if self.enabled:
                # TODO get current motor speed
                self.speed_limit = self._convert_to_max_speed(self.distance)
                self._set_motor_speed_limit(Orientation.PORT)
                self._set_motor_speed_limit(Orientation.STBD)
                self._log.info('🈯 processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {};'.format(_event.description) 
                        + Fore.BLUE + ' distance: {:5.2f};'.format(self.distance)
                        + Fore.GREEN + ' max speed: {:5.2f};'.format(self.speed_limit)
                        + Fore.MAGENTA + ' enabled? {}'.format(self.enabled))

            else:
                self.speed_limit = None
                self._log.info('🆎 processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {};'.format(_event.description) 
                        + Fore.BLUE + ' distance: {:5.2f};'.format(self.distance)
                        + Fore.GREEN + ' max speed: NONE;'
                        + Fore.MAGENTA + ' enabled? {}'.format(self.enabled))
        else:
            raise ValueError('expected INFRARED_CNTER event not: {}'.format(message.event.description))

    # ..........................................................................
    def _set_motor_speed_limit(self, orientation):
        '''
        This sets the motor speed limit based on the speed limit, if not None.
        The current speed cannot be less than zero as Roam should limit only
        speed ahead never astern (reversing).
        '''
        if self.speed_limit is None:
            self._log.info('😀 no speed limit.')
            # do nothing
        else:
            self._log.info('😡 setting speed limit for {} motor to: {:5.2f}'.format(orientation.name, self.speed_limit))
            _velocity = self._motors.get_motor_velocity(orientation)
            _target_velocity = self._clip(_velocity, self._min_speed, self.speed_limit)
            self._motors.set_motor_velocity(orientation, _target_velocity)

    # ..........................................................................
    def _clip(self, value, min_value, max_value):
        '''
        A replacement for numpy's clip():

            _value = numpy.clip(target_value, _min, _max)
        '''
        return min_value if value <= min_value else max_value if value >= max_value else value

    # ..........................................................................
#   def _disable_rgbmatrix(self):
#       self._rgbmatrix.set_color(Color.BLACK)
#       time.sleep(0.2)
#       self._rgbmatrix.clear()
#       time.sleep(0.2)
#       self._rgbmatrix.disable()

    # ..........................................................................
    @property
    def event(self):
        return Event.ROAM

#   # ..........................................................................
#   def _roam_callback(self):
#       self._log.info('🌼 roam callback; distance: {}'.format(self.distance))

#   # ..........................................................................
    def start(self):
        '''
        The state machine call to start the roam behaviour. Because this method
        is part of both superclasses we need to only call it once.
        '''
        if self.state is not State.STARTED:
#           super().start()
            Behaviour.start(self)

    # ..........................................................................
    @property
    def name(self):
        return 'roam'

    # ..........................................................................
    def execute(self):
        '''
        The method called upon each loop iteration. 

        :param message:  an optional Message passed along by the message bus
        '''
#       self._log.info('🌼 roam loop execute.')
        _dt_now = dt.now()
        if self._last_dt:
            _elapsed_ms = (_dt_now - self._last_dt).total_seconds() * 1000.0
            self._log.info('🌼 roam loop execute; {};\t'.format(self.get_formatted_time('message age:', _elapsed_ms)) 
                    + Fore.BLUE + ' distance: {};'.format(self.distance)
                    + Fore.GREEN + ' max speed: {};'.format(self.speed_limit))
        self._last_dt = _dt_now

#   # ..........................................................................
#   def suppressed(self):
#   def suppress(self, mode):

#EOF
