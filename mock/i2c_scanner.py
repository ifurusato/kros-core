#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-10-11
# modified: 2021-10-11
#

from colorama import init, Fore, Style
init()

from core.logger import Level, Logger

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MockI2CScanner(object):
    '''
    A mock of the I2CScanner class that scans the I²C bus, returning a list
    of devices.
    '''
    def __init__(self, config, level):
        super().__init__()
        self._log = Logger('i2cscan', level)
        self._log.debug('initialising...')
        self._config = config
        self._int_list = []
        self._hex_list = []
        try:
            from smbus2 import SMBus
            bus_number = 1  # 1 indicates /dev/i2c-1
            self._bus = SMBus(bus_number)
            self._log.info('ready.')
        except ImportError:
            from mock.i2cscanner import MockI2CScanner as I2CScanner
            self._log.warning('unable to initialise: this script requires smbus2. Will operate with mock.')
        except Exception as e:
            self._log.warning('error while initialising: {}'.format(e))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_hex_addresses(self):
        '''
        Returns a hexadecimal version of the list.
        '''
        return self._hex_list

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_int_addresses(self):
        '''
        Returns an integer version of the list.
        '''
        return self._int_list

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def has_address(self, addresses):
        '''
        Performs the address scan (if necessary) and returns true if a device
        is available at any of the specified int addresses, the argument a list
        of strings.
        '''
        for address in addresses:
            if address in self._int_list:
                return True
        return False

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def has_hex_address(self, addresses):
        '''
        Performs the address scan (if necessary) and returns true if a device
        is available at any of the specified hexadecimal addresses, the argument
        a list of strings.
        '''
        for address in addresses:
            if address in self._hex_list:
                return True
        return False

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _scan_addresses(self):
        '''
        Scans the bus and returns the available device addresses. After being
        called and populating the int and hex lists, this closes the connection
        to smbus.
        '''
        # nada
        return self._int_list

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_device_list(self):
        self._addrDict = dict(list(map(lambda x, y:(x,y), self.get_int_addresses(), self.get_hex_addresses())))
        for _address in self.get_int_addresses():
            _device_name = self.get_device_for_address(_address)
            self._log.info('found device at I²C address 0x{:02X}: '.format(_address) + Fore.YELLOW + '{}'.format(_device_name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_device_for_address(self, address):
        '''
        Returns the lookup device name from the device registry found in
        the YAML configuration.
        '''
        _device = self._config['devices'].get(address)
        return 'Unknown' if _device is None else _device

    # end class ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class DeviceNotFound(Exception):
    '''
    Thrown when an expected device cannot be found.
    '''
    pass

#EOF
