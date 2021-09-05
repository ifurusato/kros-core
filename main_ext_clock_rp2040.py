# MicroPython External Clock for Itsy Bitsy RP2040
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-26
# modified: 2021-09-06
#

from machine import Pin, Timer
import utime

_led = Pin(11, Pin.OUT)
_value = False

# display distinctive hello pattern
for i in range(16, 0, -1):
    _value = not _value
    _led.value(_value)
    utime.sleep(i / 24)
for j in range(0, 7):
    _value = not _value
    _led.value(_value)
    utime.sleep(0.1)

_led.value(False)

# define pin GPIO 9 on pin 7
_pin = Pin(7, Pin.OUT)
_timer = Timer(period=50, mode=Timer.PERIODIC, callback=lambda n: _pin.toggle())

while True:
    _value = not _value
    _led.value(_value)
    utime.sleep(1.0)

#EOF
