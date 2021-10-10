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
    BROWN          = ( 10, 50.0, 42.0, 24.0)
    DARK_ORANGE    = ( 11, 255.0, 50.0, 0.0)
    ORANGE         = ( 12, 255.0, 96.0, 0.0)
    DARK_YELLOW    = ( 13, 128.0, 128.0, 0.0)
    YELLOW         = ( 14, 255.0, 140.0, 0.0)
    LIGHT_YELLOW   = ( 15, 255.0, 255.0, 128.0)
    YELLOW_GREEN   = ( 16, 180.0, 255.0, 0.0)
    LIGHT_GREEN    = ( 17, 128.0, 255.0, 64.0)
    GREEN          = ( 18, 0.0, 255.0, 0.0)
    DARK_GREEN     = ( 19, 0.0, 96.0, 0.0)
    TURQUOISE      = ( 20, 0.0, 160.0, 96.0)
    LIGHT_BLUE     = ( 21, 128.0, 128.0, 255.0)
    BLUE           = ( 22, 0.0, 0.0, 255.0)
    SKY_BLUE       = ( 23, 40.0, 128.0, 192.0)
    DARK_BLUE      = ( 24, 0.0, 0.0, 128.0)
    LIGHT_CYAN     = ( 25, 128.0, 255.0, 255.0)
    CYAN           = ( 26, 0.0, 255.0, 255.0)
    DARK_CYAN      = ( 27, 0.0, 128.0, 128.0)
    LIGHT_MAGENTA  = ( 28, 255.0, 128.0, 255.0)
    MAGENTA        = ( 29, 255.0, 0.0, 255.0)
    FUCHSIA        = ( 30, 255.0, 0.0, 128.0)
    DARK_MAGENTA   = ( 31, 128.0, 0.0, 128.0)
    PURPLE         = ( 32, 77.0, 26.0, 177.0)

    # ignore the first param since it's already set by __new__
    def __init__(self, num, red, green, blue):
        self._red = red
        self._green = green
        self._blue = blue

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def all_colors():
        return [ Color.WHITE, Color.LIGHT_GREY, Color.GREY, Color.DARK_GREY,
                 Color.VERY_DARK_GREY, Color.BLACK, Color.LIGHT_RED,
                 Color.RED, Color.DARK_RED, Color.BROWN, Color.DARK_ORANGE,
                 Color.ORANGE, Color.DARK_YELLOW, Color.YELLOW,
                 Color.LIGHT_YELLOW, Color.YELLOW_GREEN, Color.LIGHT_GREEN,
                 Color.GREEN, Color.DARK_GREEN, Color.TURQUOISE,
                 Color.LIGHT_BLUE, Color.BLUE, Color.SKY_BLUE,
                 Color.DARK_BLUE, Color.LIGHT_CYAN, Color.CYAN,
                 Color.DARK_CYAN, Color.LIGHT_MAGENTA, Color.MAGENTA,
                 Color.FUCHSIA, Color.DARK_MAGENTA, Color.PURPLE ]

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
