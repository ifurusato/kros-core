#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-18
# modified: 2020-08-30
#
# For installing pigpio, see:  http://abyz.me.uk/rpi/pigpio/download.html
#
# To enable the pigpio daemon on startup:
# 
#   sudo systemctl enable pigpiod
# 
# or to disable the pigpio daemon on startup:
# 
#   sudo systemctl disable pigpiod
# 
# or start it immediately:
# 
#   sudo systemctl start pigpiod 
# 
# To obtain the status of the pigpiod deamon: 
# 
#   sudo systemctl status pigpiod 
# 

import sys
from colorama import init, Fore, Style
init()

from core.logger import Logger

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Decoder(object):
    '''
    Class to decode mechanical rotary encoder pulses, implemented
    using pigpio's pi.callback() method.

    Decodes the rotary encoder A and B pulses, e.g.:

                     +---------+         +---------+      0
                     |         |         |         |
           A         |         |         |         |
                     |         |         |         |
           +---------+         +---------+         +----- 1

               +---------+         +---------+            0
               |         |         |         |
           B   |         |         |         |
               |         |         |         |
           ----+         +---------+         +---------+  1

    '''

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __init__(self, orientation, gpio_a, gpio_b, callback, level):
        '''
        Instantiate the class with the pi and gpios connected to
        rotary encoder contacts A and B. The common contact should
        be connected to ground. The callback is called when the
        rotary encoder is turned. It takes one parameter which is
        +1 for clockwise and -1 for counterclockwise.

        EXAMPLE

        from lib.decoder import Decoder

        def my_callback(self, step):
           self._steps += step

        pin_a = 17
        pin_b = 18
        decoder = Decoder(pi, pin_a, pin_b, my_callback)
        ...
        decoder.cancel()

        :param orientation:  the motor orientation
        :param gpio_a:        pin number for A
        :param gpio_b:        pin number for B
        :param callback:     the callback method
        :param level:        the log Level
        '''
        self._log = Logger('enc:{}'.format(orientation.label), level)
        self._gpio_a = gpio_a
        self._gpio_b = gpio_b
        self._log.info('pin A: {:d}; pin B: {:d}'.format(self._gpio_a,self._gpio_b))
        self._callback = callback
        self._level_a = 0
        self._level_b = 0
        self._last_gpio = None
        self._increment = 1
        self._pi = self._get_pi()
        if self._pi:
            self._pi.set_mode(self._gpio_a, pigpio.INPUT)
            self._pi.set_mode(self._gpio_b, pigpio.INPUT)
            self._pi.set_pull_up_down(self._gpio_a, pigpio.PUD_UP)
            self._pi.set_pull_up_down(self._gpio_b, pigpio.PUD_UP)
#           _edge = pigpio.RISING_EDGE  # default
#           _edge = pigpio.FALLING_EDGE
            _edge = pigpio.EITHER_EDGE
            self.callback_a = self._pi.callback(self._gpio_a, _edge, self._pulse_a)
            self.callback_b = self._pi.callback(self._gpio_b, _edge, self._pulse_b)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_pi(self):
        try:
            import pigpio
        except ImportError as ie:
        #   import mock.pigpio as pigpio
            print(Fore.RED + "This script requires the pigpio module.\n"\
                + Fore.YELLOW + "Install with: pip3 install --user pigpio" + Style.RESET_ALL)
#           raise ModuleNotFoundError('pigpio not installed.')
            return None
        try:
            _pi = pigpio.pi()
            if _pi is None:
                raise Exception('unable to instantiate pigpio.pi().')
            elif _pi._notify is None:
                raise Exception('can\'t connect to pigpio daemon; did you start it?')
            _pi._notify.name = 'pi.callback'
            self._log.info('pigpio version {}'.format(_pi.get_pigpio_version()))
            return _pi
        except Exception as e:
            self._log.error('error importing and/or configuring Motor: {}'.format(e))
            traceback.print_exc(file=sys.stdout)
            raise Exception('unable to instantiate decoder.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_reversed(self):
        '''
        If called, sets this encoder for reversed operation.
        '''
        self._increment = -1

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _pulse_a(self, gpio, level, tick):
        self._level_a = level
        if level == 1 and self._level_b == 1:
            self._callback(self._increment)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _pulse_b(self, gpio, level, tick):
        self._level_b = level;
        if level == 1 and self._level_a == 1:
            self._callback(-1 * self._increment)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def cancel(self):
        '''
        Cancel the rotary encoder decoder.
        '''
        self.callback_a.cancel()
        self.callback_b.cancel()

#EOF
