#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-10-05
# modified: 2021-04-22
#

import sys, traceback
from fractions import Fraction
from colorama import init, Fore, Style
init()
try:
    import pigpio
except ImportError:
    print(Fore.RED + "This script requires the pigpio module.\nInstall with: sudo apt install python3-pigpio" + Style.RESET_ALL)
    sys.exit(1)

from core.logger import Logger, Level
from core.orient import Orientation
from core.speed import Speed
from hardware.i2c_scanner import I2CScanner
from hardware.motor import Motor
from hardware.decoder import Decoder

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MotorConfigurer():
    '''
    Configures either a ThunderBorg motor controller for a pair of motors.
    If the ThunderBorg does not appear on the I²C bus the motors are mocked.

    :param config:          the application configuration
    :param message_bus:     the message bus handling event-laden messages
    :param i2c_scanner:     the I²C bus scanner
    :param motors_enabled:  an optional flag to enable motors (default false)
    :param level:           the logging level
    '''
    def __init__(self, config, message_bus, i2c_scanner, motors_enabled=False, level=Level.INFO):
        self._log = Logger("motor-config", level)
        if config is None:
            raise ValueError('null configuration argument.')
        self._config = config
        if Speed.FULL.ahead == 0.0:
            self._log.info('importing speed enum values from configuration...')
            Speed.configure(self._config)
        self._message_bus = message_bus
        if not isinstance(i2c_scanner, I2CScanner):
            raise ValueError('expected I2CScanner, not {}.'.format(type(i2c_scanner)))
        self._i2c_scanner = i2c_scanner
        self._log.debug('getting battery reading...')
        # configure from command line argument properties
        _args = self._config['kros'].get('arguments')
        self._motors_enabled = _args.get('motors_enabled') or motors_enabled
        self._log.info(Fore.YELLOW + 'motors enabled? {}'.format(self._motors_enabled))
        # default until successful in configuring ThunderBorg:
        self._config['kros'].get('arguments')['using_mocks'] = True
        if not self._motors_enabled: # overrides _enable_mock
#           sys.exit(0)
            self._enable_mock = True
        else:
            self._enable_mock = _args.get('mock_enabled')
        self._log.info(Fore.YELLOW + 'mocks enabled? {}'.format(self._enable_mock))
        # Import the ThunderBorg library, then configure and return the motors
        self._max_power_ratio = None
        self._import_thunderborg()
        if self._max_power_ratio is None: # this should have been set by the ThunderBorg code.
            raise ValueError('max_power_ratio not set.')

        # now import motors
        try:
            self._log.info('configuring motors...')
            self._port_motor = Motor(self._config, self._tb, self._message_bus, Orientation.PORT, level)
            self._stbd_motor = Motor(self._config, self._tb, self._message_bus, Orientation.STBD, level)
            self._port_motor.max_power_ratio = self._max_power_ratio
            self._stbd_motor.max_power_ratio = self._max_power_ratio

        except OSError as oe:
            self._log.error('failed to configure motors: {}'.format(oe))
            self._port_motor = None
            self._stbd_motor = None
            raise Exception('unable to instantiate ThunderBorg [3].')

        _odo_cfg = self._config['kros'].get('motor').get('odometry')
        _enable_odometry = _odo_cfg.get('enable_odometry')
        if _enable_odometry: # motor odometry configuration ....................
            self._reverse_encoder_orientation = _odo_cfg.get('reverse_encoder_orientation')
            self._log.info('reverse encoder orientation: {}'.format(self._reverse_encoder_orientation))
            # in case you wire something up backwards (we need this prior to the logger)
            self._reverse_motor_orientation   = _odo_cfg.get('reverse_motor_orientation')
            self._log.info('reverse motor orientation:   {}'.format(self._reverse_motor_orientation))
            # GPIO pins configured for A1, B1, A2 and B2
            self._motor_encoder_a1_port       = _odo_cfg.get('motor_encoder_a1_port') # default: 22
            self._log.info('motor encoder a1 port: {:d}'.format(self._motor_encoder_a1_port))
            self._motor_encoder_b1_port       = _odo_cfg.get('motor_encoder_b1_port') # default: 17
            self._log.info('motor encoder b1 port: {:d}'.format(self._motor_encoder_b1_port))
            self._motor_encoder_a2_stbd       = _odo_cfg.get('motor_encoder_a2_stbd') # default: 27
            self._log.info('motor encoder a2 stbd: {:d}'.format(self._motor_encoder_a2_stbd))
            self._motor_encoder_b2_stbd       = _odo_cfg.get('motor_encoder_b2_stbd') # default: 18
            self._log.info('motor encoder b2 stbd: {:d}'.format(self._motor_encoder_b2_stbd))
            # config pigpio's pi and name its callback thread (ex-API)
            try:
                self._pi = pigpio.pi()
                if self._pi is None:
                    raise Exception('unable to instantiate pigpio.pi().')
                elif self._pi._notify is None:
                    raise Exception('can\'t connect to pigpio daemon; did you start it?')
                self._pi._notify.name = 'pi.callback'
                self._log.info('pigpio version {}'.format(self._pi.get_pigpio_version()))
            except Exception as e:
                self._log.error('error importing and/or configuring Motor: {}'.format(e))
                traceback.print_exc(file=sys.stdout)
                sys.exit(1)
            # configure motor encoders...
            self._log.info('configuring motor encoders...')
            self._configure_encoder(self._port_motor, Orientation.PORT)
            self._configure_encoder(self._stbd_motor, Orientation.STBD)
        # end odometry configuration ...........................................
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _configure_encoder(self, motor, orientation):
        if self._reverse_encoder_orientation:
            if orientation is Orientation.PORT:
                orientation = Orientation.STBD
            else:
                orientation = Orientation.PORT
        if orientation is Orientation.PORT:
            _encoder_a = self._motor_encoder_a1_port
            _encoder_b = self._motor_encoder_b1_port
        elif orientation is Orientation.STBD:
            _encoder_a = self._motor_encoder_a2_stbd
            _encoder_b = self._motor_encoder_b2_stbd
        else:
            raise ValueError("unrecognised value for orientation.")
        motor.decoder = Decoder(self._pi, motor.orientation, _encoder_a, _encoder_b, motor._callback_step_count, self._log.level)
        if self._reverse_encoder_orientation:
            motor.decoder.set_reversed() 
        self._log.info('configured {} motor encoder on pin {} and {}.'.format(motor.orientation.name, _encoder_a, _encoder_b))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _import_thunderborg(self):
        if self._motors_enabled and not self._enable_mock:
            self._log.info('configure thunderborg & motors...')
            try:
                _thunderborg_address = self._config['kros'].get('motor').get('thunderborg_address')
                if self._i2c_scanner.has_address([_thunderborg_address]):
                    self._log.info('importing ThunderBorg at address 0x[:02X]...'.format(_thunderborg_address))
                    import hardware.ThunderBorg3 as ThunderBorg
                    self._log.info('successfully imported ThunderBorg.')
                else:
                    self._log.info('importing mock ThunderBorg...')
                    self._enable_mock = True # we default if no ThunderBorg found
                    import mock.thunderborg as ThunderBorg
                    self._log.info('successfully imported mock ThunderBorg.')

                self._tb = ThunderBorg.ThunderBorg(Level.INFO)  # create a new ThunderBorg object
                self._tb.Init()                       # set the board up (checks the board is connected)
                self._log.info('successfully instantiated ThunderBorg.')
                if not self._tb.foundChip:
                    boards = ThunderBorg.ScanForThunderBorg()
                    if len(boards) == 0:
                        self._log.error('No ThunderBorg found, check you are attached :)')
                    else:
                        self._log.error('No ThunderBorg at address %02X, but we did find boards:' % (self._tb.i2cAddress))
                        for board in boards:
                            self._log.info('    %02X (%d)' % (board, board))
                        self._log.error('If you need to change the I²C address change the setup line so it is correct, e.g. TB.i2cAddress = 0x{}'.format(
                                boards[0]))
                    raise Exception('unable to instantiate ThunderBorg [1].')
                self._tb.SetLedShowBattery(True)

                # initialise ThunderBorg ...........................
                self._log.debug('getting battery reading...')
                # get battery voltage to determine max motor power
                # could be: Makita 12V or 18V power tool battery, or 12V line supply
                voltage_in = self._tb.GetBatteryReading()
                if voltage_in is None:
                    raise OSError('cannot continue: cannot read battery voltage.')
                self._log.info('voltage in: {:>5.2f}V'.format(voltage_in))
        #       voltage_in = 20.5
                # maximum motor voltage
                voltage_out = 9.0
                self._log.info('voltage out: {:>5.2f}V'.format(voltage_out))
                if voltage_in < voltage_out:
                    raise OSError('cannot continue: battery voltage too low ({:>5.2f}V).'.format(voltage_in))
                # set the power limits
                if voltage_out > voltage_in:
                    self._max_power_ratio = 1.0
                else:
                    self._max_power_ratio = voltage_out / float(voltage_in)
                # convert float to ratio format
                self._log.info('battery level: {:>5.2f}V; motor voltage: {:>5.2f}V; maximum power ratio: {}'.format(voltage_in, voltage_out, \
                        str(Fraction(self._max_power_ratio).limit_denominator(max_denominator=20)).replace('/',':')))
                # flag we are successfully using the real ThunderBorg
                self._config['kros'].get('arguments')['using_mocks'] = False

            except OSError as e:
                if self._enable_mock:
                    self._log.info('using mock ThunderBorg.')
                    self._import_mock_thunderborg()
                else:
                    self._log.error('unable to import mock ThunderBorg: {}'.format(e))
                    traceback.print_exc(file=sys.stdout)
                    raise Exception('unable to instantiate ThunderBorg [2].')
            except Exception as e:
                if self._enable_mock:
                    self._log.info('using mock ThunderBorg.')
                    self._import_mock_thunderborg()
                else:
                    self._log.error('unable to import mock ThunderBorg: {}'.format(e))
                    traceback.print_exc(file=sys.stdout)
                    raise Exception('unable to instantiate ThunderBorg [2].')
        else:
            self._import_mock_thunderborg()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _import_mock_thunderborg(self):
        self._log.info('configure thunderborg & motors...')
        try:
            import mock.thunderborg as ThunderBorg
            self._log.info('successfully imported mock ThunderBorg.')
            self._tb = ThunderBorg.ThunderBorg(Level.WARN)  # create a new ThunderBorg object
#           self._tb.Init()                       # set the board up (checks the board is connected)
            self._log.info(Fore.YELLOW + 'successfully instantiated mock ThunderBorg.')
#           self._tb.SetLedShowBattery(True)
            _voltage_in  = 19.0
            _voltage_out = 9.0
            self._max_power_ratio = _voltage_out / float(_voltage_in)
        except OSError as e:
            if self._enable_mock:
                self._log.info('using mock ThunderBorg.')
                import mock.thunderborg as ThunderBorg
            else:
                self._log.error('unable to import ThunderBorg: {}'.format(e))
                traceback.print_exc(file=sys.stdout)
                raise Exception('unable to instantiate ThunderBorg [2].')
        except Exception as e:
            if self._enable_mock:
                self._log.info('using mock ThunderBorg.')
                import mock.thunderborg as ThunderBorg
            else:
                self._log.error('unable to import ThunderBorg: {}'.format(e))
                traceback.print_exc(file=sys.stdout)
                raise Exception('unable to instantiate ThunderBorg [2].')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def thunderborg(self):
        '''
        Temporary: do no use this brain.
        '''
        return self._tb

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_motor(self, orientation):
        if orientation is Orientation.PORT:
            return self._port_motor
        else:
            return self._stbd_motor

#EOF
