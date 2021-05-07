#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021 by Murray Altheim. All rights reserved. This file is part
# of the K-Series Robot Operating System project, released under the MIT
# License. Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-05-01
# modified: 2021-05-07
#
# This script usea a PAA5100JE Near Optical Flow Sensor to measure movement
# over the ground, optionally indicating direction via a 5x5 RGB matrix display.
#

import sys, time, enum, traceback
try:
    from pmw3901 import PAA5100, BG_CS_FRONT_BCM, BG_CS_BACK_BCM
#   from pmw3901 import PMW3901 as PAA5100, BG_CS_FRONT_BCM, BG_CS_BACK_BCM
except ImportError:
    sys.exit("This script requires the pmw3901 module\nInstall with: pip3 install --user pmw3901")

RGBMATRIX_AVAILABLE = False
try:
    from rgbmatrix5x5 import RGBMatrix5x5
    RGBMATRIX_AVAILABLE = True
except ImportError:
    sys.exit("This script requires the rgbmatrix5x5 module\nInstall with: pip3 install --user rgbmatrix5x5")

# The constant used to convert ticks to distance over a specified surface. Set
# this to an average value measured over 1 meter of travel on that surface.
TICKS_PER_METER = 11115

# ..............................................................................
class CompassIndicator(object):
    '''
    Uses an 5x5 RGB matrix display as a direction indicator.
    '''
    def __init__(self):
        self._rgbmatrix = RGBMatrix5x5()
        self._rgbmatrix.set_clear_on_exit()
        self._rgbmatrix.set_brightness(0.8)

    # ..........................................................................
    def clear(self):
        '''
        Sets the indicator to black (off).
        '''
        self._rgbmatrix.set_all(*Color.BLACK.rgb)
        self._rgbmatrix.show()

    # ..........................................................................
    def set(self, direction, mode):
        '''
        Set the indicator for the given Direction with a mode as either
        enabled (True) or diabled (False).
        '''
        if direction is Direction.FORE:
            _color  = Color.CYAN if mode else Color.BLACK
            _pixels = [[4, 1], [4, 2], [4, 3], [3, 2]]
        elif direction is Direction.AFT:
            _color  = Color.YELLOW if mode else Color.BLACK
            _pixels = [[0, 1], [0, 2], [0, 3], [1, 2]]
        elif direction is Direction.PORT:
            _color  = Color.RED if mode else Color.BLACK
            _pixels = [[1, 4], [2, 4], [3, 4], [2, 3]]
        elif direction is Direction.STBD:
            _color  = Color.GREEN if mode else Color.BLACK
            _pixels = [[1, 0], [2, 0], [3, 0], [2, 1]]
        else:
            _color  = Color.WHITE if mode else Color.BLACK
            _pixels = [[1, 1], [2, 2], [3, 3], [1, 3], [3, 1]] # smaller cross
#           _pixels = [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4], [0, 4], [1, 3], [3, 1], [4, 0]] # larger cross
        for x, y in _pixels:
            self._rgbmatrix.set_pixel(x, y, *_color.rgb)
        self._rgbmatrix.show()

# ..............................................................................
class NearOpticalFlowSensor(object):
    '''
    A simple wrapper around the PMW3901/PAA5100 library providing some very
    basic configuration. While the sensor can be mounted in a different
    configuration, by default the X coordinate is side-to-side (PORT-STBD), and
    the Y coordinate is fore-to-back, FORE-AFT. So the robot moving forward will
    see the Y coordinate increase, moving left (to port) likewise an increase.

    :param spi_slot:  optional value of 'front' or 'back' for the Breakout Garden's SPI slot; default is 'front'.
    :param rotation:  optional value for device rotation of 0, 90, 180 or 270 degrees; default is 0.
    '''
    def __init__(self, spi_slot='front', rotation=0):
        self._paa5100je = PAA5100(spi_port=0, spi_cs=1, spi_cs_gpio=BG_CS_FRONT_BCM if spi_slot == 'front' else BG_CS_BACK_BCM)
        self._paa5100je.set_rotation(rotation)

    def get_motion(self):
        return self._paa5100je.get_motion()

# ..............................................................................
class Direction(enum.Enum):
    NONE = 0
    FORE = 1
    AFT  = 2
    PORT = 3
    STBD = 4

# ..............................................................................
class Color(enum.Enum):
    WHITE          = (  1, 255.0, 255.0, 255.0)
    BLACK          = (  6,   0.0,   0.0,   0.0)
    RED            = (  8, 255.0,   0.0,   0.0)
    GREEN          = ( 13,   0.0, 255.0,   0.0)
    BLUE           = ( 16,   0.0,   0.0, 255.0)
    YELLOW         = ( 25, 255.0, 180.0,   0.0)
    MAGENTA        = ( 22, 255.0,   0.0, 255.0)
    CYAN           = ( 19,   0.0, 255.0, 255.0)

    # ignore the first param since it's already set by __new__
    def __init__(self, num, red, green, blue):
        self._red   = red
        self._green = green
        self._blue  = blue

    @property
    def rgb(self):
        '''
        Return a tuple of red, green, blue.
        '''
        return self._red, self._green, self._blue

# main .........................................................................

def main(argv):

    try:

        print("""paa5100je_test.py - Detect flow/motion in front of the
PAA5100JE sensor, displaying the direction on an RGBMatrix5x5 display.

Press Ctrl+C to exit!
""")

        _indicator = None
        if RGBMATRIX_AVAILABLE:
            _indicator = CompassIndicator()

        _nofs = NearOpticalFlowSensor()

        tx = 0
        ty = 0
        x_direction = None
        y_direction = None

        while True:

            if _indicator:
                _indicator.clear()
            try:
                x, y = _nofs.get_motion()
            except RuntimeError as e:
                continue

            tx += x
            ty += y
            if x == 0:
                x_direction = Direction.NONE
            elif x < 0:
                x_direction = Direction.PORT
            else:
                x_direction = Direction.STBD
            if y == 0:
                y_direction = Direction.NONE
            elif y < 0:
                y_direction = Direction.AFT
            else:
                y_direction = Direction.FORE

            if _indicator:
                if x_direction is Direction.NONE and y_direction is Direction.NONE:
                    _indicator.set(Direction.NONE, True)
                else:
                    _indicator.set(x_direction, True)
                    _indicator.set(y_direction, True)

            x_distance_m = tx / TICKS_PER_METER
            y_distance_m = ty / TICKS_PER_METER

            print("relative: x {:03d} y {:03d} | absolute: x {:03d} y {:03d}; Y distance: {:5.2f}m".format(x, y, tx, ty, y_distance_m))
            time.sleep(0.1)

    except KeyboardInterrupt:
        print('caught Ctrl-C; exiting...')
    except Exception as e:
        print('execution error: {}\n{}'.format(e, traceback.format_exc()))

# call main ....................................................................

if __name__== "__main__":
    main(sys.argv[1:])

#EOF
