# TinyPICO Utilities
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-26
# modified: 2021-09-13
#
# This is a bit of a hodge-podge because it's attempting to support both the
# TinyPICO (ESP32) and the Itsy Bitsy RP2040 rather than creating two separate
# files.
#
# The Itsy Bitsy RP2040 uses the Neopixel library downloadable from:
#
#    https://github.com/blaz-r/pi_pico_neopixel
#

from machine import Pin
from machine import SPI
import time

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                 INITIALISE
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

TINY_PICO        = False
ITSYBITSY_RP2040 = True

_dotstar = None
_neopix  = None

if TINY_PICO:

    import tinypico as TinyPICO
    from dotstar import DotStar
    import gc

    # configure SPI for controlling the DotStar
    # uses software SPI as the pins used are not hardware SPI pins
    spi = SPI(sck=Pin(TinyPICO.DOTSTAR_CLK), mosi=Pin(TinyPICO.DOTSTAR_DATA), miso=Pin(TinyPICO.SPI_MISO)) # create a DotStar instance
    _dotstar = DotStar(spi, 1, brightness = 0.5)    # just one DotStar, half brightness
    TinyPICO.set_dotstar_power(True)               # turn on the power to the DotStar

if ITSYBITSY_RP2040:
#    global _red_led

    from neopixel import Neopixel

    # board red LED
#    _red_led = Pin(11, Pin.OUT)

    # NeoPixel power pin 16
    power_pin = Pin(16, Pin.OUT)
    power_pin.value(1)
    # NeoPixel pin 17
    _neopix = Neopixel(num_leds=1, state_machine=0, pin=17, mode="GRB") # why GRB?
    _neopix.brightness(108)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                  CONSTANTS
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

if TINY_PICO:

    # define constant colours on the Dotstar ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    COLOR_BLACK        = (  0,  0,  0, 10 )
    COLOR_RED          = ( 64,  0,  0,  1 )
    COLOR_DARK_ORANGE  = (  6,  2,  0,  1 )
    COLOR_ORANGE       = ( 32,  8,  0,  1 )
    COLOR_YELLOW       = ( 64, 64,  0,  1 )
    COLOR_APPLE_GREEN  = ( 32, 84,  0,  1 )
    COLOR_GREEN        = (  0, 64,  0,  1 )
    COLOR_BLUE         = (  0,  0, 64,  1 )
    COLOR_TURQUOISE    = (  0, 10,  7,  1 )
    COLOR_SKY_BLUE     = (  4, 12, 50,  1 )
    COLOR_CYAN         = (  0, 64, 64,  1 )
    COLOR_MAGENTA      = ( 64,  0, 64,  1 )
    COLOR_PURPLE       = (  7,  0,  3,  1 )
    COLOR_DARK_MAGENTA = ( 10,  0, 10,  1 )
    COLOR_WHITE        = ( 64, 64, 64,  1 )

if ITSYBITSY_RP2040:

    # define constant colours on the NeoPixel ┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    COLOR_BLACK        = (  0,  0,  0 )
    COLOR_RED          = ( 64,  0,  0 )
    COLOR_DARK_ORANGE  = (  6,  2,  0 )
    COLOR_ORANGE       = ( 32,  8,  0 )
    COLOR_YELLOW       = ( 64, 64,  0 )
    COLOR_APPLE_GREEN  = ( 32, 84,  0 )
    COLOR_GREEN        = (  0, 64,  0 )
    COLOR_BLUE         = (  0,  0, 64 )
    COLOR_TURQUOISE    = (  0, 10,  7 )
    COLOR_SKY_BLUE     = (  4, 12, 50 )
    COLOR_CYAN         = (  0, 64, 64 )
    COLOR_MAGENTA      = ( 64,  0, 64 )
    COLOR_PURPLE       = (  7,  0,  3 )
    COLOR_DARK_MAGENTA = ( 10,  0, 10 )
    COLOR_WHITE        = ( 64, 64, 64 )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                   FUNCTIONS
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

def red_led(state):
    pass
#    global _red_led
#    if TINY_PICO:
#        # no blinkable LED on TinyPICO
#        _dotstar[0] = COLOR_RED if state == 1 else COLOR_BLACK
#    if ITSYBITSY_RP2040:
#        _red_led.value(state)

def rgb_led(color):
    global _dotstar, _neopix
    if TINY_PICO:
        _dotstar[0] = color
    elif ITSYBITSY_RP2040:
        _neopix.set_pixel(0, color)
        _neopix.show()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def check_ram():
    '''
    Tests RAM, flash green 3x if okay, flash red 3x otherwise.
    '''
    gc.collect()
    ram = gc.mem_free()
    col = COLOR_GREEN if ram > 4000000 else COLOR_RED
    for i in range (3):
        rgb_led(col)
        time.sleep_ms(50)
        rgb_led(COLOR_BLACK)
        time.sleep_ms(50)
    time.sleep_ms(200)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def rainbow(pos):
    '''
    Input a value 0 to 255 to get a color value.
    The colours are a transition r - g - b - back to r.
    '''
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    elif pos < 85:
        return (int(pos * 3), int(255 - pos * 3), 0)
    elif pos < 170:
        pos -= 85
        return (int(255 - pos * 3), 0, int(pos * 3))
    else:
        pos -= 170
        return (0, int(pos * 3), int(255 - pos * 3))

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def unicorn(count):
    '''
    Unicorns on the RGB LED.
    '''
    for i in range(count):
        for i in range(255):
            r,g,b = rainbow(i)
            rgb_led((r, g, b, 0.5))
            time.sleep(0.001)
    rgb_led(COLOR_BLACK)
    time.sleep_ms(50)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def ready():
    '''
    Signal readiness.
    '''
    _value = False
    for i in range(3):
        for j in range(33, 3, -1):
            _value = not _value
            red_led(1 if _value else 0)
            time.sleep_ms(j)
        red_led(0)
        time.sleep_ms(100)
    red_led(0)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def error():
    '''
    Signal an error.
    '''
    print('error.')
    for i in range(15): # blinks for 30 seconds
        rgb_led(COLOR_RED)
        time.sleep_ms(500)
        rgb_led(COLOR_BLACK)
        time.sleep_ms(1500)
    red_led(1)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                   EXECUTE
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

if TINY_PICO:
    check_ram()

unicorn(3)

# signal readiness...
#ready()

#EOF
