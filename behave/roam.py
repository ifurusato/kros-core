#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-07-08
#

import itertools
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.event import Event
from core.speed import Speed
from core.util import Util
from core.orient import Orientation
from behave.behaviour import Behaviour
from behave.trigger_behaviour import TriggerBehaviour
from hardware.motor_controller import MotorController

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Roam(Behaviour):
    '''
    Implements a roaming behaviour. The end result of this Behaviour is to
    provide a forward speed limit for both motors based on a distance value
    provided by the center infrared sensor, i.e., the distance to an obstacle
    in cm. If no obstacle is perceived within the range of the sensor, the 
    velocity limit is removed.

    Because we only know how far the obstacle is based on incoming events,
    if we haven't seen an event in awhile we may assume there is nothing
    there and start moving again, at "cruising" speed. But we need to wait
    a bit after reacting to an obstacle before attempting to start moving 
    again.

    The Roam behaviour is by default suppressed.

    NOTES ....................

    This is a Subscriber to INFRARED_CNTR events, altering the usage of the
    center analog IR sensor to no longer function solely for obstacle
    avoidance, but instead set the robot's target velocity as a proportion to
    the perceived distance. I.e., if the sensor sees nothing at its maximum
    range the robot's forward target velocity will be set to its maximum. As
    the sensed distance is lessened the target velocity is likewise, until the
    robot reaches a minimum distance in which it halts and then goes into an
    obstacle avoidance behaviour (handled elsewhere).

    This means that we will in the future need to suppress whatever is the
    normal avoidance behaviour for the center IR sensor when this is active,
    at least up to the minimum roam distance.

    The external clock is required insofar as the Roam behaviour won't
    function in its absence, as it is used for resetting the motor's maximum
    velocity setting.

    This is implemented by adding a lambda function multiplier into the
    Motor's update_target_velocity method. When absent there is no effect;
    when closer than the minimum range a lambda that returns zero is set;
    otherwise a lambda that converts the observed distance (cm) to a ratio
    is used.

    :param config:           the application configuration
    :param message_bus:      the asynchronous message bus
    :param message_factory:  the factory for messages
    :param motor_ctrl:       the motor controller
    :param exernal_clock:    the external clock
    :param suppressed:       suppressed state, default True
    :param enabled:          enabled state, default True
    :param level:            the optional log level
    '''
    def __init__(self, config, message_bus, message_factory, motor_ctrl, external_clock, suppressed=True, enabled=True, level=Level.INFO):
        Behaviour.__init__(self, 'roam', config, message_bus, message_factory, suppressed=suppressed, enabled=enabled, level=level)
        if not isinstance(motor_ctrl, MotorController):
            raise ValueError('wrong type for motor_ctrl argument: {}'.format(type(motor_ctrl)))
        self._port_motor   = motor_ctrl.get_motor(Orientation.PORT)
        self._stbd_motor   = motor_ctrl.get_motor(Orientation.STBD)
        self._ext_clock    = external_clock
        if self._ext_clock:
            self._ext_clock.add_slow_callback(self._tick)
            pass
        else:
            raise Exception('unable to enable roam behaviour: no external clock available.')
        self._counter       = itertools.count()
        _cfg = config['kros'].get('behaviour').get('roam')
        self._modulo        = 5 # at 20Hz, every 20 ticks is 1 second, every 5 ticks 250ms
        self._min_distance  = _cfg.get('min_distance')
        self._max_distance  = _cfg.get('max_distance')
        self._log.info(Style.BRIGHT + 'configured distance:\t{:4.2f} to {:4.2f}cm'.format(self._min_distance, self._max_distance))
        self._min_velocity  = _cfg.get('min_velocity')
        self._max_velocity  = _cfg.get('max_velocity')
        _velocity_km_hr = 36.0 * ( self._max_velocity / 1000 )
        self._log.info(Style.BRIGHT + 'configured speed:    \t{:4.2f} to {:4.2f}cm/sec ({:3.1f}km/hr)'.format(
                self._min_velocity, self._max_velocity, _velocity_km_hr))
        # zero lambda always returns a zero value
        self._zero_velocity_ratio = lambda n: self._min_velocity
        # lambda accepts distance and returns a ratio to multiply against velocity
        self._velocity_ratio = lambda n: ( ( n - self._min_distance ) / ( self._max_distance - self._min_distance ) )
        _ratio               = ( self._max_velocity - self._min_velocity ) / ( self._max_distance - self._min_distance )
        self._log.info(Style.BRIGHT + 'ratio calculation:\t{:4.2f} = ({:4.2f} - {:4.2f}) / ({:4.2f} - {:4.2f})'.format(
                _ratio, self._max_velocity, self._min_velocity, self._max_distance, self._min_distance))
        self._log.info(Style.BRIGHT + 'speed/distance ratio:\t{:4.2f} ({:.0%})'.format(_ratio, _ratio))
        self._cruising_speed = Speed.from_string(_cfg.get('cruising_speed'))
        self._cruising_velocity = float(self._cruising_speed.velocity)
        self._log.info(Style.BRIGHT + 'cruising speed:      \t{} ({:5.2f}cm/sec)'.format(self._cruising_speed.label, self._cruising_speed.velocity))
        self._wait_ticks    = _cfg.get('cruise_wait_ticks') # assumes slow tick at 1Hz
        self._wait_count    = self._wait_ticks
        self._log.info(Style.BRIGHT + 'cruise wait time:    \t{:4.2f} ticks'.format(self._wait_ticks))
        # .................................
        self.add_event(Event.INFRARED_CNTR)
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def execute(self, message):
        '''
        The method called by process_message(), upon receipt of a message.
        :param message:  an Message passed along by the message bus
        '''
        if self.suppressed:
            self._log.info(Style.DIM + 'roam suppressed; message: {}'.format(message.event.label))
        elif self.enabled:
            if message.payload.event is Event.INFRARED_CNTR:
                _distance_cm = message.payload.value
                # TODO filter on distance here
#               self._log.info('processing message {}; '.format(message.name)
#                       + Fore.GREEN + ' distance: {:5.2f}cm\n'.format(_distance_cm))
                self._set_max_fwd_velocity_by_distance(_distance_cm)
            else:
                raise ValueError('expected INFRARED_CNTER event not: {}'.format(message.event.label))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_max_fwd_velocity_by_distance(self, distance_cm):
        '''
        This sets the velocity limit for both motors based on the distance
        argument. Both motors share the same limit, as there's no reason for
        them to be different.
        '''
        print('')
        self._log.info('setting max fwd velocity from distance of {:<5.2f}cm'.format(distance_cm))
        if distance_cm >= self._max_distance: # when distance >+ max_distance, no speed limit
            self._log.info(Fore.YELLOW + 'no speed limit at distance: {:5.2f} > max: {:5.2f}'.format(distance_cm, self._max_distance))
            self._reset_velocity_multiplier('no obstacle seen at {:>5.2f}cm.'.format(distance_cm))
        elif distance_cm < self._min_distance: # when distance < min_distance, set zero lambda
            self._set_velocity_multiplier(Fore.RED + 'too close', self._zero_velocity_ratio(distance_cm))
            self._wait_count = self._wait_ticks # reset wait
        else: # otherwise set lambda that returns a ratio of distance to speed as the limit
            self._set_velocity_multiplier(Fore.WHITE + 'within range at {:5.2f}'.format(distance_cm), self._velocity_ratio(distance_cm))
            self._wait_count = self._wait_ticks # reset wait

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _tick(self):
        '''
        This uses a leaky integrator to set a target forward velocity after
        waiting at least 3 seconds (configurable). The trigger occurs on the
        transition of the wait count from 1 to 0, so that at zero it won't
        continually auto-trigger.
        '''
        if not self.suppressed:
            self._log.info('tick;\twait count: {:d}; suppressed: {};\t'.format( self._wait_count, self.suppressed))
            # wait ten counts before trying to move
            if self._wait_count == 0:
                self._log.info('stable.')
            elif self._wait_count == 1:
                self._log.info(' cruise triggered.')
                self._log.info('cruise triggered at: {} ({:5.2f}cm/sec)'.format(self._cruising_speed.name, self._cruising_velocity))
                self._wait_count = 0
                # we change state in the transition from wait count 1 to 0 (0 being a steady state)
                self._reset_velocity_multiplier('recovered from encounter.')
                self._port_motor.target_velocity = self._cruising_velocity
                self._stbd_motor.target_velocity = self._cruising_velocity
            else:
                self._log.info('counting down from {:d}...'.format(self._wait_count))
                self._wait_count -= 1
                pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_velocity_multiplier(self, reason, lambda_function):

#       if not isinstance(message_bus, lambda):

        self._log.info(Fore.GREEN + 'set max fwd velocity: ' + '{}'.format(reason))
        self._port_motor.set_velocity_multiplier(lambda_function)
        self._stbd_motor.set_velocity_multiplier(lambda_function)
        pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _reset_velocity_multiplier(self, reason):
        self._log.info(Fore.MAGENTA + 'reset max fwd velocity: ' + Fore.YELLOW + '{}'.format(reason))
        self._port_motor.reset_velocity_multiplier()
        self._stbd_motor.reset_velocity_multiplier()
        pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_trigger_behaviour(self, event):
        return TriggerBehaviour.TOGGLE

    @property
    def trigger_event(self):
        '''
        This returns the event used to enable/disable the behaviour manually.
        '''
        return Event.ROAM

    def release(self):
        '''
        Releases (un-suppresses) this Component.
        '''
        Component.release(self)
        self._log.info(Fore.GREEN + '💚 roam released.')

    def suppress(self):
        '''
        Suppresses this Component.
        '''
        Component.suppress(self)
        self._log.info(Fore.BLUE + '💙 roam suppressed.')

#EOF
