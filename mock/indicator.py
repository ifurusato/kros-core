#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-06-26
# modified: 2021-06-29
#

from core.logger import Level, Logger
from core.component import Component
from core.orient import Orientation
from mock.rgbmatrix import RgbMatrix, Color

# ..............................................................................
class Indicator(Component):

    def __init__(self, level=Level.INFO):
        self._log = Logger('indicator', level)
        Component.__init__(self, self._log)
        self._rgbmatrix = RgbMatrix(Level.INFO)
        self._log.info('ready.')

    # ..........................................................................
    def set_display_type(self, display_type):
        self._rgbmatrix.set_display_type(display_type)

    # ..........................................................................
    def enable(self):
        if not self.closed and not self.enabled:
            super().enable()
            self._rgbmatrix.enable()

    # ..........................................................................
    def disable(self):
        if self.enabled:
            super().disable()
            self._rgbmatrix.set_color(Color.BLACK)
            self._rgbmatrix.clear()
            self._rgbmatrix.disable()

    # ..........................................................................
    def close(self):
        '''
        Permanently close and disable the indicator.
        '''
        if not self.closed:
            super().close()
            self._rgbmatrix.close()

#EOF
