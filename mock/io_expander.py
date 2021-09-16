#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2021-08-16
# modified: 2021-08-16
#
# Mocks the Pimoroni IO Expander.
#

import itertools, random
from colorama import init, Fore, Style
init()

from core.component import Component
from core.logger import Logger, Level

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MockIoExpander(Component):
    '''
    A mock Pimoroni IO Expander that responds randomly to requests for input
    values on its digital and analog pins, using the same pin configuration
    as used for the real one.
    '''
    def __init__(self, config, level):
        self._log = Logger('mock-ioe', level)
        Component.__init__(self, self._log, suppressed=True, enabled=False)
        if config is None:
            raise ValueError('no configuration provided.')
        self._counter = itertools.count()
        _count = next(self._counter) # gets us above zero
        self._cntr_value = 255.0
        # copied from IoExpander init
        _config = config['kros'].get('io_expander')
        # infrared
        self._port_side_ir_pin = _config.get('port_side_ir_pin')  # pin connected to port side infrared
        self._port_ir_pin      = _config.get('port_ir_pin')       # pin connected to port infrared
        self._cntr_ir_pin      = _config.get('cntr_ir_pin')       # pin connected to center infrared
        self._stbd_ir_pin      = _config.get('stbd_ir_pin')       # pin connected to starboard infrared
        self._stbd_side_ir_pin = _config.get('stbd_side_ir_pin')  # pin connected to starboard side infrared
        # moth/anti-moth
        self._port_moth_pin    = _config.get('port_moth_pin')     # pin connected to port moth sensor
        self._stbd_moth_pin    = _config.get('stbd_moth_pin')     # pin connected to starboard moth sensor
        # bumpers
        self._port_bmp_pin     = _config.get('port_bmp_pin')      # pin connected to port bumper
        self._cntr_bmp_pin     = _config.get('cntr_bmp_pin')      # pin connected to center bumper
        self._stbd_bmp_pin     = _config.get('stbd_bmp_pin')      # pin connected to starboard bumper
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def input(self, pin):
        if self.is_active:
            _count = next(self._counter)
            _modulo = random.randint(100, 200)
#           self._log.debug(Fore.BLACK + 'requesting input from pin {:d}...'.format(pin))
            _permit_random_bumper = False
            _value = 0.0
            if _count % _modulo == 0.0:
                if pin == self._port_side_ir_pin: # random analog value
                    _value = random.randint(0, 50) + 205
                elif pin == self._port_ir_pin: # random analog value
                    _value = random.randint(0, 50) + 205
                elif pin == self._cntr_ir_pin: # decrement center IR each time called by 22
                    self._cntr_value -= 22.0
                    if self._cntr_value <= 50.0:
                        self._cntr_value = 255.0
                    _value = self._cntr_value
                elif pin == self._stbd_ir_pin: # random analog value
                    _value = random.randint(0, 50) + 205
                elif pin == self._stbd_side_ir_pin: # random analog value
                    _value = random.randint(0, 50) + 205
                elif pin == self._port_bmp_pin: # random digital value
                    if _permit_random_bumper and ( _count % 100 == 0.0 ):
                        _value = 1
                    else:
                        _value = 0
                elif pin == self._cntr_bmp_pin: # random digital value
                    if _permit_random_bumper and ( _count % 100 == 0.0 ):
                        _value = 1
                    else:
                        _value = 0
                elif pin == self._stbd_bmp_pin: # random digital value
                    if _permit_random_bumper and ( _count % 100 == 0.0 ):
                        _value = 1
                    else:
                        _value = 0
                # done.
                if isinstance(_value, float):
                    self._log.info('requesting input from pin {:d}, returning value: {:5.2f}'.format(pin, _value))
                else:
                    self._log.info('requesting input from pin {:d}, returning value: {:d}'.format(pin, _value))
            return _value 
        else:
            raise Exception('mock ioe not active.')

# EOF
