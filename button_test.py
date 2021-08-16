#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
#    This tests the Button task, which reads the state of the push button.
#

import pigpio
import os, sys, signal, time
from colorama import init, Fore, Style
init()

#import RPi.GPIO as GPIO
from core.logger import Logger, Level
from core.component import Component

_log = Logger('button-test', Level.INFO)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Button(Component):
    '''
    Sets up a falling-edge callback on a GPIO pin.
    '''
    def __init__(self, pin, callback, level=Level.INFO):
        self._log = Logger('button', level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        self._pi = pigpio.pi()
        if not self._pi.connected:
            raise Exception('unable to establish connection to Pi.')
        self._log.info('establishing callback on pin {:d}.'.format(pin))
        self._pi.set_mode(gpio=pin, mode=pigpio.INPUT) # GPIO 12 as input
        _cb1 = self._pi.callback(pin, pigpio.EITHER_EDGE, callback)
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'button'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        if self._pi:
            self._pi.stop()
        Component.close(self)
        self._log.info('closed.')

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def callback_method(gpio, level, tick):
    global activated
    activated = True
    print(Fore.YELLOW + 'callback method fired; gpio: {}; level: {}; tick: {}'.format(gpio, level, tick) + Style.RESET_ALL)
#   _log.info(Fore.YELLOW + 'callback method fired; gpio: {}; level: {}; tick: {}'.format(gpio, level, tick))

# main ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
_button = None
def main():
    global activated
    activated = False

    _log.info('starting test...')


#   GPIO.setmode(GPIO.BCM)
#   GPIO.setup(_pin, GPIO.IN)
#   GPIO.add_event_detect(_pin, GPIO.FALLING, callback=callback_method, bouncetime=200)

    try:

        _pin = 12
        _button = Button(_pin, callback_method)
        _button.enable()

        while True:
            _log.info(Fore.BLACK + 'waiting for button press on pin {:d};\t'.format(_pin) + Fore.GREEN + ' activated: {}'.format(activated))
            time.sleep(1.0)

    except KeyboardInterrupt:
        _log.info(Fore.RED + "caught Ctrl-C.")
    finally:
        if _button:
            _log.info("closing button...")
            if _button:
                _button.close()

if __name__== "__main__":
    main()

