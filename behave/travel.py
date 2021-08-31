#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-29
# modified: 2021-08-29
#

import sys, time, random
from threading import Thread
#mport multiprocessing
#rom multiprocessing import Process
from colorama import init, Fore, Style
init()

from core.logger import Level, Logger
from core.orient import Orientation
from core.speed import Speed, Direction
from core.component import Component
from hardware.slew import SlewRate
from hardware.velocity import Velocity
from core.rate import Rate

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Travel(Component):
    '''
    This class provides a generic travel manoeuvre for a limited distance, a
    behaviour that goes forward or reverse in a straight line, accelerating
    and decelerating to hit the target distance as close as possible.

    The configuration defines an 'acceleration range', which is the range used
    for both acceleration and deceleration. If the travel distance is greater
    than twice this range we have enough room to reach cruising speed before
    beginning to decelerate to the step target. We also define a targeting speed,
    which is a low velocity from which we are prepared to immediately halt upon
    reaching our step target.

    Geometry Notes ...................................

    494 encoder steps per rotation (maybe 493)
    68.5mm diameter tires
    215.19mm/21.2cm wheel circumference
    1 wheel rotation = 215.2mm
    2295 steps per meter
    2295 steps per second  = 1 m/sec
    2295 steps per second  = 100 cm/sec
    229.5 steps per second = 10 cm/sec
    22.95 steps per second = 1 cm/sec

    1 rotation = 215mm = 494 steps
    1 meter = 4.587 rotations
    2295.6 steps per meter
    22.95 steps per cm
    '''
    def __init__(self, config, motor_configurer, level):
        self._log = Logger("travel", level)
        Component.__init__(self, self._log, suppressed=False, enabled=False)
        if config is None:
            raise ValueError('null configuration argument.')
        _config = config['kros'].get('behaviour').get('travel')
        self._accel_range_cm  = _config.get('accel_range_cm')
        self._log.info('acceleration range: {:5.2f}cm'.format(self._accel_range_cm))
        self._cruising_speed  = Speed.from_string(_config.get('cruising_speed'))
        self._targeting_speed = Speed.from_string(_config.get('targeting_speed'))
        self._log.info('cruising speed: {}; targeting speed: {}'.format(self._cruising_speed.label, self._targeting_speed.label))
        self._port_motor      = motor_configurer.get_motor(Orientation.PORT)
        self._stbd_motor      = motor_configurer.get_motor(Orientation.STBD)
        self._port_complete   = False
        self._stbd_complete   = False
        self._port_proc       = None
        self._stbd_proc       = None
#       _cpu_count = multiprocessing.cpu_count()
#       self._log.info('number of CPUs available: {:d}'.format(_cpu_count))
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        if self.closed:
            self._log.warning('cannot enable loop: already closed.')
        elif self.enabled:
            self._log.warning('travel already enabled.')
        else:
            Component.enable(self)
            self._log.info('travel enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def travel(self, direction, distance_cm):
        if self.closed:
            self._log.warning('cannot enable loop: already closed.')
        elif not self.enabled:
            self._log.warning('travel not enabled.')
        else:
            self._log.info(Fore.YELLOW + 'call to travel distance: {:d}'.format(distance_cm))
            self._port_complete = False
            self._stbd_complete = False

            _begin_port_steps = self._port_motor.steps
            _begin_stbd_steps = self._stbd_motor.steps

            # store slew rate
            self._port_slew = self._port_motor.slew_limiter.slew_rate
            self._stbd_slew = self._stbd_motor.slew_limiter.slew_rate
            # set fast slew rate
            self._port_motor.slew_limiter.slew_rate = SlewRate.EXTREMELY_FAST
            self._stbd_motor.slew_limiter.slew_rate = SlewRate.EXTREMELY_FAST
#           self._port_motor.slew_limiter.slew_rate = SlewRate.VERY_FAST
#           self._stbd_motor.slew_limiter.slew_rate = SlewRate.VERY_FAST
      
            try:

                _use_threads = True # False DOES NOT WORK
                if _use_threads:
                    self._port_proc = Thread(name='travel-port', target=self._travel, args=(direction, distance_cm, self._port_motor, self._travel_callback_port), daemon=True)
                    self._stbd_proc = Thread(name='travel-stbd', target=self._travel, args=(direction, distance_cm, self._stbd_motor, self._travel_callback_stbd), daemon=True)
                else:
                    raise Exception('unsupported operation.')
#                   self._port_proc = Process(name='travel-port', target=self._travel, args=(direction, distance_cm, self._port_motor, self._travel_callback_port))
#                   self._stbd_proc = Process(name='travel-stbd', target=self._travel, args=(direction, distance_cm, self._stbd_motor, self._travel_callback_stbd))
    
                self._port_proc.start()
                self._stbd_proc.start()
    
                # .......................................     
                _count = 0
                while _count < 7 \
                        and ( self._port_proc.is_alive() or not self._port_complete ) \
                        and ( self._stbd_proc.is_alive() or not self._stbd_complete ):
                    self._log.info(Fore.RED   + '💓 [{:d}] port travel thread waiting...  alive? {}; complete: {}'.format(_count, self._port_proc.is_alive(), self._port_complete))
                    self._log.info(Fore.GREEN + '💓 [{:d}] stbd travel thread waiting...  alive? {}; complete: {}'.format(_count, self._stbd_proc.is_alive(), self._stbd_complete))
                    _count += 1
                    time.sleep(1.0)
                # .......................................     
    
                self._log.info(Fore.RED   + '💓 port travel thread ending...  alive? {}; complete: {}'.format(self._port_proc.is_alive(), self._port_complete))
                self._log.info(Fore.GREEN + '💓 stbd travel thread ending...  alive? {}; complete: {}'.format(self._stbd_proc.is_alive(), self._stbd_complete))
    
                _end_port_steps = self._port_motor.steps
                _end_stbd_steps = self._stbd_motor.steps
    
                self._log.info('👥 joining processes...')
                self._port_proc.join()
                self._stbd_proc.join()

            except Exception as e:
                self._log.error('error traveling: {}'.format(e))
            finally:
                # restore
                self._port_motor.slew_limiter.slew_rate = self._port_slew
                self._stbd_motor.slew_limiter.slew_rate = self._stbd_slew
      
            _delta_port_steps = _end_port_steps - _begin_port_steps 
            _delta_stbd_steps = _end_stbd_steps - _begin_stbd_steps
            self._log.info('👥 travel complete; port: {:d} steps; stbd: {:d} steps.'.format(_delta_port_steps, _delta_stbd_steps))

            return [_delta_port_steps, _delta_stbd_steps]

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _compare(self, value1, value2, direction):
        if direction is Direction.AHEAD:
            return value1 < value2
        elif direction is Direction.ASTERN:
            return value1 > value2

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _travel(self, direction, distance_cm, motor, callback):
        self._log.info(Fore.YELLOW + 'travel direction: {}; distance: {:d}'.format(direction.label, distance_cm))

        _distance_cm = distance_cm
        _current_steps = motor.steps # get this quickly

        _multiplier = 1 if direction is Direction.AHEAD else -1
#       motor.slew_limiter.slew_rate = SlewRate.SLOWER

        _velocity = motor.get_velocity()
        # _velocity.steps_for_distance_cm
#       _distance_cm = 10.0 # should be 1m
        _target_step_count = _multiplier * ( _distance_cm * _velocity.steps_per_cm )
        _target_steps = round(_current_steps + _target_step_count)
        _closing_target_steps = _target_steps - _velocity.steps_per_rotation

        # last wheel rotation
        _final_target_step_count = _target_steps - ( 1 * _velocity.steps_per_rotation )

        _proposed_accel_range_cm = _distance_cm / 4.0
        if _proposed_accel_range_cm * 2.0 >= self._accel_range_cm: # is the proposed range greater than the standard range?
            # then we use standard acceleration/deceleration
            self._log.info('using standard accel/decel range (compressed: {:5.2f}cm; standard: {:5.2f}cm)'.format(_proposed_accel_range_cm, self._accel_range_cm))
            _accel_range_cm = self._accel_range_cm
        else: # otherwise compress to just one fourth of distance
            self._log.info('using compressed accel/decel range (compressed: {:5.2f}cm; standard: {:5.2f}cm)'.format(_proposed_accel_range_cm, self._accel_range_cm))
            _accel_range_cm = _proposed_accel_range_cm

        _accel_range_steps = round(_accel_range_cm * _velocity.steps_per_cm)
        self._log.info('using accel/decel range of {:5.2f}cm, or {:d} steps.'.format(_accel_range_cm, _accel_range_steps))

        _accel_target_steps = _current_steps + _accel_range_steps # accelerate til this step count
        _decel_target_steps = _target_steps  - _accel_range_steps # step count when we begin to decelerate

        self._log.info(Fore.WHITE
                + 'begin travel for {} motor accelerating from {:d} to {:d} steps, then cruise until {:d} steps, when we decelerate to {:d} steps and halt.'.format(
                        motor.orientation.label, _current_steps, _accel_target_steps, _decel_target_steps, _target_steps))

        # begin traveling ............................................................

        _rate = Rate(20)

        # accelerate to cruising velocity ............................................
        motor.target_velocity = _multiplier * float(self._cruising_speed.velocity)
        self._log.info(Fore.BLUE + '1. {} motor accelerating to velocity: {}...'.format(motor.orientation.label, motor.target_velocity))
#       self._log.info(Fore.MAGENTA + '1a. {} while {} < {}...'.format(motor.orientation.label, motor.steps, _accel_target_steps))
        while self._compare(motor.steps, _accel_target_steps, direction):
#           self._log.debug(Fore.BLUE + '{} motor accelerating from {} to {}...'.format(motor.orientation.label, motor.steps, _accel_target_steps))
            _rate.wait()

        # cruise until 3/4 of range ..................................................
        self._log.info(Fore.BLUE + '2. {} motor reached cruising velocity...'.format(motor.orientation.label))
        motor.target_velocity = _multiplier * float(self._cruising_speed.velocity)
#       self._log.debug(Fore.MAGENTA + '2a. {} while {} < {}...'.format(motor.orientation.label, motor.steps, _decel_target_steps))
        while self._compare(motor.steps, _decel_target_steps, direction):
            _rate.wait()

        # slow down until we reach 9/10 of range
        self._log.info(Fore.BLUE + '3. slowing {} motor until within range...'.format(motor.orientation.label))
        motor.target_velocity = _multiplier * ( self._cruising_speed.velocity + self._targeting_speed.velocity ) / 2.0
#       self._log.info(Fore.MAGENTA + '3a. {} while {} < {}...'.format(motor.orientation.label, motor.steps, _decel_target_steps))
        while self._compare(motor.steps, _decel_target_steps, direction): 
            _rate.wait()

        self._log.info(Fore.BLUE + '4. {} motor reached 9/10 of target, decelerating to targeting velocity...'.format(motor.orientation.label))
        motor.slew_limiter.reset()
        # decelerate to targeting velocity when we get to one wheel revo of target ...
        motor.target_velocity = _multiplier * float(self._targeting_speed.velocity)
        while self._compare(motor.steps, _closing_target_steps, direction):
            _rate.wait()

        self._log.info(Fore.BLUE + '5. {} motor slowing to a stop...'.format(motor.orientation.label))
        motor.target_velocity = _multiplier * float(self._targeting_speed.velocity)
        while self._compare(motor.steps, _target_steps, direction):
#           self._log.info(Fore.BLUE + Style.DIM + '{:d} steps...'.format(motor.steps))
            _rate.wait()
        motor.target_velocity = 0.0
        self._log.info(Fore.BLUE + '6. {} motor stopping...'.format(motor.orientation.label))

#       time.sleep(1.0)
        motor.slew_limiter.reset()

        self._log.info(Fore.BLUE + 'executing {} callback...'.format(motor.orientation.label))
        callback()

        self._log.info(Fore.BLUE + 'travel on {} motor complete: {:d} of {:d} steps.'.format(motor.orientation.label, motor.steps, _target_steps))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        Component.disable(self)
        self._log.info(Fore.MAGENTA + 'disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_cruising_velocity(self):
        return self._cruising_speed

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _travel_callback_port(self):
        self._log.info(Fore.RED + '🥝 port travel complete.')
        self._port_complete = True

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _travel_callback_stbd(self):
        self._log.info(Fore.GREEN + '🥝 stbd travel complete.')
        self._stbd_complete = True

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def is_traveling(self):
        return not self._port_complete and not self._stbd_complete

#EOF
