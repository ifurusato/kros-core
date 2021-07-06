#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-16
# modified: 2021-06-26
#

from threading import Thread
import asyncio, itertools, random, time
from math import isclose
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.orient import Orientation, Speed, Direction
from core.event import Event
from core.slew import SlewLimiter

from mock.motor import Motor

# ..............................................................................
class Motors(Component):
    '''
    A mocked dual motor controller with encoders. 

    This incorporates an increment value for halting and braking by 
    altering the set velocity of the motors, but also relies upon a 
    SlewLimiter installed on each of the motors, so that velocity 
    changes occur gradually.

    :param name:         the subscriber name (for logging)
    :param tb:           the ThunderBorg motor controller
    :param events:       the list of events used as a filter, None to set as cleanup task
    :param level:        the logging level
    '''
    def __init__(self, config, tb, level=Level.INFO):
        self._log = Logger('motors', level)
        Component.__init__(self, self._log, suppressed=False, enabled=False)
        self._log.info('initialising motors...')
        if config is None:
            raise Exception('no config argument provided.')
        self._config = config
        if tb is None:
            raise Exception('no tb argument provided.')
        _tb = tb
        self._port_motor = Motor(self._config, _tb, Orientation.PORT, level)
        self._stbd_motor = Motor(self._config, _tb, Orientation.STBD, level)
        self._port_slew_limiter = SlewLimiter(self._config, Orientation.PORT, level)
        self._stbd_slew_limiter = SlewLimiter(self._config, Orientation.STBD, level)
        # temporary until we move functionality to motors
        self._color                = Fore.MAGENTA
        self._loop_thread          = None
        self._loop_enabled         = False
        self._event_counter        = itertools.count()
        # constants
        self._loop_delay_sec       = 0.5
        self._max_velocity         = 100
        self._accel_increment      = 5.0 # normal incremental acceleration 
        self._decel_increment      = 5.0 # normal incremental deceleration
        self._halt_ratio           = 0.4 # ratio used for quick _halt behaviour
        self._brake_ratio          = 0.7 # ratio used for slower braking behaviour
        self._spin_speed           = Speed.HALF # target velocity of spin
        # variables
        self._port_target_velocity = 0.0 # the port motor target velocity for slewing
        self._stbd_target_velocity = 0.0 # the starboard motor target velocity for slewing
        self._decelerate_ratio     = 0.0 # variable used in loop
        self._log.info('motors ready.')

    # ..........................................................................
    @property
    def name(self):
        return 'motors'

    # ..........................................................................
    def start_loop(self):
        '''
        Start the loop.
        '''
        if not self.enabled:
            self._log.warning('not enabled.')
            raise Exception('not enabled.')
        if self._loop_thread is None:
            self._loop_enabled = True
            self._loop_thread = Thread(name='display_loop', target=Motors._loop, args=[self, lambda: self._loop_enabled], daemon=True)
            self._loop_thread.start()
            self._log.info('loop enabled.')
        else:
            self._log.warning('cannot enable loop: thread already exists.')

    # ..........................................................................
    def stop_loop(self):
        '''
        Stop the loop.
        '''
        if self._loop_enabled:
            self._loop_enabled = False
            self._loop_thread  = None
            self._log.info('loop disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def loop_is_running(self):
        return self._loop_enabled

    # ..........................................................................
    def _loop(self, f_is_enabled):
        '''
        The motors loop, which executes while the flag argument lambda is True.

        self._port_target_velocity :  the port motor target velocity (for slewing)
        self._stbd_target_velocity :  the starboard motor target velocity (for slewing)
        self._port_motor.velocity  :  the value sent to the port PID controller
        self._stbd_motor.velocity  :  the value sent to the starboard PID controller
        '''
        while f_is_enabled():
            _event_count = next(self._event_counter)
            _current_port_velocity = self._port_motor.velocity
            _current_stbd_velocity = self._stbd_motor.velocity
            if not isclose(self._decelerate_ratio, 0.0, abs_tol=0.1):
                # if decelerating then apply that to target velocities first
                self._decelerate(_event_count)
            if self._port_motor.velocity != self._port_target_velocity:
                self.set_motor_velocity(Orientation.PORT, self._port_target_velocity)
            if self._stbd_motor.velocity != self._stbd_target_velocity:
                self.set_motor_velocity(Orientation.STBD, self._stbd_target_velocity)
            # print stats...
            if self.stopped:
#               self._log.info('[{:04d}] velocity: '.format(_event_count) + Fore.BLUE + 'stopped.')
                self._log.info('[{:04d}] velocity: '.format(_event_count) 
                        + Fore.RED   + 'port: {:5.2f} / {:<5.2f}'.format(_current_port_velocity, self._port_target_velocity)
                        + Fore.CYAN  + '\t:: '
                        + Fore.GREEN + 'stbd: {:5.2f} / {:<5.2f}'.format(_current_stbd_velocity, self._stbd_target_velocity) + Fore.CYAN + '\t:: stopped.')
            else:
                if self._decelerate_ratio == 0.0:
                    self._log.info('[{:04d}] velocity: '.format(_event_count) 
                            + Fore.RED   + 'port: {:5.2f} / {:<5.2f}'.format(_current_port_velocity, self._port_target_velocity)
                            + Fore.CYAN  + '\t:: '
                            + Fore.GREEN + 'stbd: {:5.2f} / {:<5.2f}'.format(_current_stbd_velocity, self._stbd_target_velocity))
                else:
                    self._log.info('[{:04d}] velocity: '.format(_event_count) 
                            + Fore.RED   + 'port: {:5.2f} / {:<5.2f}'.format(_current_port_velocity, self._port_target_velocity)
                            + Fore.CYAN  + '\t:: '
                            + Fore.GREEN + 'stbd: {:5.2f} / {:<5.2f}'.format(_current_stbd_velocity, self._stbd_target_velocity)
                            + Fore.CYAN  + '\t:: decelerate: '
                            + Fore.BLUE + '{:.0%}'.format(self._decelerate_ratio))
            time.sleep(self._loop_delay_sec)
        self._log.info('exited display loop.')

    # ..........................................................................
    def get_motor(self, orientation):
        if orientation is Orientation.PORT:
            return self._port_motor
        else:
            return self._stbd_motor

    # ..........................................................................
    def dispatch_velocity_event(self, payload):
        self._reset_deceleration()
        _event = payload.event
        _value = payload.value
        if not self.loop_is_running():
            self.start_loop()
        if _event is Event.INCREASE_PORT_VELOCITY:
            self._increment_motor_velocity(Orientation.PORT, self._accel_increment)
            self._log.info(self._color + Style.BRIGHT + 'increase PORT velocity; velocity: {:5.2f}'.format(self._port_motor.velocity))
            pass
        elif _event is Event.DECREASE_PORT_VELOCITY:
            self._increment_motor_velocity(Orientation.PORT, -1 * self._decel_increment)
            self._log.info(self._color + Style.BRIGHT + 'decrease PORT velocity; velocity: {:5.2f}'.format(self._port_motor.velocity))
            pass
        elif _event is Event.INCREASE_STBD_VELOCITY:
            self._increment_motor_velocity(Orientation.STBD, self._accel_increment)
            self._log.info(self._color + Style.BRIGHT + 'increase STBD velocity; velocity: {:5.2f}'.format(self._stbd_motor.velocity))
            pass
        elif _event is Event.DECREASE_STBD_VELOCITY:
            self._increment_motor_velocity(Orientation.STBD, -1 * self._decel_increment)
            self._log.info(self._color + Style.BRIGHT + 'decrease STBD velocity; velocity: {:5.2f}'.format(self._stbd_motor.velocity))
            pass
        elif _event is Event.INCREASE_VELOCITY:
            self._increment_motor_velocity(Orientation.PORT, self._accel_increment)
            self._increment_motor_velocity(Orientation.STBD, self._accel_increment)
            self._log.info(self._color + Style.BRIGHT + 'increase velocity;\t'
                    + Fore.RED + 'port: {:5.2f};\t'.format(self._port_motor.velocity)
                    + Fore.GREEN + 'stbd: {:5.2f}'.format(self._stbd_motor.velocity))
        elif _event is Event.DECREASE_VELOCITY:
            self._increment_motor_velocity(Orientation.PORT, -1 * self._decel_increment)
            self._increment_motor_velocity(Orientation.STBD, -1 * self._decel_increment)
            self._log.info(self._color + Style.BRIGHT + 'decrease velocity;\t'
                    + Fore.RED + 'port: {:5.2f};\t'.format(self._port_motor.velocity)
                    + Fore.GREEN + 'stbd: {:5.2f}'.format(self._stbd_motor.velocity))
        else:
            raise ValueError('unrecognised velocity event {}'.format(_event.description))

    # ..........................................................................
    def dispatch_chadburn_event(self, payload):
        '''
        A dispatcher for chadburn events: full, half, slow and dead slow
        for both ahead and astern.
        '''
        self._reset_deceleration()
        _event = payload.event
        _value = payload.value
        _speed = None
        _direction = None
        if _event is Event.STOP:
            _speed = Speed.STOP
            self._log.info(self._color + 'STOP.')
        elif _event is Event.FULL_ASTERN:
            _direction = Direction.ASTERN
            _speed = Speed.FULL
            self._log.info(self._color + 'FULL ASTERN.')
        elif _event is Event.HALF_ASTERN:
            _direction = Direction.ASTERN
            _speed = Speed.HALF
            self._log.info(self._color + 'HALF ASTERN.')
        elif _event is Event.SLOW_ASTERN:
            _direction = Direction.ASTERN
            _speed = Speed.SLOW
            self._log.info(self._color + 'SLOW ASTERN.')
        elif _event is Event.DEAD_SLOW_ASTERN:
            _direction = Direction.ASTERN
            _speed = Speed.DEAD_SLOW
            self._log.info(self._color + 'DEAD SLOW ASTERN.')
        elif _event is Event.DEAD_SLOW_AHEAD:
            _direction = Direction.AHEAD
            _speed = Speed.DEAD_SLOW
            self._log.info(self._color + 'DEAD SLOW AHEAD.')
        elif _event is Event.SLOW_AHEAD:
            _direction = Direction.AHEAD
            _speed = Speed.SLOW
            self._log.info(self._color + 'SLOW AHEAD.')
        elif _event is Event.HALF_AHEAD:
            _direction = Direction.AHEAD
            _speed = Speed.HALF
            self._log.info(self._color + 'HALF AHEAD.')
        elif _event is Event.FULL_AHEAD:
            _direction = Direction.AHEAD
            _speed = Speed.FULL
            self._log.info(self._color + 'FULL AHEAD.')
        else:
            raise ValueError('unrecognised chadburn event {}'.format(_event.description))
        if _speed is not Speed.STOP and not self.loop_is_running():
            self.start_loop()
        # ........
        self._log.debug('set chadburn velocity: {}  {}.'.format(_speed.label, _direction))
        _value = _speed.value if _direction is Direction.AHEAD else -1 * _speed.value
        self.set_motor_velocity(Orientation.PORT, _value)
        self.set_motor_velocity(Orientation.STBD, _value)

    # ..........................................................................
    def dispatch_theta_event(self, payload):
        '''
        A dispatcher for theta (rotation/turning) events: turn ahead, turn to, 
        and turn astern for port and starboard; spin port and spin starboard.
        '''
        self._reset_deceleration()
        _event = payload.event
        _value = payload.value
        self._log.info('theta event: {}'.format(_event.description))
        if not self.loop_is_running():
            self.start_loop()
        # ........
        if _event is Event.THETA:
            pass
        elif _event is Event.PORT_THETA:
            pass
        elif _event is Event.STBD_THETA:
            pass
        elif _event is Event.EVEN:
            self._even()
        elif _event is Event.INCREASE_PORT_THETA:
            pass
        elif _event is Event.DECREASE_PORT_THETA:
            pass
        elif _event is Event.INCREASE_STBD_THETA:
            pass
        elif _event is Event.DECREASE_STBD_THETA:
            pass
        elif _event is Event.TURN_AHEAD_PORT:
            pass
        elif _event is Event.TURN_TO_PORT:
            self._log.info('theta TURN_TO_PORT event.')
            pass
        elif _event is Event.TURN_ASTERN_PORT:
            pass
        elif _event is Event.SPIN_PORT:
            self._spin(Orientation.PORT)
        elif _event is Event.SPIN_STBD:
            self._spin(Orientation.STBD)
        elif _event is Event.TURN_ASTERN_STBD:
            pass
        elif _event is Event.TURN_TO_STBD:
            self._log.info('theta TURN_TO_STBD event.')
            pass
        elif _event is Event.TURN_AHEAD_STBD:
            pass
        else:
            raise ValueError('unrecognised theta event {}'.format(_event.description))

    # ..........................................................................
    def dispatch_stop_event(self, payload):
        '''
        A dispatcher for deceleration events: halt, _brake and stop.
        '''
        self._reset_deceleration()
        _event = payload.event
        _value = payload.value
        if _event is Event.HALT:
            self._halt()
        elif _event is Event.BRAKE: 
            self._brake()
        elif _event is Event.STOP:
            self._stop()
        else:
            raise ValueError('unrecognised stop event {}'.format(_event.description))

    # ..........................................................................
    def dispatch_infrared_event(self, payload):
        '''
        A dispatcher for infrared events from port side, port, center, starboard, or starboard side.
        '''
        _event = payload.event
        _value = payload.value

        if _event is Event.INFRARED_PORT_SIDE:
            self._log.info('INFRARED PORT SIDE.')
#           self._stop()
        elif _event is Event.INFRARED_PORT:
            self._log.info('INFRARED PORT.')
#           self._stop()
        elif _event is Event.INFRARED_CNTR: 
            self._log.info('INFRARED CNTR.')
#           self._stop()
        elif _event is Event.INFRARED_STBD:
            self._log.info('INFRARED STBD.')
#           self._stop()
        elif _event is Event.INFRARED_STBD_SIDE:
            self._log.info('INFRARED STBD SIDE.')
#           self._stop()
        else:
            raise ValueError('unrecognised bumper event {}'.format(_event.description))

    # ..........................................................................
    def dispatch_bumper_event(self, payload):
        '''
        A dispatcher for bumper events from port, center or starboard.
        '''
        _event = payload.event
        _value = payload.value
        if _event is Event.BUMPER_PORT:
            self._log.info('BUMPER PORT.')
            self._stop()
        elif _event is Event.BUMPER_CNTR: 
            self._log.info('BUMPER CNTR.')
            self._stop()
        elif _event is Event.BUMPER_STBD:
            self._log.info('BUMPER STBD.')
            self._stop()
        else:
            raise ValueError('unrecognised bumper event {}'.format(_event.description))

    # ..........................................................................
    def _spin(self, orientation):
        '''
        Spin to either port (counter-clockwise) or starboard (clockwise) by
        setting the target velocity of each motor to opposite directions.
        '''
        self._log.info('theta SPIN {}.'.format(orientation.name))
        self._reset_deceleration()
        if orientation is Orientation.PORT:
            _port_velocity = -1.0 * self._spin_speed.value
            _stbd_velocity = self._spin_speed.value
        elif orientation is Orientation.STBD:
            _port_velocity = self._spin_speed.value
            _stbd_velocity = -1.0 * self._spin_speed.value
        else:
            raise Exception('unrecognised spin direction: {}'.format(orientation))
        self.set_motor_velocity(Orientation.PORT, _port_velocity)
        self.set_motor_velocity(Orientation.STBD, _stbd_velocity)

    # ..........................................................................
    def _even(self):
        '''
        Set the target velocity of both motors to the average of their target 
        velocities. If they are both currently equal this exits gracefully.
        '''
        if self._port_target_velocity == self._stbd_target_velocity:
            self._log.info('target velocities of both motors already equal.')
        else:
            _average_velocity = ( self._port_target_velocity + self._stbd_target_velocity ) / 2.0
            self._log.info('even velocity from: ' + Fore.RED + 'port: {:5.2f}; '.format(self._port_target_velocity) 
                    + Fore.GREEN + 'stbd: {:5.2f}; '.format(self._stbd_target_velocity)
                    + Fore.YELLOW + 'average: {:5.2f}.'.format(_average_velocity))
            self.set_motor_velocity(Orientation.PORT, _average_velocity)
            self.set_motor_velocity(Orientation.STBD, _average_velocity)

    # ..........................................................................
    def _increment_motor_velocity(self, orientation, increment):
        '''
        Increment the target velocity of the specified motor by the supplied increment
        (which can be a positive or negative value).
        '''
        if orientation is Orientation.PORT:
            _updated_target_velocity = self._update_value(self._port_target_velocity, increment)
            self._log.info('increment port motor velocity:' + Fore.RED + ' {:5.2f} + {:5.2f} ➔ {:<5.2f}'.format(\
                    self._port_motor.velocity, increment, _updated_target_velocity))
        else:
            _updated_target_velocity = self._update_value(self._stbd_target_velocity, increment)
            self._log.info('increment stbd motor velocity:' + Fore.GREEN + ' {:5.2f} + {:5.2f} ➔ {:<5.2f}'.format(\
                    self._stbd_motor.velocity, increment, _updated_target_velocity))
        self.set_motor_velocity(orientation, _updated_target_velocity)

    # ..........................................................................
    def _update_value(self, value, increment):
        # FIXME this overshoots the value
        value += increment
        if value > self._max_velocity:
            value = self._max_velocity
        elif value < -1.0 * self._max_velocity:
            value = -1.0 * self._max_velocity
        return value

    # ..........................................................................
    def get_motor_velocity(self, orientation):
        '''
        Return the target velocity of the specified motor.
        '''
        if orientation is Orientation.PORT:
            return self._port_motor.velocity
        else:
            return self._stbd_motor.velocity

    def set_motor_velocity(self, orientation, target_velocity):
        '''
        Set the target velocity of the specified motor.
        '''
        if orientation is Orientation.PORT:
            _current_port_velocity = self._port_motor.velocity
            self._port_target_velocity = target_velocity
            self._port_motor.velocity = self._port_slew_limiter.slew(_current_port_velocity, self._port_target_velocity)
            self._log.debug('set port motor velocity: {:5.2f} ➔ {:<5.2f}'.format(_current_port_velocity, self._port_target_velocity))
        else:
            _current_stbd_velocity = self._stbd_motor.velocity
            self._stbd_target_velocity = target_velocity
            self._stbd_motor.velocity = self._stbd_slew_limiter.slew(_current_stbd_velocity, self._stbd_target_velocity)
            self._log.debug('set stbd motor velocity: {:5.2f} ➔ {:<5.2f}'.format(_current_stbd_velocity, target_velocity))

    # ..........................................................................
    def _halt(self):
        '''
        Quickly (but not immediately) stops both motors.
        '''
        if not self.stopped:
            if self._loop_enabled:
                self._log.info('halting with ratio: {:5.2f}...'.format(self._decelerate_ratio))
                self._decelerate_ratio = self._halt_ratio
            else:
                self._log.info('stopping immediately: no increment loop running.')
                self._port_motor.stop()
                self._stbd_motor.stop()
            self._log.info('halted.')
        else:
            self._log.debug('already halted.')
        return True

    # ..........................................................................
    def _brake(self):
        '''
        Slowly coasts both motors to a stop.
        '''
        if not self.stopped:
            if self.loop_is_running():
                self._log.info('braking with ratio: {:5.2f}...'.format(self._decelerate_ratio))
                self._decelerate_ratio = self._brake_ratio
            else:
                self._log.info('stopping immediately: no increment loop running.')
                self._port_motor.stop()
                self._stbd_motor.stop()
            self._log.info('braked.')
        else:
            self._log.warning('already braked.')
        return True

    # ..........................................................................
    def _decelerate(self, count):
        '''
        Applies the value to incrementally slow the motor target velocity
        to zero, using either a slow (_brake) or fast (_halt) deceleration. Both
        halting and braking perform the same function, varying only by how
        quickly the change (acceleration) occurs.

        TODO
        The function should increment as a percentage of the motor target velocity
        so that if the robot is moving in an arc the braking will roughly follow
        that arc rather than having the slower motor come to a stop first,
        avoiding a final spiral inwards.
        '''
#       self._log.info(Fore.BLACK + 'decelerate() port: {:5.2f}; stbd: {:5.2f}'.format(self._port_target_velocity, self._stbd_target_velocity))
        if isclose(self._port_target_velocity, 0.0, abs_tol=0.5) and isclose(self._stbd_target_velocity, 0.0, abs_tol=0.5):
            # stopping...
            self._reset_deceleration()
            self._stop()
            self.stop_loop() # not necessarily...
            self._log.info(Fore.YELLOW + 'deceleration complete.')
        else:
            # still decelerating...
            if isclose(self._port_target_velocity, 0.0, abs_tol=1.0):
                self._port_target_velocity = 0.0
            else:
                self._port_target_velocity = self._port_target_velocity * self._decelerate_ratio
            if isclose(self._stbd_target_velocity, 0.0, abs_tol=1.0):
                self._stbd_target_velocity = 0.0
            else:
                self._stbd_target_velocity = self._stbd_target_velocity * self._decelerate_ratio
        # print stats...
        if self._log.is_at_least(Level.WARN):
            self._log.info(Style.DIM + '[{:04d}] velocity:'.format(count) 
                    + Fore.RED   + ' port: {:5.2f} ➔ {:<5.2f}'.format(self._port_motor.velocity, self._port_target_velocity)
                    + Fore.CYAN  + '\t:: '
                    + Fore.GREEN + 'stbd: {:5.2f} ➔ {:<5.2f}'.format(self._stbd_motor.velocity, self._stbd_target_velocity)
                    + Fore.CYAN  + '\t:: decelerate: '
                    + Fore.BLUE + '{:.0%}'.format(self._decelerate_ratio))

    # ..........................................................................
    def _reset_deceleration(self):
        '''
        Halts any automated deceleration.
        '''
        self._decelerate_ratio = 0.0

    # ..........................................................................
    def _stop(self):
        '''
        Stops both motors immediately, with no slewing.
        '''
        self._log.info('stopping...')
        if not self.stopped:
            self._port_target_velocity = 0.0
            self._stbd_target_velocity = 0.0
            self._port_motor.velocity  = 0.0
            self._stbd_motor.velocity  = 0.0
#           self._port_motor.stop()
#           self._stbd_motor.stop()
            self._log.info('stopped.')
        else:
            self._log.warning('already stopped.')
        return True

    # ..........................................................................
    @property
    def stopped(self):
        return self._port_motor.velocity == 0 and self._stbd_motor.velocity == 0
#       return self._port_motor.stopped and self._stbd_motor.stopped

    # ..........................................................................
    def is_in_motion(self):
        '''
        Returns true if either motor is moving.
        '''
        return self._port_motor.is_in_motion() or self._stbd_motor.is_in_motion()

    # ..........................................................................
    def enable(self):
        '''
        Enables the motors. This issues a warning if already enabled, but no
        harm is done in calling it repeatedly.
        '''
        if self.enabled:
            self._log.warning('already enabled.')
        if not self._port_motor.enabled:
            self._port_motor.enable()
        self._port_slew_limiter.enable()
        if not self._stbd_motor.enabled:
            self._stbd_motor.enable()
        self._stbd_slew_limiter.enable()
        super().enable()
        self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        '''
        Disable the motors, halting first if in motion.
        '''
        if self.enabled:
            self._log.info('disabling...')
            super().disable()
            if self.is_in_motion(): # if we're moving then halt
                self._log.warning('event: motors are in motion (halting).')
                self._halt()
            self._port_slew_limiter.disable()
            self._port_motor.disable()
            self._stbd_slew_limiter.disable()
            self._stbd_motor.disable()
            self._log.info('disabling pigpio...')
            self._log.info('disabled.')
        else:
            self._log.debug('already disabled.')

    # ..........................................................................
    def close(self):
        '''
        Halts, turn everything off and stop doing anything.
        '''
        if not self.closed:
            super().close()
            self._port_motor.close()
            self._stbd_motor.close()

    # ..........................................................................
    @staticmethod
    def cancel():
        self._log.info('cancelling motors...')
#       Motor.cancel()

#EOF
