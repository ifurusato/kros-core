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
class Swerve(Behaviour):

    _LAMBDA_NAME = 'swerve'

    '''
    Implements a swerving behaviour to avoid objects sensed at a distance,
    swerving away from them.

    The end result of this Behaviour is to provide an offset between the port
    and starboard motors based on the difference in distance values provided
    by the port and starboard (oblique) infrared sensors, i.e., the distance
    to an obstacle in cm. If no obstacle is perceived within the range of
    either sensor, using a configured hysteresis threshold that sets the
    offset to zero to minimise meandering along a target path.

    The Swerve behaviour is by default suppressed.

    NOTES ....................

    This is a Subscriber to INFRARED_PORT and INFRARED_STARBOARD events,
    using the two to create an offset between them used as a steering offset.
    This is implemented by adding a lambda function multiplier into each of
    the Motor's update_target_velocity methods, with the offset altering the
    balance of forward motion to port or starboard proportionate to the offset.

    The external clock is required insofar as this behaviour won't function
    in its absence, as it is used for resetting the motor's maximum
    velocity setting.

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
        Behaviour.__init__(self, 'swerve', config, message_bus, message_factory, suppressed=suppressed, enabled=enabled, level=level)
        if not isinstance(motor_ctrl, MotorController):
            raise ValueError('wrong type for motor_ctrl argument: {}'.format(type(motor_ctrl)))
        self._port_motor   = motor_ctrl.get_motor(Orientation.PORT)
        self._stbd_motor   = motor_ctrl.get_motor(Orientation.STBD)
        self._ext_clock    = external_clock
        if self._ext_clock:
            self._ext_clock.add_slow_callback(self._tick)
            pass
        else:
            raise Exception('unable to enable swerve behaviour: no external clock available.')
        _cfg = config['kros'].get('behaviour').get('swerve')
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
        self._log.info(Style.BRIGHT + 'cruise wait time:    \t{:4.2f} ticks'.format(self._wait_ticks))
        # .................................
        self.add_events([ Event.INFRARED_PORT, Event.INFRARED_STBD ])
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def execute(self, message):
        '''
        The method called by process_message(), upon receipt of a message.
        :param message:  an Message passed along by the message bus
        '''
        if self.suppressed:
            self._log.info(Style.DIM + 'swerve suppressed; message: {}'.format(message.event.label))
        elif self.enabled:
            if message.payload.event is Event.INFRARED_PORT:
                _distance_cm = message.payload.value
                self._log.info('processing port message {}; '.format(message.name)
                        + Fore.PORT  + ' distance: {:5.2f}cm\n'.format(_distance_cm))
#               self._set_max_fwd_velocity_by_distance(_distance_cm)
            elif message.payload.event is Event.INFRARED_STBD:
                _distance_cm = message.payload.value
                self._log.info('processing stbd message {}; '.format(message.name)
                        + Fore.GREEN + ' distance: {:5.2f}cm\n'.format(_distance_cm))
#               self._set_max_fwd_velocity_by_distance(_distance_cm)
            else:
                raise ValueError('expected INFRARED_PORT or INFRARED_STBD event not: {}'.format(message.event.label))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_max_fwd_velocity_by_distance(self, distance_cm):
        '''
        This sets the velocity limit for both motors based on the distance
        argument. The offset provides a differential between the port and 
        starboard motors.
        '''
        print('')
        self._log.info('setting max fwd velocity from distance of {:<5.2f}cm'.format(distance_cm))
        if distance_cm >= self._max_distance: # when distance >+ max_distance, no speed limit
            self._log.info(Fore.YELLOW + 'no speed limit at distance: {:5.2f} > max: {:5.2f}'.format(distance_cm, self._max_distance))
            self._reset_velocity_multiplier('no obstacle seen at {:>5.2f}cm.'.format(distance_cm))
        elif distance_cm < self._min_distance: # when distance < min_distance, set zero lambda
            self._set_velocity_multiplier(Fore.RED + 'too close', self._zero_velocity_ratio(distance_cm))
        else: # otherwise set lambda that returns a ratio of distance to speed as the limit
            self._set_velocity_multiplier(Fore.WHITE + 'within range at {:5.2f}'.format(distance_cm), self._velocity_ratio(distance_cm))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _tick(self):
        '''
        This uses a leaky integrator to set a target forward velocity after
        waiting at least 3 seconds (configurable). The trigger occurs on the
        transition of the wait count from 1 to 0, so that at zero it won't
        continually auto-trigger.
        '''
        if not self.suppressed:
            self._log.info('tick; suppressed: {};\t'.format(self.suppressed))
            self._log.info('swerving;\t'
                    + Fore.RED   + 'port: {:5.2f}cm/s;\t'.format(self._port_motor.velocity)
                    + Fore.GREEN + 'stbd: {:5.2f}cm/s'.format(self._stbd_motor.velocity))
            pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_velocity_multiplier(self, reason, lambda_function):
        self._log.info(Fore.GREEN + 'set max fwd velocity: ' + '{}'.format(reason))
        self._port_motor.add_velocity_multiplier(Swerve._LAMBDA_NAME, lambda_function)
        self._stbd_motor.add_velocity_multiplier(Swerve._LAMBDA_NAME, lambda_function)
        pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _reset_velocity_multiplier(self, reason):
        self._log.info(Fore.MAGENTA + '😨 reset max fwd velocity: ' + Fore.YELLOW + '{}'.format(reason))
        self._port_motor.remove_velocity_multiplier(Swerve._LAMBDA_NAME)
        self._stbd_motor.remove_velocity_multiplier(Swerve._LAMBDA_NAME)
        pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_trigger_behaviour(self, event):
        return TriggerBehaviour.TOGGLE

    @property
    def trigger_event(self):
        '''
        This returns the event used to enable/disable the behaviour manually.
        '''
        return Event.SWERVE

    def release(self):
        '''
        Releases (un-suppresses) this Component.
        '''
        Component.release(self)
        self._log.info(Fore.GREEN + '💚 swerve released.')

    def suppress(self):
        '''
        Suppresses this Component.
        '''
        Component.suppress(self)
        self._reset_velocity_multiplier('suppressing swerve.')
        self._log.info(Fore.BLUE + '💙 swerve suppressed.')

    def disable(self):
        '''
        Disables this Component.
        '''
        Component.disable(self)
        self._reset_velocity_multiplier('disabling swerve.')
        self._log.info(Fore.BLUE + '💙 swerve disabled.')

#EOF
