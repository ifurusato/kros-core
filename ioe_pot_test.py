#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-19
# modified: 2021-07-18
#

import pytest
import sys, traceback
from colorama import init, Fore, Style
init()

from core.config_loader import ConfigLoader
from core.logger import Level, Logger
from core.rate import Rate
from hardware.digital_pot import DigitalPotentiometer
from mock.pot_publisher import MockPotentiometer

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_ioe_potentiometer():

    _log = Logger("test-ioe-pot", Level.INFO)
    _log.info(Fore.RED + 'to kill type Ctrl-C')

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    _config = _loader.configure('config.yaml')

    try:
        _pot = DigitalPotentiometer(_config, Level.INFO)
    except Exception as e:
        _pot = MockPotentiometer(Level.INFO)
#   _pot.set_output_limits(0.00, 0.150)
    _pot.set_output_limits(-0.90, 0.90)

    _log.info('starting test...')
    _hz = 10
    _rate = Rate(_hz, Level.ERROR)
    while True:
#       _value = self.get_value()
#       self.set_rgb(_value)
#       _scaled_value = self.scale_value() # as float
        _scaled_value = _pot.get_scaled_value(True)
#       _scaled_value = math.floor(self.scale_value()) # as integer
        _log.info(Fore.YELLOW + 'scaled value: {:9.6f}'.format(_scaled_value))
        _rate.wait()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main(argv):

    try:
        test_ioe_potentiometer()
    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)

if __name__== "__main__":
    main(sys.argv[1:])

# prevent Python script from exiting abruptly
#signal.pause()

#EOF

