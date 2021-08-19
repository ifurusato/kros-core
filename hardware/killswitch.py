#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-18
# modified: 2021-08-18
#

import time, pigpio
from enum import Enum
from colorama import init, Fore, Style
init()

from core.logger import Level, Logger
from core.event import Event
from core.component import Component

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class KillSwitch(Component):
    '''
    A simple monitor for a kill switch connected to a GPIO pin.

    Rather than any fancy message bus stuff we just set up a callback on the
    pin when enabled and just call a kill() method on KROS when triggered.

    This should be closed upon completion so the Pi resources are freed up.

    :param config:    the application configuration
    :param kros:      the KROS application
    :param level:     the loggin level
    '''
    def __init__(self, config, kros, level):
        self._log = Logger('kill', level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        if not isinstance(config, dict):
            raise ValueError('wrong type for config argument: {}'.format(type(config)))
        self._config = config['kros'].get('hardware').get('killswitch')
        self._pin = self._config.get('pin')
        self._kros = kros
        self._triggered = False
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def callback_method(self, gpio, level, tick):
        if not self._triggered:
            self._triggered = True
            print(Fore.YELLOW + 'callback method fired; gpio: {}; level: {}; tick: {}'.format(gpio, level, tick) + Style.RESET_ALL)
            self._log.info(Fore.YELLOW + 'callback method fired; gpio: {}; level: {}; tick: {}'.format(gpio, level, tick) + Style.RESET_ALL)
            self._kros.shutdown()
            time.sleep(0.1)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def reset(self):
        self._triggered = False

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Component.enable(self)
        if self.enabled:
            self._log.info('enabling killswitch...')
            try:
                self._pi = pigpio.pi()
                if not self._pi.connected:
                    raise Exception('unable to establish connection to Pi.')
                self._pi.set_mode(gpio=self._pin, mode=pigpio.INPUT) # GPIO 12 as input
                _cb1 = self._pi.callback(self._pin, pigpio.FALLING_EDGE, self.callback_method)
                self._log.info('configured kill switch callback on pin {:d}.'.format(self._pin))
            except Exception as e:
                self._log.error('unable to enable kill switch: {}'.format(e))
        else:
            self._log.warning('already enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        if self._pi:
            self._pi.stop()
        Component.close(self)
        self._log.info('closed.')

#EOF
