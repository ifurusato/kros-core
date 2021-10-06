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

import itertools, traceback
import math
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.event import Event
from core.speed import Speed
from core.util import Util
from core.ranger import Ranger
from core.orient import Orientation
from behave.behaviour import Behaviour
from behave.trigger_behaviour import TriggerBehaviour
from hardware.motor_controller import MotorController
from hardware.i2c_scanner import I2CScanner
# also see imports in _connect()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Swerve(Behaviour):

    _LAMBDA_PORT_NAME = 'swerve-port'
    _LAMBDA_STBD_NAME = 'swerve-stbd'

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
    def __init__(self, config, message_bus, message_factory, motor_ctrl, external_clock, suppressed=True, enabled=False, level=Level.INFO):
        self._level = level
        Behaviour.__init__(self, 'swerve', config, message_bus, message_factory, suppressed=suppressed, enabled=enabled, level=level)
        if motor_ctrl:
            if not isinstance(motor_ctrl, MotorController):
                raise ValueError('wrong type for motor_ctrl argument: {}'.format(type(motor_ctrl)))
            self._port_motor   = motor_ctrl.get_motor(Orientation.PORT)
            self._stbd_motor   = motor_ctrl.get_motor(Orientation.STBD)
        else:
            self._port_motor   = None
            self._stbd_motor   = None
        self._ext_clock    = external_clock
        if self._ext_clock:
            self._ext_clock.add_callback(self._tick)
            pass
        else:
            self._log.error('unable to enable swerve behaviour: no external clock available.')
#           raise Exception()
        self._config = config
        _cfg = self._config['kros'].get('behaviour').get('swerve')
        self._modulo     = _cfg.get('tick_modulo') # 10 # modulo on ticks
        # comparison configuration .............
        self._reverse    = _cfg.get('reverse') # reverses the effect of the differential
        self._multiplier = _cfg.get('multiplier') # 1.0
        # clipping lambda
        _minimum_output  = 0.0
        _maximum_output  = 255
        self._clip = lambda n: _minimum_output if n <= _minimum_output else _maximum_output if n >= _maximum_output else n
        self._ranger     = Ranger(_minimum_output, _maximum_output, 0.0, 1.0)
        # we have ten columns and 25.5 is 10% of 255, but we want a wide deadband
        _percent_tolerance = _cfg.get('tolerance')
        self._abs_tol   = ( _percent_tolerance / 100.0 ) * 255.0

        # lambda accepts distance and returns a ratio to multiply against velocity
        self._offset_port = 0.2
        self._offset_stbd = 0.2
        self._port_velocity_function = lambda : self.offset_port
        self._stbd_velocity_function = lambda : self.offset_stbd

        self._percent_ranger = Ranger(-1.0, 1.0, 0, 100)
        self._ioe       = None
        self._ifs       = None
        self._matrices  = None
        self._connected = False
        self._counter   = itertools.count()
        self.add_events([ Event.INFRARED_PORT, Event.INFRARED_STBD ])
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def offset_port(self):
        return self._offset_port

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def offset_stbd(self):
        return self._offset_stbd

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _compare(self, port, stbd):
        '''
        Compares the port and starboard values and returns lambda multipliers
        for each motor whose value depends on the ratio between the values,
        with a configurable deadband around zero to avoid oscillation.
        '''
        self._log.debug(Fore.RED + 'port: {}; '.format(port) + Fore.GREEN + 'stbd: {}'.format(stbd))

        _port = self._clip(port)
        _stbd = self._clip(stbd)
    #   print(Fore.CYAN + 'compare ' + Fore.RED + 'PORT: {:5.2f}\t'.format(_port) + Fore.CYAN + 'with ' + Fore.GREEN + 'STBD: {:5.2f}  \t'.format(_stbd) )

        if math.isclose(_port, _stbd, abs_tol=self._abs_tol):
            _port = 0.0
            _stbd = 0.0
    #       print(Fore.CYAN + 'equal: ' + Fore.RED + 'PORT: {:5.2f} '.format(_port) + Fore.CYAN + 'with ' + Fore.GREEN + 'STBD: {:5.2f}  \t'.format(_stbd))
        else:
            _comp = -1 if ( (stbd - port) < 0 ) else 1
            if _comp < 0: # then bias to PORT
                _port = abs(self._ranger.convert(_stbd - _port))
                _stbd = 0.0
            elif _comp > 0: # then bias to STBD
                _port = 0.0
                _stbd = abs(self._ranger.convert(_port - _stbd))
    #       print(Fore.CYAN + 'compare ' + Fore.RED + 'PORT: {:5.2f}\t'.format(_port) + Fore.CYAN + 'with ' + Fore.GREEN + 'STBD: {:5.2f}  \t'.format(_stbd)
    #               + Fore.WHITE + 'compared: {}'.format(_comp))
        if self._reverse:
            _port = 1.0 - _port
            _stbd = 1.0 - _stbd
        _port *= self._multiplier
        _stbd *= self._multiplier
        self._offset_port = _port
        self._offset_stbd = _stbd
        return ( _port, _stbd )

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _tick(self):
        '''
        On a clock tick modulo'd to cut down the frequency we read the
        oblique infrared sensors and use the ratio between them to set
        the lambda functions on the motors.
        '''
        if not self.suppressed:
            self._log.debug('tick; suppressed: {};\t'.format(self.suppressed))
            self._log.debug('swerving;\t'
                    + Fore.RED   + 'port: {:5.2f}cm/s;\t'.format(self._port_motor.velocity)
                    + Fore.GREEN + 'stbd: {:5.2f}cm/s'.format(self._stbd_motor.velocity))

            _count = next(self._counter)
            if _count % self._modulo == 0:

                try:

                    _port_raw = self._ioe.get_port_ir_value()
                    _stbd_raw = self._ioe.get_stbd_ir_value()

                    self._offset_port, self._offset_stbd = self._compare(_port_raw, _stbd_raw)
#                   self._compare(_port_raw, _stbd_raw)

                    _port_cm  = self._ifs.convert_to_distance(_port_raw)
                    _stbd_cm  = self._ifs.convert_to_distance(_stbd_raw)

                    # used for matrices only .....
                    _port_pc  = _port_raw / 255.0
                    _stbd_pc  = _stbd_raw / 255.0
                    _raw_diff = _port_raw - _stbd_raw
                    self._ratio_multiplier = 1.0
                    _ratio    = ( _port_pc - _stbd_pc ) * self._ratio_multiplier
 
                    _percent  = self._percent_ranger.convert(_ratio)
#                   self._log.info(Fore.YELLOW + 'RATIO: {:5.2f}; PERCENT: {:5.2f} '.format(_ratio, _percent))

                    if self._offset_port == 0.0 and self._offset_stbd == 0: # all things being equal
                        if self._matrices:
                            self._matrices.clear_all()
                        self._log.info('[{:04d}] (=) '.format(_count)
                                + Fore.RED    + Style.DIM + 'PORT: {:6.3f} / {:6.3f}cm / '.format(_port_raw, _port_cm) + Fore.YELLOW + ' {:5.2f}\t'.format(self._offset_port)
                                + Fore.GREEN  + Style.DIM + 'STBD: {:6.3f} / {:6.3f}cm / '.format(_stbd_raw, _stbd_cm) + Fore.YELLOW + ' {:5.2f}'.format(self._offset_stbd))
                    else:
                        if self._matrices:
                            self._matrices.percent(_percent)
                        if self._offset_port == 0.0: # offset to STBD
                            self._log.info('[{:04d}] (S) '.format(_count)
                                    + Fore.RED    + Style.NORMAL + 'PORT: {:6.3f} / {:6.3f}cm / '.format(_port_raw, _port_cm) + Fore.YELLOW + ' {:5.2f}\t'.format(self._offset_port)
                                    + Fore.GREEN  + Style.BRIGHT + 'STBD: {:6.3f} / {:6.3f}cm / '.format(_stbd_raw, _stbd_cm) + Fore.YELLOW + ' {:5.2f}'.format(self._offset_stbd))
                        else: # offset to PORT
                            self._log.info('[{:04d}] (P) '.format(_count)
                                    + Fore.RED    + Style.BRIGHT + 'PORT: {:6.3f} / {:6.3f}cm / '.format(_port_raw, _port_cm) + Fore.YELLOW + ' {:5.2f}\t'.format(self._offset_port)
                                    + Fore.GREEN  + Style.NORMAL + 'STBD: {:6.3f} / {:6.3f}cm / '.format(_stbd_raw, _stbd_cm) + Fore.YELLOW + ' {:5.2f}'.format(self._offset_stbd))

                    '''
                    if self._compare(_port_raw, _stbd_raw): # then they're close enough to each other (within tolerance) to consider balanced
                        self._log.info('[{:04d}] '.format(_count) + Fore.RED + 'IR {:6.3f} / {:6.3f}cm\t'.format(_port_raw, _port_cm)
                                + Fore.GREEN + '{:6.3f} / {:6.3f}cm\t'.format(_stbd_raw, _stbd_cm)
                                + Fore.WHITE + Style.NORMAL + 'ratio: SAME')
                    else:
                        _out_port = self._ port_ranger.convert(_port_raw)
                        _out_stbd = self._ stbd_ranger.convert(_stbd_raw)
                        self._log.info('[{:04d}] '.format(_count) + Fore.RED + 'IR {:6.3f} / {:6.3f}cm\t'.format(_port_raw, _port_cm)
                                + Fore.GREEN + '{:6.3f} / {:6.3f}cm\t'.format(_stbd_raw, _stbd_cm)
                                + Fore.WHITE + Style.NORMAL + 'ratio: {:4.1f}\t'.format(_ratio)
                                + Fore.RED + 'port: {:4.1f}\t'.format(_out_port)
                                + Fore.GREEN + 'stbd: {:4.1f}\t'.format(_out_stbd)
                                + Fore.YELLOW  + 'offset: {:4.1f}%'.format(_percent))
                    '''

                except KeyboardInterrupt:
                    print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
                except Exception as e:
                    print(Fore.RED + Style.BRIGHT + 'error testing ifs: {}\n{}'.format(e, traceback.format_exc()) + Style.RESET_ALL)
                finally:
                    if self._matrices:
                        self._matrices.clear_all()
            else:
#               self._log.info(Style.DIM + '[{:04d}] tick modulo.'.format(_count))
                pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _connect(self):
        '''
        Connect to the IO Expander, Integrated Front Sensor, and any Matrix
        displays.
        '''
        if self._connected:
            self._log.warning('already connected.')
        else:
            self._log.warning('🎯 🎯 🎯 connecting...')
            try:
                from hardware.io_expander import IoExpander
                from hardware.ifs import IntegratedFrontSensor
                from hardware.matrix import Matrices
                from hardware.rgbmatrix import RgbMatrix

                # configure ifs/ioe ..........................................
                self._ioe = IoExpander(self._config, Level.INFO)
                self._ifs = IntegratedFrontSensor(self._config, self._message_bus, self._message_factory, level=self._level)

                _i2c_scanner = I2CScanner(self._config, Level.DEBUG)
                # 11x7 white LED matrix
                _enable_port_11x7 = _i2c_scanner.has_address([0x77])
                _enable_stbd_11x7 = _i2c_scanner.has_address([0x75])
                _use_11x7         = _enable_port_11x7 and _enable_stbd_11x7
                # 5x5 RGB LED matrix
                _enable_port_5x5  = _i2c_scanner.has_address([0x77])
                _enable_stbd_5x5  = _i2c_scanner.has_address([0x74])
                _use_5x5          = _enable_port_5x5 and _enable_stbd_5x5
                # choose based on what's available
                if _use_11x7:
                    self._matrices = Matrices(_enable_port_11x7, _enable_stbd_11x7, Level.INFO)
                elif _use_5x5:
                    self._matrices = RgbMatrix(_enable_port_5x5, _enable_stbd_5x5, Level.INFO)
                else:
                    self._log.warning('could not find suitable pair of displays.')

                self._connected = True
                self._log.info('🍏 connected.')

            except ImportError as e:
                self._log.warning('error importing support libraries: {}'.format(e))
                self._log.info('🍎 unable to connect.')

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
                self._log.info('🍥 processing PORT message {}; '.format(message.name)
                        + Fore.PORT  + ' distance: {:5.2f}cm\n'.format(_distance_cm))
            elif message.payload.event is Event.INFRARED_STBD:
                _distance_cm = message.payload.value
                self._log.info('🍥 processing STBD message {}; '.format(message.name)
                        + Fore.GREEN + ' distance: {:5.2f}cm\n'.format(_distance_cm))
            else:
                raise ValueError('expected INFRARED_PORT or INFRARED_STBD event not: {}'.format(message.event.label))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_velocity_multipliers(self, reason):
        self._log.info('😨 set velocity multipliers: ' + Fore.YELLOW + '{}'.format(reason))
        self._set_velocity_multiplier(reason, Orientation.PORT, self._port_velocity_function())
        self._set_velocity_multiplier(reason, Orientation.STBD, self._stbd_velocity_function())

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_velocity_multiplier(self, reason, orientation, lambda_function):
        if orientation is Orientation.PORT:
            self._log.info(Fore.RED + 'setting PORT velocity multiplier: ' + '{}'.format(reason))
            self._port_motor.add_velocity_multiplier(Swerve._LAMBDA_PORT_NAME, lambda_function)
            self._log.info(Fore.RED + 'set PORT velocity multiplier: ' + '{}'.format(reason))
        elif orientation is Orientation.STBD:
            self._log.info(Fore.GREEN + 'setting STBD velocity multiplier: ' + '{}'.format(reason))
            self._stbd_motor.add_velocity_multiplier(Swerve._LAMBDA_STBD_NAME, lambda_function)
            self._log.info(Fore.GREEN + 'set STBD velocity multiplier: ' + '{}'.format(reason))
        else:
            raise TypeError('expected PORT or STBD orientation, not {}'.format(orientation))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _reset_velocity_multiplier(self, reason):
        self._log.info(Fore.MAGENTA + '😨 reset velocity multipliers: ' + Fore.YELLOW + '{}'.format(reason))
        self._port_motor.remove_velocity_multiplier(Swerve._LAMBDA_PORT_NAME)
        self._stbd_motor.remove_velocity_multiplier(Swerve._LAMBDA_STBD_NAME)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_trigger_behaviour(self, event):
        return TriggerBehaviour.TOGGLE

    @property
    def trigger_event(self):
        '''
        This returns the event used to enable/disable the behaviour manually.
        '''
        return Event.SWERVE

    def enable(self):
        '''
        Enables this Component.
        '''
        if self.enabled:
            self._log.warning('💚 swerve already enabled.')
        else:
            Component.enable(self)
            self._connect()
            if self._ioe and not self._ioe.enabled:
                self._ioe.enable()
            if self._ifs and not self._ifs.enabled:
                self._ifs.enable()
            self._log.info(Fore.BLUE + '💚 swerve enabled.')

    def release(self):
        '''
        Releases (un-suppresses) this Component.
        '''
        if not self.enabled:
            self._log.warning('swerve not enabled.')
        else:
            Component.release(self)
            self._set_velocity_multipliers('releasing swerve.')
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
        if not self.enabled:
            self._log.warning('swerve already disabled.')
        else:
            Component.disable(self)
            if self._ioe and self._ioe.enabled:
                self._ioe.disable()
            if self._ifs and self._ifs.disabled:
                self._ifs.disable()
            self._reset_velocity_multiplier('disabling swerve.')
            self._log.info(Fore.BLUE + '💙 swerve disabled.')



#EOF
