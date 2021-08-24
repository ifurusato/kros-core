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
    velocity limit is reset to the motor's default maximum speed.

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

    There are effectively two distance filters at play: the center infrared
    sensor doesn't generate messages beyond a certain distance; and there is
    also a filter within this class that ignores messages whose distance value
    exceeds the threshold of the roam behaviour.

    The external clock is required insofar as the Roam behaviour won't
    function in its absence, as it is used for resetting the motor's maximum
    velocity setting.

    An option is to set the maximum distance to roam, so that the robot
    accelerates to roaming speed, varies its speed as described above,
    then as it nears its target distance, decelerates to a halt at the
    target.

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
        self._ratio         = ( self._max_velocity - self._min_velocity ) / ( self._max_distance - self._min_distance )
        self._log.info(Style.BRIGHT + 'speed/distance ratio:\t{:4.2f} ({:.0%})'.format(self._ratio, self._ratio))
        self._cruising_speed = Speed.from_string(_cfg.get('cruising_speed'))
        self._cruising_velocity = float(self._cruising_speed.velocity)
        self._log.info(Style.BRIGHT + 'cruising speed:      \t{} ({:5.2f}cm/sec)'.format(self._cruising_speed.label, self._cruising_speed.velocity))
        self._last_dist_cm  = 0.0
        self._wait_ticks    = _cfg.get('cruise_wait_ticks') # assumes slow tick at 1Hz
        self._log.info(Style.BRIGHT + 'cruise wait time:    \t{:4.2f} ticks'.format(self._wait_ticks))
        self._wait_count    = self._wait_ticks
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
        them to be different. Because the values are stored on each motor
        separately we just use the PORT motor to obtain the value.
        '''
        print('')
        self._log.info('🌰 setting max fwd velocity from distance of {:<5.2f}cm'.format(distance_cm))

#       _cruise_ok = self._last_dist_cm > distance_cm
        self._last_dist_cm = distance_cm
#       if self._cruise_ok: # then it's further than it was before, so reset

        # are both moters moving forward?
#       if self._port_motor.velocity > 0.0 and self._stbd_motor.velocity > 0.0:
        self._wait_count = self._wait_ticks

        if distance_cm >= self._max_distance: 
            self._log.info(Fore.YELLOW + '📶 no speed limit at distance: {:5.2f} > max: {:5.2f}'.format(distance_cm, self._max_distance))
            # when distance >+ max_distance, no speed limit. E.g., at 200cm return 100.0
            self._reset_maximum_forward_velocity('no obstacle seen at {:>5.2f}cm.'.format(distance_cm))
            return
        elif distance_cm < self._min_distance: 
            self._log.info(Fore.RED + '🚻 TOO CLOSE: stopping.')
            # When the distance < min_distance, returns min_velocity. E.g., at 20cm return 0.0
            _roam_max_velocity = self._min_velocity
        else:
            # otherwise use a ratio of distance to speed as the limit. E.g., at 100cm return 50.0
            # distance range = 200 - 20 (180), speed range = 100 - 0 (100)
            # so the ratio = 100:180 or 5:9 or 55%
            _roam_max_velocity = distance_cm * self._ratio
            self._log.info(Fore.GREEN + '💹 set speed limit to: {:5.2f} using ratio {:5.2f}'.format(_roam_max_velocity, self._ratio))

        # sanity czech
        _roam_max_velocity = Util.clip(_roam_max_velocity, self._min_velocity, self._max_velocity)

        # get the maximum forward velocity of both motors. This should be the same for both.
        if self._port_motor.max_fwd_velocity != self._stbd_motor.max_fwd_velocity:
            raise Exception('expected max fwd velocities to be equal.') # TEMP
        _motors_max_fwd_velocity = max(self._port_motor.max_fwd_velocity, self._stbd_motor.max_fwd_velocity)

        # Compare max velocity limit of motors with roam_max_velocity generated by distance argument
        # If roam_max_velocity < current max velocity of motor, set the motor's limit.
        # e.g., if roam limit is 30 and current max velocity is 50, then set max_fwd_velocity to roam limit
        if _roam_max_velocity < _motors_max_fwd_velocity:
            self._port_motor.max_fwd_velocity = _roam_max_velocity
            self._stbd_motor.max_fwd_velocity = _roam_max_velocity
            self._log.info('🍏 SET roam max velocity: {:5.2f}; motor max fwd: {:5.2f}'.format(_roam_max_velocity, _motors_max_fwd_velocity))
        else:
            self._log.info('🍎 DID NOT SET roam max velocity: {:5.2f}; motor max fwd: {:5.2f}'.format(_roam_max_velocity, _motors_max_fwd_velocity))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _tick(self):
        '''
        This uses a leaky integrator to set a target forward velocity after
        waiting at least 3 seconds (configurable). The trigger occurs on the
        transition of the wait count from 1 to 0, so that at zero it won't
        continually auto-trigger.
        '''
        if not self.suppressed:
            self._log.info('🕓 tick;\twait count: {:d}; suppressed: {};\t'.format(
                    self._wait_count, self.suppressed) + Fore.YELLOW + 'last distance: {:>5.2f}cm'.format(self._last_dist_cm))
            # wait ten counts before trying to move
            if self._wait_count == 0:
                self._log.info('🐰 stable.')
            elif self._wait_count == 1:
                self._log.info(' cruise triggered.')
                self._log.info('🐰 cruise triggered at: {} ({:5.2f}cm/sec)'.format(self._cruising_speed.name, self._cruising_velocity))
                self._wait_count = 0
                # we change state in the transition from wait count 1 to 0 (0 being a steady state)
#               if self._last_dist_cm > self._min_distance:
                self._reset_maximum_forward_velocity('recovered from encounter.')
                self._port_motor.target_velocity = self._cruising_velocity
                self._stbd_motor.target_velocity = self._cruising_velocity
            else:
                self._log.info('🐰 counting down from {:d}...'.format(self._wait_count))
                self._wait_count -= 1
                pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _reset_maximum_forward_velocity(self, reason):
        self._log.info(Fore.MAGENTA + '♒ reset max fwd velocity: ' + Fore.YELLOW + '{}'.format(reason))
        self._port_motor.reset_max_fwd_velocity()
        self._stbd_motor.reset_max_fwd_velocity()
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
