#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2021-06-26
#
# An enum of colors.
#

from enum import Enum

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Color(Enum):
    WHITE          = (  1, 255.0, 255.0, 255.0)
    LIGHT_GREY     = (  2, 192.0, 192.0, 192.0)
    GREY           = (  3, 128.0, 128.0, 128.0)
    DARK_GREY      = (  4, 64.0, 64.0, 64.0)
    VERY_DARK_GREY = (  5, 32.0, 32.0, 32.0)
    BLACK          = (  6, 0.0, 0.0, 0.0)
    LIGHT_RED      = (  7, 255.0, 128.0, 128.0)
    RED            = (  8, 255.0, 0.0, 0.0)
    DARK_RED       = (  9, 128.0, 0.0, 0.0)
    ORANGE         = ( 10, 255.0, 50.0, 0.0)
#   ORANGE         = ( 10, 255.0, 128.0, 0.0)
    YELLOW_GREEN   = ( 11, 180.0, 255.0, 0.0)
    LIGHT_GREEN    = ( 12, 128.0, 255.0, 128.0)
    GREEN          = ( 13, 0.0, 255.0, 0.0)
    DARK_GREEN     = ( 14, 0.0, 128.0, 0.0)
    LIGHT_BLUE     = ( 15, 128.0, 128.0, 255.0)
    BLUE           = ( 16, 0.0, 0.0, 255.0)
    DARK_BLUE      = ( 17, 0.0, 0.0, 128.0)
    LIGHT_CYAN     = ( 18, 128.0, 255.0, 255.0)
    CYAN           = ( 19, 0.0, 255.0, 255.0)
    DARK_CYAN      = ( 20, 0.0, 128.0, 128.0)
    LIGHT_MAGENTA  = ( 21, 255.0, 128.0, 255.0)
    MAGENTA        = ( 22, 255.0, 0.0, 255.0)
    FUCHSIA        = ( 22, 255.0, 0.0, 128.0)
    DARK_MAGENTA   = ( 23, 128.0, 0.0, 128.0)
    LIGHT_YELLOW   = ( 24, 255.0, 255.0, 128.0)
    PURPLE         = ( 25, 77.0, 26.0, 177.0)
#   YELLOW         = ( 25, 255.0, 208.0, 0.0)
    YELLOW         = ( 25, 255.0, 140.0, 0.0)
    DARK_YELLOW    = ( 27, 128.0, 128.0, 0.0)

    # ignore the first param since it's already set by __new__
    def __init__(self, num, red, green, blue):
        self._red = red
        self._green = green
        self._blue = blue

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def rgb(self):
        return [ self._red, self._green, self._blue ]

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def red(self):
        return self._red

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def green(self):
        return self._green

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def blue(self):
        return self._blue

#EOF
