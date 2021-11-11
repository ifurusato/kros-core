#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-17
# modified: 2021-10-19
#
# Lazily imports RPi.GPIO
#
# Install with: sudo apt install rpi.gpio
#

#import time, threading

from core.logger import Level, Logger

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Status():
    '''
    Status Task: turns the status light (an LED connected to a GPIO pin) on and
    off when it is set enabled or disabled.
    '''
    def __init__(self, config, level):
        self._log = Logger('status', level)
        self._log.debug('initialising...')
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['kros'].get('hardware').get('status')
        self._led_pin = _config.get('led_pin')
        try:
            import RPi.GPIO as GPIO

            self._gpio = GPIO
            self._gpio.setwarnings(False)
            self._gpio.setmode(GPIO.BCM)
            self._gpio.setup(self._led_pin, GPIO.OUT, initial=GPIO.LOW)
            self._blink_thread = None
            self._log.info('ready.')
        except ModuleNotFoundError as e:
            self._log.warning('This script requires the RPi.GPIO library. Some features will be disabled.')
            self._gpio = None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        if self._gpio:
            self._log.info('enable status light.')
            self._gpio.output(self._led_pin, True)
        else:
            self._log.info('💡 enable status light.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        self._log.info('disable status light.')
        if self._gpio:
            self._gpio.output(self._led_pin,False)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        self._log.info('closing status light...')
        self.disable()
        self._log.info('status light closed.')

#EOF
