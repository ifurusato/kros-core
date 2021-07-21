#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-19
# modified: 2021-07-21
#
# DeviceNotFound at bottom.
#

import sys, colorsys
import ioexpander as io
from colorama import init, Fore, Style
init()

from core.logger import Logger

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Potentiometer(object):
    '''
    Configures an IO Expander Potentiometer breakout, returning an analog
    value scaled to a specified range. For a center-zero pot simply
    specify the minimum value as (-1.0 * out_max).
    '''
    def __init__(self, config, level):
        super().__init__()
        self._log = Logger('ioe', level)
        if config is None:
            raise ValueError('no configuration provided.')
        _cfg = config['kros'].get('hardware').get('potentiometer')
        # 0x18 for IO Expander, 0x0E for the potentiometer breakout
#       self._i2c_addr = 0x0E
        self._i2c_addr   = _cfg.get('i2c_address')
        self._pin_red    = _cfg.get('pin_red')
        self._pin_green  = _cfg.get('pin_green')
        self._pin_blue   = _cfg.get('pin_blue')
        self._log.info("pins: red: {}; green: {}; blue: {}".format(self._pin_red, self._pin_green, self._pin_blue))

        self._pot_enc_a  = 12
        self._pot_enc_b  = 3
        self._pot_enc_c  = 11
        self._max_value  = 3.3                       # maximum voltage (3.3v supply)
        self._brightness = _cfg.get('brightness') # effectively max fraction of period LED will be on
        self._period = int(255 / self._brightness)   # add a period large enough to get 0-255 steps at the desired brightness

        _in_min          = _cfg.get('in_min')  # minimum analog value from IO Expander
        _in_max          = _cfg.get('in_max')  # maximum analog value from IO Expander
        self.set_input_limits(_in_min, _in_max)
        _out_min         = _cfg.get('out_min') # minimum scaled output value
        _out_max         = _cfg.get('out_max') # maximum scaled output value
        self.set_output_limits(_out_min, _out_max)

        # now configure IO Expander
        try:
            self._ioe = io.IOE(i2c_addr=self._i2c_addr)
            self._ioe.set_mode(self._pot_enc_a, io.PIN_MODE_PP)
            self._ioe.set_mode(self._pot_enc_b, io.PIN_MODE_PP)
            self._ioe.set_mode(self._pot_enc_c, io.ADC)
            self._ioe.output(self._pot_enc_a, 1)
            self._ioe.output(self._pot_enc_b, 0)
            self._ioe.set_pwm_period(self._period)
            self._ioe.set_pwm_control(divider=2)  # PWM as fast as we can to avoid LED flicker
            self._ioe.set_mode(self._pin_red,   io.PWM, invert=True)
            self._ioe.set_mode(self._pin_green, io.PWM, invert=True)
            self._ioe.set_mode(self._pin_blue,  io.PWM, invert=True)
        except Exception as e:
#           self._log.warning(Fore.BLACK + "unable to initialise IO Expander: {}\n{}".format(e, traceback.format_exc()))
            raise DeviceNotFound("unable to initialise potentiometer.")

        self._log.info("running LED with {} brightness steps.".format(int(self._period * self._brightness)))
        self._log.info("ready.")

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_input_limits(self, in_min, in_max):
        self._in_min = in_min
        self._in_max = in_max
        self._log.info('input range:\t{:>5.2f}-{:<5.2f}'.format(self._in_min, self._in_max))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_output_limits(self, out_min, out_max):
        self._out_min = out_min
        self._out_max = out_max
        self._log.info('output range:\t{:>5.2f}-{:<5.2f}'.format(self._out_min, self._out_max))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def value(self):
        _value = self._max_value - self._ioe.input(self._pot_enc_c)
        self._log.debug(Fore.BLACK + 'value: {:<5.2f}'.format(_value))
        return _value

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_white(self):
        self._ioe.output(self._pin_red, 255)
        self._ioe.output(self._pin_green, 255)
        self._ioe.output(self._pin_blue, 255)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_black(self):
        self._ioe.output(self._pin_red, 0)
        self._ioe.output(self._pin_green, 0)
        self._ioe.output(self._pin_blue, 0)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_rgb(self, value):
        h = value / self._max_value # time.time() / 10.0
        r, g, b = [int(c * self._period * self._brightness) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0)]
        self._ioe.output(self._pin_red, r)
        self._ioe.output(self._pin_green, g)
        self._ioe.output(self._pin_blue, b)
        self._log.debug('value: {:<5.2f}; rgb: {},{},{}'.format(value, r, g, b))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_scaled_value(self, update_led=True):
        '''
        Return a scaled value while also updating the RGB LED if the
        argument is True (the default).
        '''
        _value = self.value
        if update_led:
            self.set_rgb(_value)
        return self.scale_value(_value) # as float

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def scale_value(self, value):
        '''
                   (out_max - out_min)(value - in_min)
            f(x) = -----------------------------------  + out_min
                            in_max - in_min

            where e.g.:  a = 0.0, b = 1.0, min = 0, max = 330.
        '''
        return (( self._out_max - self._out_min ) * ( value - self._in_min ) / ( self._in_max - self._in_min )) + self._out_min

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class DeviceNotFound(Exception):
    '''
    Thrown when an expected device cannot be found.
    '''
    pass

#EOF
