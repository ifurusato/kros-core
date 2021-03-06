#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# author:   Murray Altheim
# created:  2021-10-11
# modified: 2021-10-11
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#

from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MockRGBMatrix5x5(Component):
    '''
    This is a minimal mock of the Pimoroni RGB Matrix 5x5 board.

    :param level:      the logging level.
    :param address:    the I2C address (unused).
    '''
    def __init__(self, address=None, level=Level.INFO):
        self._log = Logger('mock-rgb5x5', level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'mock-rgb5x5'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def show(self):
        pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_pixel(self, x, y, r, g, b, brightness=1.0):
        self._log.debug('set pixel ({},{}): '.format(x, y)
            + Fore.RED   + '{}'.format(r) + Fore.CYAN + ', '
            + Fore.GREEN + '{}'.format(g) + Fore.CYAN + ', '
            + Fore.BLUE  + '{}'.format(b) + Fore.CYAN + ')')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_all(self, r, g, b, brightness=1.0):
        self._log.debug('set all pixels: ('
                + Fore.RED   + '{}'.format(r) + Fore.CYAN + ', '
                + Fore.GREEN + '{}'.format(g) + Fore.CYAN + ', '
                + Fore.BLUE  + '{}'.format(b) + Fore.CYAN + ')')

#EOF
