#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-19
# modified: 2021-08-07
#

try:
    import ioexpander as io
except ImportError:
    exit("This script requires the ioexpander module\nInstall with: pip3 install --user pimoroni-ioexpander")

from core.logger import Level, Logger

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class AnalogPotentiometer(object):
    '''
    Configures an analog potentiometer (wired from Vcc to Gnd) connected to a
    single pin on a Pimoroni IO Expander Breakout Garden board, returning an
    analog value scaled to a specified range. For a center-zero pot simply
    specify the minimum value as (-1.0 * out_max).

    Optional pin, min and max values will resort to the application
    configuration if not provided explicitly as arguments.

    :param config:     The application configuration.
    :param pin:        The pin on the IO Expander to use for analog input.
    :param in_min:     (optional) Minimum input value.
    :param in_max:     (optional) Maximum input value.
    :param out_min:    (optional) Minimum output value.
    :param out_max:    (optional) Maximum output value.
    :param level:      The log level.
    '''
    def __init__(self, config, pin=None, in_min=None, in_max=None, out_min=None, out_max=None, level=Level.INFO):
        super().__init__()
        self._log = Logger('analog-pot', level)
        if not isinstance(config, dict):
            raise ValueError('wrong type for config argument: {}'.format(type(config)))
        _config = config['kros'].get('hardware').get('analog_potentiometer')
        self._pin     = _config.get('pin') if pin is None else pin
        self._log.info('pin assignment: {:d};'.format(self._pin))
        # e.g., minimum and maximum analog values from IO Expander
        self._in_min  = float(_config.get('in_min')) if in_min is None else in_min
        self._in_max  = float(_config.get('in_max')) if in_max is None else in_max
        self._log.info('in range:  {:>5.2f}-{:<5.2f}'.format(self._in_min, self._in_max))
        # minimum and maximum scaled output values
        self._out_min = _config.get('out_min') if out_min is None else out_min
        self._out_max = _config.get('out_max') if out_max is None else out_max
        self._log.info('out range: {:>5.2f}-{:<5.2f}'.format(self._out_min, self._out_max))
        # configure IO Expander board
        self._ioe     = io.IOE(i2c_addr=0x18)
        self._ioe.set_adc_vref(3.3)  # input voltage of IO Expander, this is 3.3 on Breakout Garden
        # configure pin
        self._ioe.set_mode(self._pin, io.ADC)
        self._clip = lambda n: self._out_min if n <= self._out_min else self._out_max if n >= self._out_max else n
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_out_max(self, out_max):
        self._out_max = out_max

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_value(self):
        '''
        Return the analog value as returned from the IO Expander board.
        This has been observed to be integers ranging from 0 to 330.
        '''
        return int(round(self._ioe.input(self._pin) * 100.0))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_scaled_value(self):
        '''
                (b-a)(x - in_min)
        f(x) = ------------------- + a
                 in_max - in_min

        where:

            x is input value to the function
            a is out_min, b is out_max

            E.g., a = 0.0, b = 1.0, min = 0, max = 330.

        For safety, the value is further clipped by the configured lambda.
        '''
        _value = (( self._out_max - self._out_min ) * ( self.get_value() - self._in_min ) / ( self._in_max - self._in_min )) + self._out_min
        return -1.0 * self._clip(-1.0 * _value) if _value < 0.0 else self._clip(_value)

#EOF
