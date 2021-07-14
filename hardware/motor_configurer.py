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

from core.logger import Logger, Level
from core.i2c_scanner import I2CScanner
from core.orient import Orientation
from hardware.motors import Motors

# ..............................................................................
class MotorConfigurer():

    THUNDERBORG_ADDRESS = 0x15

    '''
    Configures either a ThunderBorg motor controller for a pair of motors. 
    If the ThunderBorg does not appear on the I²C bus the motors are mocked.

    :param config:       the application configuration
    :param message_bus:  the message bus handling event-laden messages
    :param level:        the logging level
    '''
    def __init__(self, config, message_bus, i2c_scanner, level=Level.INFO):
        self._log = Logger("mock-motor-conf", level)
        if config is None:
            raise ValueError('null configuration argument.')
        self._config = config
        self._message_bus = message_bus
        if not isinstance(i2c_scanner, I2CScanner):
            raise ValueError('expected I2CScanner, not {}.'.format(type(i2c_scanner)))
        self._i2c_scanner = i2c_scanner
        self._log.debug('getting battery reading...')
        # get battery voltage to determine max motor power (moved earlier in config)
        voltage_in = 19.0
        self._log.info('voltage in: {:>5.2f}V'.format(voltage_in))
        voltage_out = 9.0
        self._log.info('voltage out: {:>5.2f}V'.format(voltage_out))
        self._max_power_ratio = voltage_out / float(voltage_in)
        # convert float to ratio format
        self._log.info('battery level: {:>5.2f}V; motor voltage: {:>5.2f}V; maximum power ratio: {}'.format(voltage_in, voltage_out, \
                str(Fraction(self._max_power_ratio).limit_denominator(max_denominator=20)).replace('/',':')))
        # actually, for the mock just set it to 1:1
        self._max_power_ratio = 1.0
        # configure from command line argument properties
        _cfg = self._config['kros'].get('arguments')
        self._motors_enabled = _cfg.get('motors_enabled')
        self._log.info(Fore.YELLOW + 'motors enabled? {}'.format(self._motors_enabled))
        if not self._motors_enabled: # overrides _enable_mock
            self._enable_mock = True
        else:
            self._enable_mock = _cfg.get('mock_enabled')
        self._log.info(Fore.YELLOW + 'enabled mocks? {}'.format(self._enable_mock))

        # Import the ThunderBorg library, then configure and return the Motors.
        self._import_thunderborg()

        # now import motors
        try:
            self._log.info('configuring motors...')
            self._motors = Motors(self._config, self._tb, level=Level.INFO)
            self._motors.get_motor(Orientation.PORT).set_max_power_ratio(self._max_power_ratio)
            self._motors.get_motor(Orientation.STBD).set_max_power_ratio(self._max_power_ratio)
        except OSError as oe:
            self._log.error('failed to configure motors: {}'.format(oe))
            self._motors = None
#           sys.stderr = DevNull()
            raise Exception('unable to instantiate ThunderBorg [3].')
#           sys.exit(1)
        self._log.info('ready.')

    # ..........................................................................
    def _import_thunderborg(self):
        if self._motors_enabled and not self._enable_mock:
            self._log.info('configure thunderborg & motors...')
            try:
    
                _has_thunderborg = self._i2c_scanner.has_address([MotorConfigurer.THUNDERBORG_ADDRESS])
                if _has_thunderborg:
                    self._log.info('importing ThunderBorg...')
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
                        self._log.error('If you need to change the I²C address change the setup line so it is correct, e.g. TB.i2cAddress = 0x{}'.format(boards[0]))
                    raise Exception('unable to instantiate ThunderBorg [1].')
    #               sys.exit(1)
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
                # Setup the power limits
                if voltage_out > voltage_in:
                    _max_power_ratio = 1.0
                else:
                    _max_power_ratio = voltage_out / float(voltage_in)
                # convert float to ratio format
                self._log.info('battery level: {:>5.2f}V; motor voltage: {:>5.2f}V; maximum power ratio: {}'.format(voltage_in, voltage_out, \
                        str(Fraction(_max_power_ratio).limit_denominator(max_denominator=20)).replace('/',':')))
    
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
#                   sys.exit(1)
        else:
            self._import_mock_thunderborg()

    # ..........................................................................
    def _import_mock_thunderborg(self):
        self._log.info('configure thunderborg & motors...')
        try:
            import mock.thunderborg as ThunderBorg
            self._log.info('successfully imported mock ThunderBorg.')
            self._tb = ThunderBorg.ThunderBorg(Level.WARN)  # create a new ThunderBorg object
#           self._tb.Init()                       # set the board up (checks the board is connected)
            self._log.info(Fore.YELLOW + 'successfully instantiated mock ThunderBorg.')
#           self._tb.SetLedShowBattery(True)
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
#               sys.exit(1)

    # ..........................................................................
    def get_motors(self):
        '''
        Return the configured motors.
        '''
        return self._motors
            
#EOF
