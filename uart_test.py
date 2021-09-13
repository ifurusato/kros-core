#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-09-10
# modified: 2021-09-13
#

import serial
import sys, time, traceback
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.orient import Orientation

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():

    _log = Logger('test', Level.INFO)
    _start_time = dt.now()

    _port = '/dev/serial0'
#   _baud_rate = 4800
#   _baud_rate = 9600
    _baud_rate = 19200

    try:
        _log.info('starting...\t' + Fore.YELLOW + 'type Ctrl-C to exit.')
        uart = serial.Serial(port=_port, baudrate=_baud_rate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE) # timeout=1)
        while True:
            try:
#               with serial.Serial(_port, _baud_rate, timeout=3) as uart:
#               _bytes = uart.readline() # read until '\n' terminated line
                _bytes = uart.read_until() # read until '\n' terminated line
                if len(_bytes) > 1:
                    _data = _bytes.decode('UTF-8')
                    if len(_data) == 5:
                        _label = _data.strip()
                        _orientation = Orientation.from_label(_label)
                        if _orientation:
                            _log.info('orientation:\t' + Fore.YELLOW + '{} ({})'.format(_orientation.name, _orientation.label))
                        else:
                            _log.warning('unmatched: \'{}\'; ({:d} chars)'.format(_data, len(_data)))
                    else:
                        _log.warning('errant data \'{}\'; type: \'{}\'; length: {:d} chars.'.format(_data, type(_data), len(_data)))
                time.sleep(0.1)
            except UnicodeDecodeError as ude:
                _log.error(Fore.BLACK + 'UnicodeDecodeError: {} (ignoring)'.format(ude))
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
