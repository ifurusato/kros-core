#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-19
# modified: 2020-09-19
#

import pytest
import sys, traceback
from colorama import init, Fore, Style
init()

from core.config_loader import ConfigLoader
from core.logger import Logger, Level
from core.rate import Rate
from hardware.analog_pot import AnalogPotentiometer

_log = Logger('pot-test', Level.INFO)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_pot():
    '''
    Tests reading the wiper of a potentiometer attached to a GPIO pin,
    where its other two connections are to Vcc and ground.
    '''
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

#   _in_min  = 29.0
#   _in_max  = 330.0
#   _out_min = 0.0
#   _out_max = 1.0
#   _apot = AnalogPotentiometer(_config, in_min=_in_min, in_max=_in_max, out_min=_out_min, out_max=_out_max, level=Level.INFO)

    _cfg = [ 0, 330, 0.0, 1.0 ]
    _apot = AnalogPotentiometer(_config, in_min=_cfg[0], in_max=_cfg[1], out_min=_cfg[2], out_max=_cfg[3], level=Level.INFO)
#   _apot = AnalogPotentiometer(_config, Level.DEBUG)

    _value = 0
    # start...
    _rate = Rate(20) # Hz
    i = 0
    while True:
#   for i in range(20):
        _value        = _apot.get_value()
        _scaled_value = _apot.get_scaled_value()
        _log.info('[{:d}] analog value: {:03d};'.format(i, _value) + Fore.GREEN + '\tscaled: {:>7.4f};'.format(_scaled_value))
        _rate.wait()
        i += 1
#   assert _value != 0

# main ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main(argv):

    try:
        test_pot()
    except KeyboardInterrupt:
        _log.info('caught Ctrl-C; exiting...')
    except Exception:
        _log.error('error starting potentiometer: {}'.format(traceback.format_exc()))

if __name__== "__main__":
    main(sys.argv[1:])

#EOF
