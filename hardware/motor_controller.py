#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-16
# modified: 2021-07-22
#

from threading import Thread
import asyncio, itertools, random, time, traceback
from math import isclose
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.orient import Orientation
from core.speed import Speed, Direction
from core.event import Event
from core.message_bus import MessageBus
from hardware.motor_configurer import MotorConfigurer
from hardware.motor import Motor

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MotorController(Component):
    '''
    A motor controller that asbtracts the actual control of two motors.

    This relies upon both a SlewLimiter and JerkLimiter so that velocity
    and power (resp.) changes occur gradually and safely. It also contains
    the motor thread loop, which is used to create various acceleration,
    deceleration, and other behaviours.

    There are three modes of stopping:

      Stop:  set the target velocity of the motors to zero immediately.
      Halt:  slew the target velocity of the motors to zero quickly.
      Brake: slew the target velocity of the motors to zero slowly.

    :param confif:       the application configuration
    :param message_bus:  the application MessageBus
    :param motor_config: the MotorConfigurator object
    :param level:        the logging level
    '''
    def __init__(self, config, message_bus, motor_configurer, level=Level.INFO):
        self._log = Logger('motor-ctrl', level)
        Component.__init__(self, self._log, suppressed=False, enabled=False)
        self._log.info('initialising motors...')
        if not isinstance(config, dict):
            raise ValueError('wrong type for config argument: {}'.format(type(name)))
        self._config = config
        if not isinstance(message_bus, MessageBus):
            raise ValueError('wrong type for message bus argument: {}'.format(type(message_bus)))
        self._message_bus = message_bus
        if not isinstance(motor_configurer, MotorConfigurer):
            raise ValueError('wrong type for motor configurer argument: {}'.format(type(motor_configurer)))
        self._port_motor = motor_configurer.get_motor(Orientation.PORT)
        self._stbd_motor = motor_configurer.get_motor(Orientation.STBD)

        # temporary until we move functionality to motors
        self._color                = Fore.MAGENTA
        self._loop_thread          = None
        self._loop_enabled         = False
        self._event_counter        = itertools.count()
        # configured constants
        _cfg = config['kros'].get('motor').get('motor_controller')
        self._loop_delay_sec       = _cfg.get('loop_delay_sec')    # main loop delay
        self._log.info('loop delay:\t{:5.2f}s'.format(self._loop_delay_sec))
        self._accel_increment      = _cfg.get('accel_increment')   # normal incremental acceleration
        self._decel_increment      = _cfg.get('decel_increment')   # normal incremental deceleration
        self._log.info('accelerate increment: {:5.2f}; decelerate increment: {:5.2f}'.format(self._accel_increment, self._decel_increment))
        self._halt_ratio           = _cfg.get('halt_ratio')        # ratio for quick _halt behaviour
        self._log.info('halt ratio:\t{:<5.2f}'.format(self._halt_ratio))
        self._brake_ratio          = _cfg.get('brake_ratio')       # ratio for slower braking behaviour
        self._log.info('brake ratio:\t{:<5.2f}'.format(self._brake_ratio))
        self._spin_speed           = Speed.from_string(_cfg.get('spin_speed')) # motor speed when spinning
        self._log.info('spin speed:\t{}'.format(self._spin_speed.name))
#       self._use_pid_controller   = _cfg.get('use_pid_controller') # when True use PID control, otherwise direct drive
#       if self._use_pid_controller:
#           self._log.info('using PID controller.')
#       else:
#           self._log.info('using direct motor control.')
        # variables
        self._decelerate_ratio     = 0.0 # variable used in loop
        # lambdas
        self._log.info('motors ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'motor-ctrl'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def start_loop(self):
        '''
        Start the loop.
        '''
        self._log.info('start motor control loop...           🎈🎈🎈🎈🎈🎈🎈🎈  ')
        if not self.enabled:
            self._log.warning('not enabled.')
            raise Exception('not enabled.')
        if self._loop_thread is None:
            self._loop_enabled = True
            self._loop_thread = Thread(name='display_loop', target=MotorController._loop, args=[self, lambda: self._loop_enabled], daemon=True)
            self._loop_thread.start()
            self._log.info('loop enabled.')
        else:
            raise Exception('cannot enable loop: thread already exists.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _loop(self, f_is_enabled):
        '''
        The motors loop, which executes while the flag argument lambda is True.
        '''
        self._log.info('🌳 loop start: {}'.format(self._decelerate_ratio))
        try:
            while f_is_enabled():
                _event_count = next(self._event_counter)
                if not isclose(self._decelerate_ratio, 0.0, abs_tol=0.1):
                    # if decelerating then apply that to target velocities first
                    self.decelerate(_event_count)
                    pass
                self._port_motor.update_target_velocity()
                self._stbd_motor.update_target_velocity()
                # TODO add execute any callbacks here

                # print stats...
                self.print_info(_event_count)
                time.sleep(self._loop_delay_sec)
        except Exception as e:
            self._log.error('error in loop: {}\n{}'.format(e, traceback.format_exc()))
        self._log.info('exited display loop.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
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

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def loop_is_running(self):
        return self._loop_enabled and self._loop_thread != None and self._loop_thread.is_alive()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_info(self, count):
        if self.stopped:
            self._log.info(('[{:04d}] '.format(count) if count else '')
                    + 'velocity: '
                    + Fore.RED   + 'port: {:<5.2f} -> {:<5.2f} / {:<5.2f}'.format(
                            self._port_motor.velocity, self._port_motor.target_velocity, self._port_motor.current_power)
                    + Fore.CYAN  + ' :: '
                    + Fore.GREEN + 'stbd: {:<5.2f} -> {:<5.2f} / {:<5.2f}'.format(
                            self._stbd_motor.velocity, self._stbd_motor.target_velocity, self._stbd_motor.current_power)
                    + Fore.CYAN + ' :: movement: {}'.format(self._characterise_movement()))
        else:
            if self._decelerate_ratio == 0.0:
                self._log.info(('[{:04d}] '.format(count) if count else '')
                        + 'velocity: '
                        + Fore.RED   + 'port: {:<5.2f} -> {:<5.2f} / {:<5.2f}'.format(
                                self._port_motor.velocity, self._port_motor.target_velocity, self._port_motor.current_power)
                        + Fore.CYAN  + ' :: '
                        + Fore.GREEN + 'stbd: {:<5.2f} -> {:<5.2f} / {:<5.2f}'.format(
                                self._stbd_motor.velocity, self._stbd_motor.target_velocity, self._stbd_motor.current_power)
                        + Fore.CYAN + ' :: movement: {}'.format(self._characterise_movement()))
            else:
                self._log.info(('[{:04d}] '.format(count) if count else '')
                        + 'velocity: '
                        + Fore.RED   + 'port: {:<5.2f} -> {:<5.2f} / {:<5.2f}'.format(
                                self._port_motor.velocity, self._port_motor.target_velocity, self._port_motor.current_power)
                        + ' {:5.2f}'.format(self._port_motor.current_power)
                        + Fore.CYAN  + ' :: '
                        + Fore.GREEN + 'stbd: {:<5.2f} -> {:<5.2f} / {:<5.2f}'.format(
                                self._stbd_motor.velocity, self._stbd_motor.target_velocity, self._stbd_motor.current_power)
                        + Fore.CYAN  + ' :: decelerate: ' + Fore.BLUE + '{:.0%}'.format(self._decelerate_ratio)
                        + Fore.CYAN + ' :: movement: {}'.format(self._characterise_movement()))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_motor_status(self):
        self._log.info('motors:')

        # port ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

        self._log.info(Fore.RED + '\t{}'.format('port') \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len('port')))))
                + Fore.YELLOW + '{}\t'.format(self._port_motor.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._port_motor.suppressed))

        self._log.info(Fore.RED + '\t{}'.format('slew') \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len('port')))))
                + Fore.YELLOW + '{}\t'.format(self._port_motor.slew_limiter.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._port_motor.slew_limiter.suppressed))

        self._log.info(Fore.RED + '\t{}'.format('pid') \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len('port')))))
                + Fore.YELLOW + '{}\t'.format(self._port_motor.pid_controller.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._port_motor.pid_controller.suppressed))

        self._log.info(Fore.RED + '\t{}'.format('jerk') \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len('port')))))
                + Fore.YELLOW + '{}\t'.format(self._port_motor.jerk_limiter.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._port_motor.jerk_limiter.suppressed))

        # starboard ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

        self._log.info(Fore.GREEN + '\t{}'.format('stbd') \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len('stbd')))))
                + Fore.YELLOW + '{}\t'.format(self._stbd_motor.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._stbd_motor.suppressed))

        self._log.info(Fore.GREEN + '\t{}'.format('slew') \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len('stbd')))))
                + Fore.YELLOW + '{}\t'.format(self._stbd_motor.slew_limiter.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._stbd_motor.slew_limiter.suppressed))

        self._log.info(Fore.GREEN + '\t{}'.format('pid') \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len('stbd')))))
                + Fore.YELLOW + '{}\t'.format(self._stbd_motor.pid_controller.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._stbd_motor.pid_controller.suppressed))

        self._log.info(Fore.GREEN + '\t{}'.format('jerk') \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len('stbd')))))
                + Fore.YELLOW + '{}\t'.format(self._stbd_motor.jerk_limiter.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._stbd_motor.jerk_limiter.suppressed))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _characterise_movement(self):
        '''
        Return a pair of strings in a list, characterising the current and
        target movement based on the direction of the two motors.
        '''
        _before = self._get_movement_description(self._port_motor.velocity, self._stbd_motor.velocity)
        _after  = self._get_movement_description(self._port_motor.target_velocity, self._stbd_motor.target_velocity)
        if _before == _after:
            return _before
        else:
            return '{} -> → {}'.format(_before, _after)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_movement_description(self, port_velocity, stbd_velocity):
        _avg_velocity = ( port_velocity + stbd_velocity ) / 2.0

        if isclose(port_velocity, 0.0, abs_tol=0.5) and isclose(stbd_velocity, 0.0, abs_tol=0.5):
            # close to stopped
            return 'stopped'
        elif isclose(port_velocity, stbd_velocity, abs_tol=0.5):
            if port_velocity > 0.0:
                return 'straight ahead'
            else:
                return 'straight astern'
        elif isclose(_avg_velocity, 0.0, abs_tol=0.5):
            if port_velocity > stbd_velocity:
                return 'rotate to starboard'
            elif port_velocity < stbd_velocity:
                return 'rotate to port'
            else:
                return 'indeterminate (0)'
        elif _avg_velocity > 0.0:
            if port_velocity > stbd_velocity:
                return 'turn ahead to starboard'
            elif port_velocity < stbd_velocity:
                return 'turn ahead to port'
            else:
                return 'ahead indeterminate (1)'
        elif _avg_velocity < 0.0:
            if port_velocity > stbd_velocity:
                return 'turn astern to starboard'
            elif port_velocity < stbd_velocity:
                return 'turn astern to port'
            else:
                return 'astern indeterminate (2)'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_motor_velocity(self, orientation, target_velocity):
        '''
        A convenience method that sets the target velocity and motor
        power of the specified motor.
        '''
#       self._log.info(Fore.GREEN + Style.NORMAL + 'set velocity: {:5.2f} of {} motor.'.format(target_velocity, orientation.name))
        if not isinstance(target_velocity, float):
            raise ValueError('expected float, not {}'.format(type(target_velocity)))
        if orientation is Orientation.PORT:
            self._port_motor.target_velocity = target_velocity
        else:
            self._stbd_motor.target_velocity = target_velocity

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def dispatch_velocity_event(self, payload):
        self.reset_deceleration()
        _event = payload.event
        self._log.info('dispatch velocity event: {}'.format(_event.label))
        _value = payload.value
        if not self.loop_is_running():
            self.start_loop()
        if _event is Event.VELOCITY:
            self._log.info(self._color + Style.BRIGHT + 'set velocity;\t'
                    + Fore.RED + 'port: {:5.2f} / {:5.2f};\t'.format(_value, self._port_motor.velocity)
                    + Fore.GREEN + 'stbd: {:5.2f} / {:5.2f}'.format(_value, self._stbd_motor.velocity))
            self.set_motor_velocity(Orientation.PORT, _value)
            self.set_motor_velocity(Orientation.STBD, _value)
        elif _event is Event.INCREASE_PORT_VELOCITY:
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
            raise ValueError('unrecognised velocity event {}'.format(_event.label))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def dispatch_chadburn_event(self, payload):
        '''
        A dispatcher for chadburn events: full, half, slow and dead slow
        for both ahead and astern.
        '''
        self.reset_deceleration()
        _event = payload.event
        self._log.info('dispatch chadburn event: {}'.format(_event.label))
        _value = payload.value
        _speed = _event.speed
        _direction = _event.direction
        if _speed is not Speed.STOP and not self.loop_is_running():
            self.start_loop()
        # ........
        self._log.debug('set chadburn velocity: {}  {}.'.format(_speed.label, _direction))
        _value = _speed.ahead if _direction is Direction.AHEAD else _speed.astern
        self.set_motor_velocity(Orientation.PORT, _value)
        self.set_motor_velocity(Orientation.STBD, _value)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def dispatch_theta_event(self, payload):
        '''
        A dispatcher for theta (rotation/turning) events: turn ahead, turn to,
        and turn astern for port and starboard; spin port and spin starboard.
        '''
        self.reset_deceleration()
        _event = payload.event
        self._log.info('dispatch theta event: {}'.format(_event.label))
        _value = payload.value
        self._log.info('theta event: {}'.format(_event.label))
        if not self.loop_is_running():
            self.start_loop()
        # ........
        if _event is Event.THETA:
            pass
        elif _event is Event.EVEN:
            self._even()
        # port .............................................
        elif _event is Event.PORT_THETA:
            pass
        elif _event is Event.INCREASE_PORT_THETA:
            pass
        elif _event is Event.DECREASE_PORT_THETA:
            pass
        elif _event is Event.TURN_AHEAD_PORT:
            self._log.info('theta TURN_AHEAD_PORT event.')
            self.set_motor_velocity(Orientation.PORT, Speed.HALF.value)
            self.set_motor_velocity(Orientation.STBD, Speed.FULL.value)
            pass
        elif _event is Event.TURN_ASTERN_PORT:
            self._log.info('theta TURN_ASTERN_PORT event.')
            self.set_motor_velocity(Orientation.PORT, -1 * Speed.HALF.value)
            self.set_motor_velocity(Orientation.STBD, -1 * Speed.FULL.value)
            pass
        elif _event is Event.TURN_TO_PORT:
            self._log.info('theta TURN_TO_PORT event (unimplemented).')
            pass
        elif _event is Event.SPIN_PORT:
            self._log.info('SPIN_PORT event.')
            self._spin(Orientation.PORT)
        # stbd .............................................
        elif _event is Event.STBD_THETA:
            pass
        elif _event is Event.INCREASE_STBD_THETA:
            pass
        elif _event is Event.DECREASE_STBD_THETA:
            pass
        elif _event is Event.TURN_AHEAD_STBD:
            self._log.info('theta TURN_AHEAD_STBD event.')
            self.set_motor_velocity(Orientation.PORT, Speed.FULL.value)
            self.set_motor_velocity(Orientation.STBD, Speed.HALF.value)
            pass
        elif _event is Event.TURN_ASTERN_STBD:
            self._log.info('theta TURN_ASTERN_STBD event.')
            self.set_motor_velocity(Orientation.PORT, -1 * Speed.FULL.value)
            self.set_motor_velocity(Orientation.STBD, -1 * Speed.HALF.value)
            pass
        elif _event is Event.TURN_TO_STBD:
            self._log.info('theta TURN_TO_STBD event (unimplemented).')
            pass
        elif _event is Event.SPIN_STBD:
            self._log.info('SPIN_STBD event.')
            self._spin(Orientation.STBD)
        else:
            raise ValueError('unrecognised theta event {}'.format(_event.label))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def dispatch_stop_event(self, payload):
        '''
        A dispatcher for deceleration events: halt, _brake and stop.
        '''
        self.reset_deceleration()
        _event = payload.event
        self._log.info('dispatch stop event: {}'.format(_event.label))
        _value = payload.value
        if _event is Event.HALT:
            self.halt()
        elif _event is Event.BRAKE:
            self.brake()
        elif _event is Event.STOP:
            self.stop()
        else:
            raise ValueError('unrecognised stop event {}'.format(_event.label))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def dispatch_infrared_event(self, payload):
        '''
        A dispatcher for infrared events from port side, port, center, starboard, or starboard side.
        '''
        _event = payload.event
        _value = payload.value
        self._log.info('dispatch infrared event: {}'.format(_event.label))
        if _event is Event.INFRARED_PORT_SIDE:
            self._log.info('INFRARED PORT SIDE.')
#           self._brake()
        elif _event is Event.INFRARED_PORT:
            self._log.info('INFRARED PORT.')
#           self._brake()
        elif _event is Event.INFRARED_CNTR:
            self._log.info('INFRARED CNTR.')
#           self._brake()
        elif _event is Event.INFRARED_STBD:
            self._log.info('INFRARED STBD.')
#           self._brake()
        elif _event is Event.INFRARED_STBD_SIDE:
            self._log.info('INFRARED STBD SIDE.')
#           self._brake()
        else:
            raise ValueError('unrecognised bumper event {}'.format(_event.label))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def dispatch_bumper_event(self, payload):
        '''
        A dispatcher for bumper events from port, center or starboard.

        This causes the robot to halt.
        '''
        _event = payload.event
        _value = payload.value
        if _event is Event.BUMPER_PORT:
            self._log.info('BUMPER PORT.')
            self.halt()
        elif _event is Event.BUMPER_CNTR:
            self._log.info('BUMPER CNTR.')
            self.halt()
        elif _event is Event.BUMPER_STBD:
            self._log.info('BUMPER STBD.')
            self.halt()
        else:
            raise ValueError('unrecognised bumper event {}'.format(_event.label))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _spin(self, orientation):
        '''
        Spin to either port (counter-clockwise) or starboard (clockwise) by
        setting the target velocity of each motor to opposite directions.
        '''
        self._log.info('theta SPIN {}.'.format(orientation.name))
        self.reset_deceleration()
        if orientation is Orientation.PORT:
            _port_velocity = self._spin_speed.astern
            _stbd_velocity = self._spin_speed.ahead
        elif orientation is Orientation.STBD:
            _port_velocity = self._spin_speed.ahead
            _stbd_velocity = self._spin_speed.astern
        else:
            raise Exception('unrecognised spin direction: {}'.format(orientation))
        self.set_motor_velocity(Orientation.PORT, _port_velocity)
        self.set_motor_velocity(Orientation.STBD, _stbd_velocity)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _even(self):
        '''
        Set the target velocity of both motors to the average of their target
        velocities. If they are both currently equal this exits gracefully.
        '''
        if self._port_motor.target_velocity == self._stbd_motor.target_velocity:
            self._log.info('target velocities of both motors already equal.')
        else:
            _average_velocity = ( self._port_motor.target_velocity + self._stbd_motor.target_velocity ) / 2.0
            self._log.info('even velocity from: ' + Fore.RED + 'port: {:5.2f}; '.format(self._port_motor.target_velocity)
                    + Fore.GREEN + 'stbd: {:5.2f}; '.format(self._stbd_motor.target_velocity)
                    + Fore.YELLOW + 'average: {:5.2f}.'.format(_average_velocity))
            self.set_motor_velocity(Orientation.PORT, _average_velocity)
            self.set_motor_velocity(Orientation.STBD, _average_velocity)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _increment_motor_velocity(self, orientation, increment):
        '''
        Increment the target velocity of the specified motor by the supplied increment
        (which can be a positive or negative value). No clipping is done here, so it's
        possible to set a value higher than the motor will accept.
        '''
        if orientation is Orientation.PORT:
            _updated_target_velocity = self._port_motor.target_velocity + increment
            self._log.info('increment port motor velocity:' + Fore.RED + ' {:5.2f} + {:5.2f} ➔ {:<5.2f}'.format(\
                    self._port_motor.velocity, increment, _updated_target_velocity))
        else:
            _updated_target_velocity = self._stbd_motor.target_velocity + increment
            self._log.info('increment stbd motor velocity:' + Fore.GREEN + ' {:5.2f} + {:5.2f} ➔ {:<5.2f}'.format(\
                    self._stbd_motor.velocity, increment, _updated_target_velocity))
        self.set_motor_velocity(orientation, _updated_target_velocity)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def halt(self):
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

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def brake(self):
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

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def decelerate(self, count):
        '''
        Applies the value to incrementally slow the motor target velocity
        to zero, using either a slow (brake) or fast (halt) deceleration. Both
        halting and braking perform the same function, varying only by how
        quickly the change (acceleration) occurs.

        TODO
        The function should increment as a percentage of the motor target velocity
        so that if the robot is moving in an arc the braking will roughly follow
        that arc rather than having the slower motor come to a stop first,
        avoiding a final spiral inwards.
        '''
        self._log.info(Fore.BLACK + 'decelerate() port: {:5.2f}; stbd: {:5.2f}'.format(self._port_motor.target_velocity, self._stbd_motor.target_velocity))
        if isclose(self._port_motor.target_velocity, 0.0, abs_tol=0.5) and isclose(self._stbd_motor.target_velocity, 0.0, abs_tol=0.5):
            # stopping...
            self.reset_deceleration()
            self.stop()
            self.stop_loop() # not necessarily...
            self._log.info(Fore.YELLOW + 'deceleration complete.')
        else:
            # still decelerating...
            if isclose(self._port_motor.target_velocity, 0.0, abs_tol=1.0):
                self._port_motor.target_velocity = 0.0
            else:
                self._port_motor.target_velocity = self._port_motor.target_velocity * self._decelerate_ratio
            if isclose(self._stbd_motor.target_velocity, 0.0, abs_tol=1.0):
                self._stbd_motor.target_velocity = 0.0
            else:
                self._stbd_motor.target_velocity = self._stbd_motor.target_velocity * self._decelerate_ratio
        # print stats...
        if self._log.is_at_least(Level.WARN):
            self._log.info(Style.DIM + '[{:04d}] velocity:'.format(count)
                    + Fore.RED   + ' port: {:5.2f} ➔ {:<5.2f}'.format(self._port_motor.velocity, self._port_motor.target_velocity)
                    + ' {:5.2f}'.format(self._port_motor.current_power)
                    + Fore.CYAN  + '\t:: '
                    + Fore.GREEN + 'stbd: {:5.2f} ➔ {:<5.2f}'.format(self._port_motor.velocity, self._stbd_motor.target_velocity)
                    + ' {:5.2f}'.format(self._stbd_motor.current_power)
                    + Fore.CYAN  + '\t:: decelerate: ' + Fore.BLUE + '{:.0%}'.format(self._decelerate_ratio))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def reset_deceleration(self):
        '''
        Halts any automated deceleration.
        '''
        self._decelerate_ratio = 0.0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def stop(self):
        '''
        Stops both motors immediately, with no slewing.
        '''
        self._log.info('stopping...')
        if not self.stopped:
            self._port_motor.target_velocity = 0.0
            self._stbd_motor.target_velocity = 0.0
            self._log.info('stopped.')
        else:
            self._log.warning('already stopped.')
        # call stop anyway
        self._port_motor.stop()
        self._stbd_motor.stop()
        return True

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def stopped(self):
        '''
        Returns true if the velocity of both motors is zero.
        '''
        return self._port_motor.velocity == 0 and self._stbd_motor.velocity == 0

  # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def is_in_motion(self):
        '''
        Returns true if either motor is moving.
        '''
        return self._port_motor.is_in_motion() or self._stbd_motor.is_in_motion()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        '''
        Enables the motors. This issues a warning if already enabled, but no
        harm is done in calling it repeatedly.
        '''
        if self.enabled:
            self._log.warning('already enabled.')
        else:
            if not self.loop_is_running():
                self._port_motor.enable()
                self._stbd_motor.enable()
                Component.enable(self)
                self.start_loop()
            self._log.info('enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable the motors, halting first if in motion.
        '''
        if self.enabled:
            self._log.info('disabling...')
            Component.disable(self)
            if self.is_in_motion(): # if we're moving then halt
                self._log.warning('event: motors are in motion (halting).')
                self._port_motor.stop()
                self._stbd_motor.stop()
            self._port_motor.disable()
            self._stbd_motor.disable()
            self._log.info('disabled.')
        else:
            self._log.debug('already disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        '''
        Halts, turn everything off and stop doing anything.
        '''
        if not self.closed:
            Component.close(self)
            self._port_motor.close()
            self._stbd_motor.close()

#EOF
