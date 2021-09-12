#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-09-10
# modified: 2021-09-10
#

import serial
import sys, time, traceback
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():

    _log = Logger('test', Level.INFO)
    _start_time = dt.now()
#   _baud_rate = 4800
    _baud_rate = 19200

    try:

        _log.info('🌼 starting...\t' + Fore.YELLOW + 'type Ctrl-C to exit.')
        _port = '/dev/serial0'
#       _baud_rate = 9600
        uart = serial.Serial(port=_port, baudrate=_baud_rate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE) # timeout=1)
        while True:
            try:
#               with serial.Serial(_port, _baud_rate, timeout=3) as uart:
#               _bytes = uart.readline() # read until '\n' terminated line
                _bytes = uart.read_until() # read until '\n' terminated line
                _log.info('🌼 a. read {:d} of type {}'.format(len(_bytes), type(_bytes)))
                if len(_bytes) > 1:
                    _data = _bytes.decode('UTF-8')
                    _log.info('🌼 b. _data TYPE: {}'.format(type(_data)))
                    _log.info('🌼 c. _data: {}'.format(_data))
                time.sleep(0.1)

            except UnicodeDecodeError as ude:
                _log.error('UnicodeDecodeError: {} (ignoring)'.format(ude))

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
    except Exception as e:
        _log.error('{} encountered, exiting: {}'.format(type(e), e))
        traceback.print_exc(file=sys.stdout)
    finally:
        _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
        _log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))

if __name__== "__main__":
    main()

#EOF
