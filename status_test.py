#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.

# author:   Murray Altheim
# created:  2020-01-17
# modified: 2021-10-19
#
# This tests the Status task, which turns on and off the status LED.
#

import pytest
import time
from colorama import init, Fore, Style
init()

from core.config_loader import ConfigLoader
from core.logger import Level
from hardware.status import Status

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_status():

    _status = None
    try:

        # read YAML configuration
        _config = ConfigLoader(Level.INFO).configure()

        _status = Status(_config, Level.INFO)

    #   _status.blink(True)
    #   for i in range(5):
    #       print(Fore.CYAN + "blinking...")
    #       time.sleep(1)
    #   _status.blink(False)

        print(Fore.CYAN + 'status task running...' + Style.RESET_ALL)

        for i in range(10):
            _status.enable()
            time.sleep(0.5)
            _status.disable()
            time.sleep(0.5)

    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught: interrupted.')
    finally:
        if _status:
            _status.close()
        print(Fore.CYAN + 'status task complete.' + Style.RESET_ALL)


# main ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():
    test_status()

if __name__== "__main__":
    main()

#EOF
