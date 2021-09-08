#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-30
# modified: 2020-05-24
#
# This tests the two oblique infrared sensors of the KR01's Integrated Front
# Sensor (IFS). Its signals are returned via a Pimoroni IO Expander Breakout
# Garden board, an I²C-based microcontroller. This converts the two raw signals
# into centimeters as well as a ratio between the two of them, displaying this
# as a percentage across two 11x7 LED Matrix displays. This provides a visual
# indication of the relative distance between any objects sensed by the port
# and starboard sensors.
#

import pytest
import time, itertools, traceback
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from core.message_bus import MessageBus
from core.orient import Orientation
from core.message_factory import MessageFactory
from core.ranger import Ranger
from hardware.i2c_scanner import I2CScanner
from hardware.io_expander import IoExpander
from hardware.ifs import IntegratedFrontSensor
from hardware.matrix import Matrices
from hardware.rgbmatrix import RgbMatrix

# ..............................................................................
@pytest.mark.unit
def test_oblique():
    '''
    Test the basic functionality of the IO Expander's connections to the IR
    and bumper sensors.
    '''
    _log = Logger("test-ioe", log_to_file=False, level=Level.INFO)

    # read YAML configuration
    _loader = ConfigLoader(level=Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _log.info('creating message bus...')
    _message_bus = MessageBus(_config, Level.INFO)
    _log.info('creating message factory...')
    _message_factory = MessageFactory(_message_bus, Level.INFO)

    _ioe = IoExpander(_config, Level.INFO)
    _ioe.enable()
    _ifs = IntegratedFrontSensor(_config, _message_bus, _message_factory, level=Level.INFO)
    _ifs.enable()

    _ranger   = Ranger(-1.0, 1.0, 0, 100)
    _port_ranger = Ranger(0.0, 255.0, 0.0, -1.0)
    _stbd_ranger = Ranger(0.0, 255.0, 0.0, -1.0)

    _i2c_scanner = I2CScanner(_config, Level.DEBUG)
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
        _matrices = Matrices(_enable_port_11x7, _enable_stbd_11x7, Level.INFO)
    elif _use_5x5:
        _matrices = RgbMatrix(_enable_port_5x5, _enable_stbd_5x5, Level.INFO)
    else:
         raise Exception('could not find suitable pair of displays.')

    # we have ten columns and 25.5 is 10% of 255, but we want a wide deadband
    _tolerance = 30.0
    try:
        _counter = itertools.count()
        while True:
            _count = next(_counter)
            _port_raw = _ioe.get_port_ir_value()
            _stbd_raw = _ioe.get_stbd_ir_value()

            _port_pc  = _port_raw / 255.0
            _stbd_pc  = _stbd_raw / 255.0
            _ratio    = _port_pc - _stbd_pc

            _raw_diff = _port_raw - _stbd_raw

            _out_port = _port_ranger.convert(_port_raw)
            _out_stbd = _stbd_ranger.convert(_stbd_raw)

            _percent  = _ranger.convert(_ratio)

            _port_cm  = _ifs.convert_to_distance(_port_raw)
            _stbd_cm  = _ifs.convert_to_distance(_stbd_raw)
            if _percent <= 50:
                _port_em = Style.NORMAL
                _stbd_em = Style.BRIGHT
            else:
                _port_em = Style.BRIGHT
                _stbd_em = Style.NORMAL

            if compare(_port_raw, _stbd_raw, _tolerance):
                _matrices.clear_all()
                _log.info(Fore.RED   + _port_em + 'IR {:6.3f} / {:6.3f}cm\t'.format(_port_raw, _port_cm)
                        + Fore.GREEN + _stbd_em + '{:6.3f} / {:6.3f}cm\t'.format(_stbd_raw, _stbd_cm)
                        + Fore.WHITE + Style.NORMAL + 'ratio: SAME')
            else:
                _matrices.percent(_percent)
                _log.info(Fore.RED   + _port_em + 'IR {:6.3f} / {:6.3f}cm\t'.format(_port_raw, _port_cm)
                        + Fore.GREEN + _stbd_em + '{:6.3f} / {:6.3f}cm\t'.format(_stbd_raw, _stbd_cm)
                        + Fore.WHITE + Style.NORMAL + 'ratio: {:4.1f}\t'.format(_ratio)
                        + Fore.RED + 'port: {:4.1f}\t'.format(_out_port)
                        + Fore.GREEN + 'stbd: {:4.1f}\t'.format(_out_stbd))
    #                   + Fore.BLUE  + 'percent: {:4.1f}%'.format(_percent))

            _log.info('count={:d}\n'.format(_count))
            time.sleep(0.33)

    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error testing ifs: {}\n{}'.format(e, traceback.format_exc()) + Style.RESET_ALL)
    finally:
        _matrices.clear_all()

def compare(a, b, tol):
#   print('> compare {} with {}'.format(a,b))
    return abs(a-b) < tol

# ..............................................................................
def main():
    test_oblique()

if __name__== "__main__":
    main()

#EOF
