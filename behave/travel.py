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
import multiprocessing
from multiprocessing import Process
from colorama import init, Fore, Style
init()

from core.logger import Level, Logger
from core.orient import Orientation
from core.speed import Speed
from core.component import Component
from hardware.slew import SlewRate
from hardware.velocity import Velocity
from core.rate import Rate

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Travel(Component):
    '''
        This class provides a generic travel manoeuvre for a limited distance, a
        behaviour that goes forward or reverse in a straight line, accelerating
        and decelerating to hit the target distance exactly.

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
        _cpu_count = multiprocessing.cpu_count()
        self._log.info('number of CPUs available: {:d}'.format(_cpu_count))
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        if self.closed:
            self._log.warning('cannot enable loop: already closed.')
        else:
            if self.enabled:
                self._log.warning('loop already enabled.')
            else:
                Component.enable(self)
                self._log.info('start traveling...')
                self._port_complete = False
                self._stbd_complete = False

                _use_threads = True

                if _use_threads:
                    self._port_proc = Thread(name='travel-port', target=self._travel, args=(self._port_motor, self._travel_callback_port))
                    self._stbd_proc = Thread(name='travel-stbd', target=self._travel, args=(self._stbd_motor, self._travel_callback_stbd))
                else:
                    self._port_proc = Process(name='travel-port', target=self._travel, args=(self._port_motor, self._travel_callback_port))
                    self._stbd_proc = Process(name='travel-stbd', target=self._travel, args=(self._stbd_motor, self._travel_callback_stbd))

                self._port_proc.start()
                self._stbd_proc.start()

                self._log.info('👥 joining port process...')
                self._port_proc.join()

                self._log.info('👥 joining stbd process...')
                self._stbd_proc.join()

                self._log.info('👥 travel complete.')

                # .......................................     
                _count = 0
                while _count < 7 and ( self._port_proc.is_alive() or not self._port_complete ):
                    self._log.info(Fore.RED   + '🥝 [{:d}] port travel thread waiting...  alive? {}; complete: {}'.format(_count, self._port_proc.is_alive(), self._port_complete))
                    _count += 1
                    time.sleep(1.0)
                self._log.info(Fore.RED   + '🥝 port travel thread alive? {}'.format(self._port_proc.is_alive()))


                self._log.info('travel complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _travel(self, motor, callback):

        _current_steps = motor.steps # get this quickly


#       motor.slew_limiter.slew_rate = SlewRate.SLOWER

        _velocity = motor.get_velocity()
        # _velocity.steps_for_distance_cm
        _distance_cm = 10.0 # should be 1m
        _target_step_count = _distance_cm * _velocity.steps_per_cm
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

        _accel_target_steps = _current_steps + _accel_range_steps  # accelerate til this step count
        _decel_target_steps = _target_steps  - _accel_range_steps  # step count when we begin to decelerate

        self._log.info(Fore.WHITE
                + 'begin travel for {} motor accelerating from {:d} to {:d} steps, then cruise until {:d} steps, when we decelerate to {:d} steps and halt.'.format(
                        motor.orientation.label, _current_steps, _accel_target_steps, _decel_target_steps, _target_steps))


        # begin traveling ............................................................

        _rate = Rate(20)

        # accelerate to cruising velocity ............................................
        self._log.info(Fore.BLUE + '{} motor accelerating to velocity: {}...'.format(motor.orientation.label, float(self._cruising_speed.velocity)) )
        motor.target_velocity = float(self._cruising_speed.velocity)
        while motor.steps < _accel_target_steps:
            self._log.info(Fore.BLUE + '{} motor accelerating from {} to {}...'.format(motor.orientation.label, motor.steps, _accel_target_steps))
            _rate.wait()

        # cruise until 3/4 of range ..................................................
        self._log.info(Fore.BLUE + '{} motor reached cruising velocity...'.format(motor.orientation.label))
        motor.target_velocity = float(self._cruising_speed.velocity)
        while motor.steps < _decel_target_steps: # .....................................
            _rate.wait()

        # slow down until we reach 9/10 of range
        motor.target_velocity = ( self._cruising_speed.velocity + self._targeting_speed.velocity ) / 2.0
        while motor.steps < _decel_target_steps: # .....................................
            _rate.wait()

        self._log.info(Fore.BLUE + '{} motor reached 9/10 of target, decelerating to targeting velocity...'.format(motor.orientation.label))
        motor.slew_limiter.reset()
        # decelerate to targeting velocity when we get to one wheel revo of target ...
        motor.target_velocity = float(self._targeting_speed.velocity)
        while motor.steps < _closing_target_steps: # ...................................
            _rate.wait()

        motor.target_velocity = float(self._targeting_speed.velocity)
        while motor.steps < _target_steps: # ...........................................
#           self._log.info(Fore.BLUE + Style.DIM + '{:d} steps...'.format(motor.steps))
            _rate.wait()
        motor.target_velocity = 0.0
        self._log.info(Fore.BLUE + '{} motor stopping...'.format(motor.orientation.label))

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
