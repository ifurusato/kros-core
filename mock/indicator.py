#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import time
from colorama import init, Fore, Style
init()

from core.logger import Level, Logger
from core.orient import Orientation
from mock.rgbmatrix import RgbMatrix, Color, DisplayType, WipeDirection

# ..............................................................................
class Indicator(object):

    def __init__(self, level):
        self._log = Logger('indicator', level)
        self._rgbmatrix = RgbMatrix(Level.INFO)
        self._enabled = False
        self._closed  = False
        self._log.info('ready.')

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def set_display_type(self, display_type):
        self._rgbmatrix.set_display_type(display_type)

    # ..........................................................................
#   def display(self, display_type):
#       self._log.info('displaying {}...'.format(display_type.name))
#       self._rgbmatrix.set_display_type(display_type)
#       self._rgbmatrix.enable()
#       time.sleep(2.0)
#       self._rgbmatrix.disable()
#       count = 0
#   #       while not self._rgbmatrix.is_disabled():
#       while self._enabled:
#           count += 1
#           if count > 5:
#               raise Exception('timeout waiting to disable rgbmatrix thread for {}.'.format(display_type.name))
#           time.sleep(1.0)
#       self._rgbmatrix.set_color(Color.BLACK)
#       self._log.info('{} complete.'.format(display_type.name))

#   # ..........................................................................
#   def wipe(self):
#       self._rgbmatrix.enable()
#       _port_rgbmatrix = self._rgbmatrix.get_rgbmatrix(Orientation.PORT)
#       _stbd_rgbmatrix = self._rgbmatrix.get_rgbmatrix(Orientation.STBD)
#       while self._enabled:
#           for c in [ Color.RED, Color.GREEN, Color.BLUE ]:
#               self._rgbmatrix.set_wipe_color(c)
#               self._rgbmatrix._wipe_vertical(_port_rgbmatrix, WipeDirection.DOWN)
#               self._rgbmatrix._wipe_vertical(_stbd_rgbmatrix, WipeDirection.DOWN)

    # ..........................................................................
    def enable(self):
        if not self._closed:
            if self._enabled:
                self._log.warning('already enabled.')
            else:
#               super().enable()
                self._enabled = True
                self._rgbmatrix.enable()
#               self._execute()
                self._log.info('enabled.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
#           super().disable()
            self._enabled = False
            self._rgbmatrix.set_color(Color.BLACK)
            self._rgbmatrix.clear()
            self._rgbmatrix.disable()
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def close(self):
        '''
        Permanently close and disable the message bus.
        '''
        if not self._closed:
            self.disable()
#           super().close()
            self._rgbmatrix.close()
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.info('already closed.')

#EOF
