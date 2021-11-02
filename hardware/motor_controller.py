#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-16
# modified: 2021-10-31
#

import sys, time
from threading import Thread
import asyncio, itertools, random, traceback
from math import isclose
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

import core.globals as globals
globals.init()

from core.logger import Logger, Level
from core.component import Component
from core.event import Event
from core.orientation import Orientation
from core.direction import Direction
from core.speed import Speed
from core.rate import Rate
from core.message import Message, Payload
from core.message_bus import MessageBus
from hardware.motor import Motor
from hardware.motor_configurer import MotorConfigurer
from hardware.motor_directive import MotorDirective
from hardware.slew import SlewRate
from hardware.speed_indicator import SpeedIndicator

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MotorController(Component):
    '''
    A motor controller that asbtracts the actual control of two motors
    from the physical motor control hardware.

    This relies upon both a SlewLimiter and JerkLimiter so that velocity
    and power (resp.) changes occur gradually and safely. It also contains
    the motor thread loop, which is used to react to directives sent to
    its dispatch methods:

      dispatch_stop_event()       reacts to event only for both motors
      dispatch_chadburn_event()   reacts to event only for both motors
      dispatch_velocity_event()   reacts to motor directive
      dispatch_theta_event()      reacts to motor directive

    :param config:          the application configuration
    :param message_bus:     the application MessageBus
    :param motor_config:    the MotorConfigurator object
    :param external_clock:  optional external system clock
    :param level:           the logging level
    '''
    def __init__(self, config, message_bus, motor_configurer, use_external_clock=False, level=Level.INFO):
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
        self._use_ext_clock        = use_external_clock
        # temporary until we move functionality to motors
        self._loop_thread          = None
        self._loop_enabled         = False
        self._event_counter        = itertools.count()
        self._last_port_velocity   = None
        self._last_stbd_velocity   = None
        # configured constants
        self._slew_limiter_enabled = config['kros'].get('motor').get('enable_slew_limiter')
        _cfg = config['kros'].get('motor').get('motor_controller')
        self._verbose              = _cfg.get('verbose')
        self._loop_freq_hz         = _cfg.get('loop_freq_hz')      # main loop frequency
        self._loop_delay_sec       = 1 / self._loop_freq_hz
        self._log.info('loop frequency:\t{}Hz ({:4.2f}s)'.format(self._loop_freq_hz, self._loop_delay_sec))
        self._rate                 = Rate(self._loop_freq_hz, Level.ERROR)
        self._accel_increment      = _cfg.get('accel_increment')   # normal incremental acceleration
        self._decel_increment      = _cfg.get('decel_increment')   # normal incremental deceleration
        self._log.info('accelerate increment: {:5.2f}; decelerate increment: {:5.2f}'.format(self._accel_increment, self._decel_increment))
        # slew rate for quick halt behaviour
        self._halt_slew_rate       = SlewRate.from_string(_cfg.get('halt_rate'))
        self._log.info('halt rate:\t{}'.format(self._halt_slew_rate.name))
        # slew rate for slower braking behaviour
        self._emergency_slew_rate  = SlewRate.FASTEST
        self._brake_slew_rate      = SlewRate.from_string(_cfg.get('brake_rate'))
        self._log.info('brake rate:\t{}'.format(self._brake_slew_rate.name))
        self._spin_speed           = Speed.from_string(_cfg.get('spin_speed')) # motor speed when spinning
        self._log.info('spin speed:\t{}'.format(self._spin_speed.name))
        self._millis               = lambda: int(round(time.time() * 1000))
        self._start_time           = self._millis()
        self._log.info('motors ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'motor-ctrl'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def start_loop(self):
        '''
        Start the loop Thread.

        If we're using an external clock this generates a warning message
        and otherwise does nothing.
        '''
        self._log.info('start motor control loop...')
        if not self.enabled:
            raise Exception('not enabled.')
        if self.loop_is_running:
            if self._use_ext_clock:
                self._log.warning('cannot start control loop: using external clock.')
            else:
                self._log.warning('loop already running.')
        elif self._loop_thread is None:
            if self._use_ext_clock:
                raise Exception('cannot use thread loop: external clock enabled.') # TEMP shouldn't be necessary
            self._loop_enabled = True
            _is_daemon = False
            self._loop_thread = Thread(name='display_loop', target=MotorController._loop, args=[self, lambda: self._loop_enabled], daemon=_is_daemon)
            self._loop_thread.start()
            self._log.info('loop enabled.')
        else:
            raise Exception('cannot enable loop: thread already exists.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _loop(self, f_is_enabled):
        '''
        The motors loop, which executes while the flag argument lambda is True.
        '''
        self._log.info('loop start.')
        try:
            while f_is_enabled():
                self._port_motor.update_target_velocity()
                self._stbd_motor.update_target_velocity()
                # add execute any callbacks here...
                if self._verbose: # print stats
                    self.print_info(next(self._event_counter))
                self._rate.wait()
        except Exception as e:
            self._log.error('error in loop: {}\n{}'.format(e, traceback.format_exc()))
        finally:
            self._log.info(Fore.GREEN + 'exited motor control loop.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _external_callback_method(self):
        '''
        The callback called by the external clock as an alternative to the
        asyncio _loop() method.
        '''
        if self.enabled:
            _now = self._millis()
            self._port_motor.update_target_velocity()
            self._stbd_motor.update_target_velocity()
            _elapsed = _now - self._start_time
            self._start_time = _now
            if self._verbose: # print stats
                self.print_info(next(self._event_counter))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def stop_loop(self):
        '''
        Stop the loop.
        '''
        if self.loop_is_running:
            self._loop_enabled = False
            self._loop_thread  = None
            self._log.info('loop disabled.')
        else:
            self._log.warning('already disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def loop_is_running(self):
        '''
        Returns true if using an external clock or if the loop thread is alive.
        '''
        return self._use_ext_clock \
                or ( self._loop_enabled and self._loop_thread != None and self._loop_thread.is_alive() )

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def dispatch_stop_event(self, payload, reset_slew=True):
        '''
        A dispatcher for deceleration and stopping events.

        While the argument is a Payload only the contained Event is significant;
        the value is ignored.

        There are three modes of stopping:

          Stop:  set the target velocity of the motors to zero immediately.
          Halt:  slew the target velocity of the motors to zero quickly.
          Brake: slew the target velocity of the motors to zero slowly.
        '''
        if self.enabled:
            if not isinstance(payload, Payload):
                raise TypeError('expected Payload, not {}'.format(type(payload)))
#           if not self.loop_is_running:
#               self.start_loop()
#           if not self.loop_is_running:
#               raise Exception('loop not running')
            _event = payload.event
            self._log.info('dispatch stop event: {}'.format(_event.label))
            if reset_slew:
                self._reset_slew_rate()
            if _event is Event.HALT:
                self.halt()
            elif _event is Event.BRAKE:
                self.brake()
            elif _event is Event.STOP:
                self.stop()
            else:
                raise ValueError('unrecognised stop event {}'.format(_event.label))
        else:
            self._log.warning('disabled: ignoring stop dispatch.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def dispatch_chadburn_event(self, payload, reset_slew=True):
        '''
        A dispatcher for chadburn events, e.g., full, half, slow and dead slow
        for both ahead and astern.

        While the argument is a Payload only the contained Event is significant;
        the value is ignored. The Event itself provides the direction and speed.
        '''
        if self.enabled:
#           if not self.loop_is_running:
#               self.start_loop()
            if not self.loop_is_running:
                raise Exception('loop not running')
            if not isinstance(payload, Payload):
                raise TypeError('expected Payload, not {}'.format(type(payload)))
            if reset_slew:
                self._reset_slew_rate()
            _event = payload.event
            self._log.info('dispatch chadburn event: {}'.format(_event.label))
            _speed     = _event.speed
            _direction = _event.direction
            _value = float(_speed.velocity) if _direction is Direction.AHEAD else float(-1.0 * _speed.velocity)
            self._log.info('set chadburn velocity: {} direction: {}; value: {}'.format(_speed.label, _direction.label, _value))
            self.set_motor_velocity(Orientation.PORT, _value)
            self.set_motor_velocity(Orientation.STBD, _value)
        else:
            self._log.warning('disabled: ignoring chadburn dispatch.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def dispatch_velocity_event(self, payload, reset_slew=True):
        '''
        A dispatcher for velocity change events.
        '''
        if self.enabled:
            self._log.info('🐢 A. dispatch velocity event; payload type {}; payload: {}'.format(type(payload), payload))
#           if not self.loop_is_running:
#               self.start_loop()
            if not self.loop_is_running:
                raise Exception('loop not running')
            if isinstance(payload, MotorDirective):
                self._log.info('🐢 B. dispatch velocity event; MotorDirective type {}; payload: {}'.format(type(payload), payload))
                # TODO get Speed and Direction
                _event = payload.event
                _motor_directive = payload
                _value = payload.value
                _orientation = _motor_directive.orientation
                _direction   = _motor_directive.direction
                _speed       = _motor_directive.speed

            elif isinstance(payload, Payload):
                # TODO get speed value as int or float
                _event = payload.event
                _value = payload.value
                _orientation = Orientation.BOTH
                _direction   = None
                _speed       = None
                self._log.info('🐢 E. dispatch velocity event; Payload type {}; payload: {}; value: {}'.format(type(payload), payload, _value))

            self._log.info('🐢🐢 Z. dispatch velocity event;\nPayload type {}; payload: {}; value: {};\n'.format(
                    type(payload), payload, _value) + Fore.YELLOW + 'orientation: {}; direction: {}; speed: {}'.format(
                    _orientation, _direction, _speed))

            return
            if True:
                    # increase or decrease BOTH ..............................
                if _event is Event.INCREASE_VELOCITY:
                    # INCREASE_VELOCITY      = ( 207, "increase velocity",      100,   Group.VELOCITY )
                    self._log.info('🐢 C. dispatch velocity event {}; type {}; payload: {}; value: {}'.format(_event.label, type(payload), payload, _value))
                elif _event is Event.DECREASE_VELOCITY:
                    # DECREASE_VELOCITY      = ( 208, "decrease velocity",      100,   Group.VELOCITY )
                    self._log.info('🐢 D. dispatch velocity event {}; type {}; payload: {}; value: {}'.format(_event.label, type(payload), payload, _value))




                if _event is Event.VELOCITY or _event is Event.PORT_VELOCITY or _event is Event.STBD_VELOCITY:
                    self._log.info('🐢 F. dispatch velocity event {}; type {}; payload: {}; value: {}'.format(_event.label, type(payload), payload, _value))
                    # set velocity from int, float, or Speed .................
                    # VELOCITY               = ( 200, "velocity",               100,   Group.VELOCITY ) # with value
                    # PORT_VELOCITY          = ( 201, "port velocity",          100,   Group.VELOCITY ) # with value
                    # STBD_VELOCITY          = ( 202, "stbd velocity",          100,   Group.VELOCITY ) # with value
                    pass

                elif _event is Event.INCREASE_PORT_VELOCITY:
                    self._log.info('🐢🐢 G. dispatch velocity INCREASE_PORT_VELOCITY; payload type: {}; payload: {}; value: {}'.format(type(payload), payload, _value))
                    self._increment_motor_velocity(Orientation.PORT, self._accel_increment)
                    self._log.info('increase PORT velocity; velocity: {:5.2f}'.format(self._port_motor.velocity))
                    pass
                elif _event is Event.DECREASE_PORT_VELOCITY:
                    self._log.info('🐢🐢 H. dispatch velocity DECREASE_PORT_VELOCITY; payload type: {}; payload: {}; value: {}'.format(type(payload), payload, _value))
                    self._increment_motor_velocity(Orientation.PORT, -1 * self._decel_increment)
                    self._log.info('decrease PORT velocity; velocity: {:5.2f}'.format(self._port_motor.velocity))
                    pass
                elif _event is Event.INCREASE_STBD_VELOCITY:
                    self._log.info('🐢🐢 I. dispatch velocity INCREASE_STBD_VELOCITY; payload type: {}; payload: {}; value: {}'.format(type(payload), payload, _value))
                    self._increment_motor_velocity(Orientation.STBD, self._accel_increment)
                    self._log.info('increase STBD velocity; velocity: {:5.2f}'.format(self._stbd_motor.velocity))
                    pass
                elif _event is Event.DECREASE_STBD_VELOCITY:
                    self._log.info('🐢🐢 J. dispatch velocity DECREASE_STBD_VELOCITY; payload type: {}; payload: {}; value: {}'.format(type(payload), payload, _value))
                    self._increment_motor_velocity(Orientation.STBD, -1 * self._decel_increment)
                    self._log.info('decrease STBD velocity; velocity: {:5.2f}'.format(self._stbd_motor.velocity))

            else:
                raise TypeError('expected Payload or MotorDirective, not {}'.format(type(payload)))
            if reset_slew:
                self._reset_slew_rate()

            self._log.info('🐢 Z. dispatch velocity event {}; payload value type {}; value: {}'.format(_event.label, type(_value), _value))
            return # TEMP

            # # velocity directives ............................................

#           self._log.info('processing message with event {} and motor directive of direction: {} and speed: {}.'.format(
#                   _event.label, _motor_directive.direction, _motor_directive.speed))
            '''
            if _event is Event.VELOCITY or _event is Event.PORT_VELOCITY or _event is Event.STBD_VELOCITY:

    #           _port_velocity = 0.0
    #           _stbd_velocity = 0.0
                if isinstance(_value, tuple):
                    if isinstance(_value[0], Orientation):
                        self._log.info('🐢 C. dispatch velocity event {}; payload value type {} (tuple mixed); value: {}'.format(_event.label, type(_value), _value))
                        _orientation = _value[0]
                        _velocities  = _value[1]
                        _port_velocity = _velocities[0]
                        _stbd_velocity = _velocities[1]
                    else:
                        self._log.info('🐢 D. dispatch velocity event {}; payload value type {} (tuple mono); value: {}'.format(_event.label, type(_value), _value))
                        _port_velocity = _value[0]
                        _stbd_velocity = _value[1]

                elif isinstance(_value, float):
                    self._log.info('🐢 E. dispatch velocity event {}; payload value type {} (float); value: {}'.format(_event.label, type(_value), _value))
                    _port_velocity = _value
                    _stbd_velocity = _value

                elif isinstance(_value, int):
                    self._log.info('🐢 F. dispatch velocity event {}; payload value type {} (int); value: {}'.format(_event.label, type(_value), _value))
                    _port_velocity = float(_value)
                    _stbd_velocity = float(_value)

                elif isinstance(_value, Orientation):
                    raise TypeError('expected either a single or a tuple of velocity values, not an Orientation.')
                else:
                    raise TypeError('expected either a single or a tuple of velocity values, not a {}'.format(type(_value)))

                if _event is Event.VELOCITY:
                    _changed = self._last_port_velocity != _port_velocity or self._last_stbd_velocity != _stbd_velocity
                    if _changed:
                        self._log.info('set velocity;\t'
                                + Fore.RED   + 'port: {:5.2f} / {:5.2f}; '.format(_port_velocity, self._port_motor.velocity)
                                + Fore.GREEN + 'stbd: {:5.2f} / {:5.2f}'.format(_stbd_velocity, self._stbd_motor.velocity))
                    self.set_motor_velocity(Orientation.PORT, _port_velocity)
                    self.set_motor_velocity(Orientation.STBD, _stbd_velocity)

                elif _event is Event.PORT_VELOCITY:
                    self.set_motor_velocity(Orientation.PORT, _port_velocity)
                    self._log.info('🐢 set PORT velocity; value: {}; velocity: {:5.2f}'.format(_port_velocity, self._port_motor.velocity))

                elif _event is Event.STBD_VELOCITY:
                    self.set_motor_velocity(Orientation.STBD, _stbd_velocity)
                    self._log.info('🐢 set STBD velocity; value: {}; velocity: {:5.2f}'.format(_stbd_velocity, self._stbd_motor.velocity))

                self._last_port_velocity = _port_velocity
                self._last_stbd_velocity = _stbd_velocity

            else:

                if _event is Event.INCREASE_PORT_VELOCITY:
                    self._increment_motor_velocity(Orientation.PORT, self._accel_increment)
                    self._log.info('increase PORT velocity; velocity: {:5.2f}'.format(self._port_motor.velocity))
                    pass
                elif _event is Event.DECREASE_PORT_VELOCITY:
                    self._increment_motor_velocity(Orientation.PORT, -1 * self._decel_increment)
                    self._log.info('decrease PORT velocity; velocity: {:5.2f}'.format(self._port_motor.velocity))
                    pass
                elif _event is Event.INCREASE_STBD_VELOCITY:
                    self._increment_motor_velocity(Orientation.STBD, self._accel_increment)
                    self._log.info('increase STBD velocity; velocity: {:5.2f}'.format(self._stbd_motor.velocity))
                    pass
                elif _event is Event.DECREASE_STBD_VELOCITY:
                    self._increment_motor_velocity(Orientation.STBD, -1 * self._decel_increment)
                    self._log.info('decrease STBD velocity; velocity: {:5.2f}'.format(self._stbd_motor.velocity))
                    pass
                elif _event is Event.INCREASE_VELOCITY:
                    self._increment_motor_velocity(Orientation.PORT, self._accel_increment)
                    self._increment_motor_velocity(Orientation.STBD, self._accel_increment)
                    self._log.info('increase velocity;\t'
                            + Fore.RED + 'port: {:5.2f};\t'.format(self._port_motor.velocity)
                            + Fore.GREEN + 'stbd: {:5.2f}'.format(self._stbd_motor.velocity))
                elif _event is Event.DECREASE_VELOCITY:
                    self._increment_motor_velocity(Orientation.PORT, -1 * self._decel_increment)
                    self._increment_motor_velocity(Orientation.STBD, -1 * self._decel_increment)
                    self._log.info('decrease velocity;\t'
                            + Fore.RED + 'port: {:5.2f};\t'.format(self._port_motor.velocity)
                            + Fore.GREEN + 'stbd: {:5.2f}'.format(self._stbd_motor.velocity))
                else:
                    raise ValueError('unrecognised velocity event {}'.format(_event.label))
            '''

        else:
            self._log.warning('disabled: ignoring velocity dispatch.')


    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def dispatch_theta_event(self, payload, reset_slew=True):
        '''
        A dispatcher for theta (rotation/turning) events, e.g., turn ahead,
        turn astern for port and starboard, spin port and spin starboard.
        '''
        if self.enabled:
#           if not self.loop_is_running:
#               self.start_loop()
            if not self.loop_is_running:
                raise Exception('loop not running')
            if not isinstance(payload, Payload):
                raise TypeError('expected Payload, not {}'.format(type(payload)))
            # FIXME
            if not isinstance(payload, MotorDirective):
                raise TypeError('expected MotorDirective, not {}'.format(type(payload)))
            if reset_slew:
                self._reset_slew_rate()

#           _motor_directive = _payload
#           self._log.info('🙅 processing message with event {} and motor directive of direction: {} and speed: {}.'.format(
#                   _event.label, _motor_directive.direction, _motor_directive.speed))

            _event = payload.event
            self._log.info('dispatch theta event: {}'.format(_event.label))
            _value = payload.value
            self._log.info('theta event: {}'.format(_event.label))

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
                self.set_motor_velocity(Orientation.PORT, Speed.HALF.velocity)
                self.set_motor_velocity(Orientation.STBD, Speed.FULL.velocity)
            elif _event is Event.TURN_ASTERN_PORT:
                self._log.info('theta TURN_ASTERN_PORT event.')
                self.set_motor_velocity(Orientation.PORT, -1 * Speed.HALF.velocity)
                self.set_motor_velocity(Orientation.STBD, -1 * Speed.FULL.velocity)
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
                self.set_motor_velocity(Orientation.PORT, Speed.FULL.velocity)
                self.set_motor_velocity(Orientation.STBD, Speed.HALF.velocity)
                pass
            elif _event is Event.TURN_ASTERN_STBD:
                self._log.info('theta TURN_ASTERN_STBD event.')
                self.set_motor_velocity(Orientation.PORT, -1 * Speed.FULL.velocity)
                self.set_motor_velocity(Orientation.STBD, -1 * Speed.HALF.velocity)
                pass
            elif _event is Event.TURN_TO_STBD:
                self._log.info('theta TURN_TO_STBD event (unimplemented).')
                pass
            elif _event is Event.SPIN_STBD:
                self._log.info('SPIN_STBD event.')
                self._spin(Orientation.STBD)
            else:
                raise ValueError('unrecognised theta event {}'.format(_event.label))
        else:
            self._log.warning('disabled: ignoring theta dispatch.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_motor(self, orientation):
        '''
        Returns the motor with the matching orientation.
        '''
        if orientation is Orientation.PORT:
            return self._port_motor
        elif orientation is Orientation.STBD:
            return self._stbd_motor
        else:
            raise Exception('expected PORT or STBD orientation.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_motor_velocity(self, orientation, target_velocity):
        '''
        A convenience method that sets the target velocity and motor
        power of the specified motor. Accepts either ints or floats
        between -100 and 100.

        When the motor controller is disabled any calls to this method
        will override the target velocity argument and set it to zero.
        '''
        if not self.enabled:
            self._log.error('motor controller not enabled.')
            target_velocity = 0.0
        if isinstance(target_velocity, int):
#           self._log.warning('expected target velocity as float not int: {:d}'.format(target_velocity))
#           target_velocity = float(target_velocity)
            raise ValueError('expected target velocity as float not int: {:d}'.format(target_velocity))
        if not isinstance(target_velocity, float):
            raise ValueError('expected float, not {}'.format(type(target_velocity)))
        if orientation is Orientation.PORT:
            self._log.info('set_motor_velocity ' + Fore.RED   + 'PORT: {:5.2f}'.format(target_velocity))
            self._port_motor.target_velocity = target_velocity
        elif orientation is Orientation.STBD:
            self._log.info('set_motor_velocity ' + Fore.GREEN + 'STBD: {:5.2f}'.format(target_velocity))
            self._stbd_motor.target_velocity = target_velocity
        else:
            raise Exception('expected PORT or STBD orientation.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def reset_max_fwd_velocity(self):
        '''
        Resets the maximum forward velocity limit for both motors to the default.
        '''
        self._port_motor.reset_max_fwd_velocity()
        self._stbd_motor.reset_max_fwd_velocity()
        self._log.info('reset motor speed limit.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _spin(self, orientation):
        '''
        Spin to either port (counter-clockwise) or starboard (clockwise) by
        setting the target velocity of each motor to opposite directions.
        '''
        self._log.info('theta SPIN {}.'.format(orientation.name))
#       self._reset_slew_rate()
        if orientation is Orientation.PORT:
            _port_velocity = -1.0 * self._spin_speed.velocity
            _stbd_velocity = self._spin_speed.velocity
        elif orientation is Orientation.STBD:
            _port_velocity = self._spin_speed.velocity
            _stbd_velocity = -1.0 * self._spin_speed.velocity
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
    def emergency_stop(self):
        self._log.info('emergency stop...')
        # suppress any behaviours
        _kros = globals.get('kros')
        _behaviour_mgr = _kros.get_behaviour_manager()
        if _behaviour_mgr:
            self._log.info('suppressing behaviours...')
#           _behaviour_mgr.suppress()
            _behaviour_mgr.suppress_all_behaviours()
        else:
            self._log.info('behaviour manager: ' + Fore.YELLOW + 'disabled')

        self._macro_publisher = _kros.get_macro_publisher()
        if self._macro_publisher:
            # suppress any macros
            self._log.info('suppressing macros...')
            self._macro_publisher.suppress()
        else:
            self._log.info('no macro-publisher available.')

        # now stop very fast
#       self._set_slew_rate(self._emergency_slew_rate)
        self._port_motor.target_velocity = 0.0
        self._stbd_motor.target_velocity = 0.0
        # we rely on this ultimately
#       self._port_motor.stop()
#       self._stbd_motor.stop()
#       self._port_motor.off()
#       self._stbd_motor.off()
#       self._reset_slew_rate()
        self._log.info('emergency stopped.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def stop(self):
        '''
        Stops both motors immediately, with no slewing.

        This differs from both halt() and brake() in that it also suppresses
        all behaviours.
        '''
        if self.is_stopped:
            self._log.warning('already stopped.')
            # but we do it anyway...
        else:
            self._log.info('stopping...')
        # suppress any behaviours
#       self._suppress_behaviours()
        if self.loop_is_running:
            if self._slew_limiter_enabled:
                self._log.info('stopping soft...')
                try:
                    # temporarily suppress slew
                    _port_slew_limiter_suppressed = self._port_motor.slew_limiter.suppressed
                    _stbd_slew_limiter_suppressed = self._port_motor.slew_limiter.suppressed
                    self._port_motor.target_velocity = 0.0
                    self._stbd_motor.target_velocity = 0.0
                finally:
                    if not _port_slew_limiter_suppressed:
                        self._port_motor.slew_limiter.release
                    if not _stbd_slew_limiter_suppressed:
                        self._stbd_motor.slew_limiter.release
            else:
                # the last two blocks aren't currently very different from each other
                self._log.info('stopping hard...')
                # set velocity but don't wait, just call stop
                self._reset_slew_rate() # use default FAST rate
                self._port_motor.target_velocity = 0.0
                self._stbd_motor.target_velocity = 0.0
                # we rely on this ultimately
                self._port_motor.stop()
                self._stbd_motor.stop()
        else:
            self.emergency_stop()
        self._log.info('stopped.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def halt(self):
        '''
        Quickly (but not immediately) stops both motors.
        '''
        if self.is_stopped:
            self._log.warning('already halted.')
            # but we do it anyway...
        else:
            self._log.info('halting...')
        if self._use_ext_clock or self._loop_enabled:
            if self._slew_limiter_enabled:
                self._log.info('halting soft...')
                try:
                    # use slew limiter for halting if available
                    self._set_slew_rate(self._halt_slew_rate)
                    self._port_motor.target_velocity = 0.0
                    self._stbd_motor.target_velocity = 0.0
                finally:
                    self._reset_slew_rate()
            else:
                self._log.info('halting hard...')
                self._port_motor.target_velocity = 0.0
                self._stbd_motor.target_velocity = 0.0
        else:
            self._log.info('halting very hard...')
            self.emergency_stop()
        self._log.info('halted.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def brake(self):
        '''
        Slowly coasts both motors to a stop.
        '''
        if self.is_stopped:
            self._log.warning('already braked.')
            # but we do it anyway...
        else:
            self._log.info('braking...')
        if self._use_ext_clock or self._loop_enabled:
            if self._slew_limiter_enabled:
                self._log.info('braking soft...')
                try:
                    # use slew limiter for halting if available
                    self._set_slew_rate(self._brake_slew_rate)
                    self._port_motor.target_velocity = 0.0
                    self._stbd_motor.target_velocity = 0.0
                finally:
                    self._reset_slew_rate()
            else:
                self._log.info('braking hard...')
                self._port_motor.target_velocity = 0.0
                self._stbd_motor.target_velocity = 0.0
        else:
            self._log.info('braking very hard...')
            self.emergency_stop()
        self._log.info('braked.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_slew_rate(self, slew_rate):
        '''
        Set the slew rate for both motors to the argument.
        '''
        self._port_motor.slew_limiter.slew_rate = slew_rate
        self._stbd_motor.slew_limiter.slew_rate = slew_rate

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _reset_slew_rate(self):
        '''
        Halts any automated deceleration.
        '''
        self._port_motor.slew_limiter.reset()
        self._stbd_motor.slew_limiter.reset()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def wait_til_stopped(self, timeout_sec=3):
        '''
        Returns either after all motors have stopped, or the timeout, whichever
        is first. The default timeout is 3 seconds.
        '''
        for _count in range(timeout_sec):
            _count += 1
            time.sleep(1.0)
            if self.is_stopped:
                break

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def is_stopped(self):
        '''
        Returns true if the velocity of both motors is zero.
        '''
        return not self.is_in_motion
#       return self._port_motor.velocity == 0 and self._stbd_motor.velocity == 0

  # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def is_in_motion(self):
        '''
        Returns true if either motor is moving, i.e., if the motor power of
        either motor is greater than zero.
        '''
        return self._port_motor.is_in_motion or self._stbd_motor.is_in_motion

  # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def is_moving_ahead(self):
        '''
        Returns true if both motors are moving ahead.
        '''
        return self._port_motor.is_moving_ahead and self._stbd_motor.is_moving_ahead

  # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def is_moving_astern(self):
        '''
        Returns true if both motors are moving astern.
        '''
        self._log.info('is_moving_astern() PORT: '
                    + Fore.RED   + '{}'.format(self._port_motor.is_moving_astern)
                    + Fore.CYAN  + '; STBD: '
                    + Fore.GREEN + '{}'.format(self._stbd_motor.is_moving_astern))
        return self._port_motor.is_moving_astern and self._stbd_motor.is_moving_astern

    # TODO: is_spinning_clockwise() and is_spinning_counter_clockwise()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_info(self, count):
        if self.is_stopped:
            self._log.info(('[{:04d}] '.format(count) if count else '') + 'velocity: stopped.')
        else:
            self._log.info(('[{:04d}] '.format(count) if count else '')
                    + 'velocity: '
                    + Fore.RED   + 'port: {:<5.2f} -> {:<5.2f} / {:<5.2f}'.format(
                            self._port_motor.velocity, self._port_motor.target_velocity, self._port_motor.current_power)
                    + ' {:5.2f}'.format(self._port_motor.current_power)
                    + Fore.CYAN  + ' :: '
                    + Fore.GREEN + 'stbd: {:<5.2f} -> {:<5.2f} / {:<5.2f}'.format(
                            self._stbd_motor.velocity, self._stbd_motor.target_velocity, self._stbd_motor.current_power)
                    + Fore.CYAN + ' :: movement: {}'.format(self._characterise_movement()))

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
    def print_motor_status(self):
        '''
        Pretty-prints the status of the motor controller and motors.
        '''
        # motor controller ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

        self._log.info('motor controller:')
        self._log.info('  loop running:\t' + Fore.YELLOW + '{}'.format(self.loop_is_running))
        self._log.info('  is in motion:\t' + Fore.YELLOW + '{}'.format(self.is_in_motion))
        self._log.info('  is stopped:  \t' + Fore.YELLOW + '{}'.format(self.is_stopped))

        # motors ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

        self._log.info('motors:')

        # port ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

        self._log.info(Fore.RED + '\t{}{}'.format('port',(' ' * 9))
                + Fore.CYAN + 'power: ' + Fore.YELLOW + '{:5.2f}'.format(self._port_motor.current_power))
        self._log.info(Fore.RED + '\tmotor' \
                + Fore.CYAN + ' {}enabled: '.format((' ' * 5))
                + Fore.YELLOW + '{}\t'.format(self._port_motor.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._port_motor.suppressed))

        self._log.info(Fore.RED + '\tslew' \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len('port')))))
                + Fore.YELLOW + '{}\t'.format(self._port_motor.slew_limiter.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._port_motor.slew_limiter.suppressed))

        self._log.info(Fore.RED + '\tpid' \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (11 - len('port')))))
                + Fore.YELLOW + '{}\t'.format(self._port_motor.pid_controller.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._port_motor.pid_controller.suppressed))

        # we currently never enable the jerk limiter as it doesn't work...
        if self._port_motor.jerk_limiter.enabled:
            self._log.info(Fore.RED + '\t{}'.format('jerk') \
                    + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len('port')))))
                    + Fore.YELLOW + '{}\t'.format(self._port_motor.jerk_limiter.enabled)
                    + Fore.CYAN + 'suppressed: '
                    + Fore.YELLOW + '{}'.format(self._port_motor.jerk_limiter.suppressed))

        # starboard ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

        self._log.info(Fore.GREEN + '\t{}{}'.format('stbd',(' ' * 9))
                + Fore.CYAN + 'power: ' + Fore.YELLOW + '{:5.2f}'.format(self._stbd_motor.current_power))
        self._log.info(Fore.GREEN + '\t{}'.format('motor') \
                + Fore.CYAN + ' {}enabled: '.format((' ' * 5))
                + Fore.YELLOW + '{}\t'.format(self._stbd_motor.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._stbd_motor.suppressed))

        self._log.info(Fore.GREEN + '\t{}'.format('slew') \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len('stbd')))))
                + Fore.YELLOW + '{}\t'.format(self._stbd_motor.slew_limiter.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._stbd_motor.slew_limiter.suppressed))

        self._log.info(Fore.GREEN + '\t{}'.format('pid') \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (11 - len('stbd')))))
                + Fore.YELLOW + '{}\t'.format(self._stbd_motor.pid_controller.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._stbd_motor.pid_controller.suppressed))

        self._log.info(Fore.GREEN + '\t{}'.format('jerk') \
                + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len('stbd')))))
                + Fore.YELLOW + '{}\t'.format(self._stbd_motor.jerk_limiter.enabled)
                + Fore.CYAN + 'suppressed: '
                + Fore.YELLOW + '{}'.format(self._stbd_motor.jerk_limiter.suppressed))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_movement_description(self, port_velocity, stbd_velocity):
        _avg_velocity = ( port_velocity + stbd_velocity ) / 2.0
        # TODO FIXME use existing methods!
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
    def enable(self):
        '''
        Enables the motors. This issues a warning if already enabled, but no
        harm is done in calling it repeatedly.
        '''
        if self.enabled:
            self._log.warning('already enabled.')
        else:
            Component.enable(self)
            if not self._use_ext_clock and not self.loop_is_running:
                self.start_loop()

            # optional speed indicator feature
            self._queue_publisher = globals.get('queue-publisher')
            if self._queue_publisher:
                self._log.info('using queue publisher to publish speed indicator events.')
                self._speed_indicator = SpeedIndicator(self._queue_publisher, self._port_motor, self._stbd_motor)
            else:
                self._log.warning('no speed indicator (no queue publisher available).')

            self._port_motor.enable()
            self._stbd_motor.enable()
            self._log.info('enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable the motors, halting first if in motion.
        '''
        if self.enabled:
            self._log.info('disabling...')
            self.stop_loop() # stop loop thread
            Component.disable(self)
            _count = 0
            while _count < 10 and self.is_in_motion: # if we're moving then halt
                _count += 1
                self._log.warning('[{:d}] event: motors are in motion (halting).'.format(_count))
                self._port_motor.stop()
                self._stbd_motor.stop()
                time.sleep(0.1)
            self._log.info('disabled.')
        else:
            self._log.debug('already disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        '''
        Halts, turn everything off and stop doing anything.
        '''
        if not self.closed:
            # if we're moving let's halt first
            if self.is_in_motion or not self.is_stopped:
                self.halt()
                while self.wait_til_stopped():
                    pass
            Component.close(self) # calls disable
            self._port_motor.close()
            self._stbd_motor.close()
        # stop anyway...
        self._port_motor.stop()
        self._stbd_motor.stop()
        self._port_motor.disable()
        self._stbd_motor.disable()

#EOF
