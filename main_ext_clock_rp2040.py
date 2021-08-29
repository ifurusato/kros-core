# MicroPython External Clock for Itsy Bitsy RP2040
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-25
# modified: 2021-08-27
#

from machine import Pin, Timer
import utime

# display distinctive hello pattern ........................

_led = Pin(11, Pin.OUT)
for i in range(16, 0, -1):
    _led.toggle()
    utime.sleep(i / 24)
for j in range(0, 7):
    _led.toggle()
    utime.sleep(0.1)
_led.off()

# define GPIO 9 on pin 7 and start Timer ...................

_pin = Pin(7, Pin.OUT)
_timer = Timer(period=50, mode=Timer.PERIODIC, callback=lambda n: _pin.toggle())

#EOF
