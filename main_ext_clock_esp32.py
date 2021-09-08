# MicroPython External Clock for TinyPICO
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-26
# modified: 2021-08-27
#
from machine import Timer
from machine import Pin
from machine import SPI
#from machine import PWM
import tinypico as TinyPICO
from dotstar import DotStar
import time, gc

# define constant colours on the Dotstar
COLOR_GREEN     = ( 0, 64, 0, 1 )
COLOR_TURQUOISE = ( 0, 10, 7, 1 )
COLOR_RED       = ( 64, 0, 0, 1 )
COLOR_YELLOW    = ( 64, 64, 0, 1 )
COLOR_BLACK     = ( 0, 0, 0, 10 )

# configure SPI for controlling the DotStar
# use software SPI as the pins used are not hardware SPI pins
spi = SPI(sck=Pin(TinyPICO.DOTSTAR_CLK), mosi=Pin(TinyPICO.DOTSTAR_DATA), miso=Pin(TinyPICO.SPI_MISO)) # create a DotStar instance
dotstar = DotStar(spi, 1, brightness = 0.5)    # just one DotStar, half brightness
TinyPICO.set_dotstar_power(True)               # turn on the power to the DotStar

# test RAM, flash green 3x if okay, flash red 3x otherwise
def check_ram():
    gc.collect()
    ram = gc.mem_free()
    col = COLOR_GREEN if ram > 4000000 else COLOR_RED
    for i in range (3):
        dotstar[0] = col
        time.sleep_ms(150)
        dotstar[0] = COLOR_BLACK
        time.sleep_ms(50)
    time.sleep_ms(250)

# check the RAM
check_ram()

# signal readiness ...............................

for j in range(0, 3):
    dotstar[0] = COLOR_YELLOW
    time.sleep_ms(333)
    dotstar[0] = COLOR_BLACK
    time.sleep_ms(333)

# now the raison d'etre ..........................

_pin = Pin(4, Pin.OUT)

def tick():
    global _pin
    if _pin.value():
        _pin.value(0)
    else:
        _pin.value(1)

# some implementations have Pin.toggle(), some don't!
_timer = Timer(1)
_timer.init(period=50, mode=Timer.PERIODIC, callback=lambda n: tick())
#_timer.init(period=50, mode=Timer.PERIODIC, callback=lambda n: _pin.toggle())
#_pwm = PWM(_pin, freq=200, duty_u16=32767)

# health ping ....................................

while True:
    for j in range(0, 3):
        dotstar[0] = COLOR_TURQUOISE
        time.sleep_ms(5)
        dotstar[0] = COLOR_BLACK
        time.sleep_ms(2995)

#EOF
