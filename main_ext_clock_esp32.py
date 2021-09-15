# UART Data Transmitter for Sensor Data (UDT4SD)
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-26
# modified: 2021-09-14
#

from machine import Timer
from machine import Pin
import time

import itertools
import upy_utils as ut

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def poll():
    '''
    Toggle the clock pin.
    '''
    _clock_pin.value(not _clock_pin.value())
    if next(g_counter) % 20 == 0.0:
        ut.rgb_led(ut.COLOR_TURQUOISE)
        time.sleep_ms(4)
    ut.rgb_led(ut.COLOR_BLACK)

g_counter = itertools.count()

EXT_CLOCK_PIN = 18
_clock_pin = Pin(EXT_CLOCK_PIN, Pin.OUT)

# start polling loop with frequency of 20Hz (50ms)
_timer = Timer(1)
_timer.init(period=50, mode=Timer.PERIODIC, callback=lambda n: poll())

ut.ready()

#EOF
