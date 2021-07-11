#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:  altheim
# created: 2020-02-14
#
#  Scans the I²C bus, printing a list of devices.
#

from core.logger import Level, Logger
from core.config_loader import ConfigLoader
from core.i2c_scanner import I2CScanner

def main():

    _level = Level.INFO
    _log = Logger('main', _level)

    # read YAML configuration
    _config = ConfigLoader().configure()
    _log.info('scanning for I2C devices...')
    _scanner = I2CScanner(_config, Level.INFO)
    _scanner.print_device_list()

    _log.info('complete.')

if __name__== "__main__":
    main()

#EOF

