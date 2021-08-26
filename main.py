# MicroPython external clock script
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-25
# modified: 2021-08-26
#

from machine import Pin, Timer
gpio6 = Pin(7, Pin.OUT)
tim = Timer()
def tick(timer):
    global gpio6
    gpio6.toggle()
# 50ms = 20Hz, 5ms = 200Hz
tim.init(period=5, mode=Timer.PERIODIC, callback=tick)

#EOF
