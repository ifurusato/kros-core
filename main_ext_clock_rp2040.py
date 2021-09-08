# MicroPython External Clock for Itsy Bitsy RP2040
# file: main.py
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-26
# modified: 2021-09-08
#
# This has options for generating a 50ms (20Hz) external clock or blinking the
# red LED as well as various display options for the NeoPixel on an Itsy Bitsy
# RP2040.
#
# Uses the Neopixel library downloadable from:
#
#    https://github.com/blaz-r/pi_pico_neopixel
#
# copy the 'neopixel.py' file to /pyboard/

from machine import Pin, Timer
from neopixel import Neopixel
import utime

# if True generate 50ms external clock pulse
EXT_CLOCK = True
# elif True blink red LED
BLINK     = False

# if True display unicorn 
UNICORN   = False
# otherwise simple color cycling
CYCLE     = False
# otherwise just blink NeoPixel

BLACK        = (  0,   0,   0)
PURPLE       = ( 40,   0,  72)

RED          = (255,   0,   0)
ORANGE       = (255, 165,   0)
YELLOW       = (255, 150,   0)
GREEN        = (  0, 255,   0)
CYAN         = (  0, 255, 255)
BLUE         = (  0,   0, 255)
INDIGO       = ( 75,   0, 130)
VIOLET       = (138,  43, 226)
MAGENTA      = (255, 255,   0)
COLORS = [ RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, INDIGO, VIOLET, MAGENTA ]

# configure NeoPixel ..................................................

# NeoPixel power pin 16
p16 = Pin(16, Pin.OUT)
p16.value(1)
# NeoPixel pin 17
np17 = Neopixel(num_leds=10, state_machine=0, pin=17, mode="RGB")
np17.brightness(108)

# toggle red LED using hardware Timer ................................

# red LED
_led  = Pin(11, Pin.OUT)
# define pin GPIO 9 on pin 7
_pin7 = Pin(7, Pin.OUT)

def toggle_led():
    _led.value(not _led.value())

if EXT_CLOCK:
    _timer = Timer(period=50, mode=Timer.PERIODIC, callback=lambda n: _pin7.toggle())
elif BLINK:
    _timer = Timer(freq=1, mode=Timer.PERIODIC, callback=lambda n: toggle_led())

# cycle NeoPixel through colors ......................................

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

# execute ............................................................

if UNICORN:
    while True:
        for i in range(255):
            np17.set_pixel(0, wheel(i))
            np17.show()
            utime.sleep(0.01)
elif CYCLE:
    while True:
        for i in range(len(COLORS)):
            np17.set_pixel(0, COLORS[i])
            np17.show()
            utime.sleep(1.0)
else:
    while True:
        np17.set_pixel(0, PURPLE)
        np17.show()
        utime.sleep(0.01)
        np17.set_pixel(0, BLACK)
        np17.show()
        utime.sleep(1.0)

#EOF
