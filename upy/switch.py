#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-09-12
# modified: 2021-09-13
#

import time

from machine import Pin

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Switch(object):
    '''
    A debounced switch implementation. Usage e.g.:

        def _callback(pin):
            print('Switch {} changed to: {}'.format(pin, pin.value()))

        switch_handler = Switch(pin=Pin(17, mode=Pin.IN, pull=Pin.PULL_UP), callback=_callback)

    :param pin:       the pin number
    :param callback:  the callback method upon completion
    :param trigger:   the interrupt trigger (default: IRQ_FALLING)
    :param min_ago:   the minimum delay (default 250ms)
    '''
    def __init__(self, num, pin, callback, trigger=Pin.IRQ_FALLING, min_ago=250):
        self._num      = num
        self._callback = callback
        self._min_ago   = min_ago
        self._next_call = time.ticks_ms() + self._min_ago
        pin.irq(trigger=trigger, handler=self.debounce_handler)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _call_callback(self, pin):
        self._callback(pin)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def debounce_handler(self, pin):
        if time.ticks_ms() > self._next_call:
            self._call_callback(pin)
            self._next_call = time.ticks_ms() + self._min_ago
        
#EOF
