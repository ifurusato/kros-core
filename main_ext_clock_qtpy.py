# MicroPython External Clock for QT Py RP2040
# file: main.py
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-09-16
# modified: 2021-09-19
#
# This has options for generating a 50ms (20Hz) external clock or blinking the
# NeoPixel on a QT Py RP2040.
#
# Uses the Neopixel library downloadable from:
#
#    https://github.com/blaz-r/pi_pico_neopixel
#
# copy the 'neopixel.py' file to /pyboard/

from machine import Pin, Timer
from neopixel import Neopixel
import itertools
import utime

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# constants
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

BLACK    =  (  0,   0,   0)
RED      = (255,   0,   0)
ORANGE   = (255, 165,   0)
YELLOW   = (255, 150,   0)
GREEN    = (  0, 255,   0)
CYAN     = (  0, 255, 255)
BLUE     = (  0,   0, 255)
INDIGO   = ( 75,   0, 130)
VIOLET   = (138,  43, 226)
MAGENTA  = (255, 255,   0)
SKY_BLUE = ( 40,   0,  72)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# configure pins
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# external clock pin ("MO")
clock_pin = Pin(3, Pin.OUT)

# NeoPixel power pin 11
power_pin = Pin(11, Pin.OUT)
power_pin.value(1)

# NeoPixel pin 12
neopix = Neopixel(num_leds=1, state_machine=0, pin=12, mode="GRB")
neopix.brightness(108)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# functions
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def wheel(pos):
    '''
    Input a value 0 to 255 to get a color value.
    The colours are a transition r - g - b - back to r.
    '''
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def tick():
    global g_counter
    clock_pin.value(not clock_pin.value())
    # now some fluff
    _count = next(g_counter)
    if _count % 500 == 0.0:
        neopix.set_pixel(0, RED)
    elif _count % 50 == 0.0:
        neopix.set_pixel(0, CYAN)
    neopix.show()
    utime.sleep(0.01)
    neopix.set_pixel(0, BLACK)
    neopix.show()

def rgb_blink():
    for color in [RED, GREEN, BLUE]:
        neopix.set_pixel(0, color)
        neopix.show()
        utime.sleep(0.33)
    neopix.set_pixel(0, BLACK)
    neopix.show()
    utime.sleep(1.0)

def unicorns():
    for i in range(1):
        for j in range(255):
            neopix.set_pixel(0, wheel(j))
            neopix.show()
            utime.sleep(0.01)
    neopix.set_pixel(0, BLACK)
    neopix.show()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# execute
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

g_counter = itertools.count()

rgb_blink()

_ext_clock_timer = Timer(period=50, mode=Timer.PERIODIC, callback=lambda x: tick())

unicorns()

#EOF
