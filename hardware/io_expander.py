#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-01-18
# modified: 2020-10-28
#
# Wraps the functionality of a Pimoroni IO Expander Breakout board, providing
# access to the values of the board's pins, which outputs 0-255 values for
# analog pins, and a 0 or 1 for digital pins.
#
# source: /usr/local/lib/python3.7/dist-packages/ioexpander/__init__.py
#
from threading import Thread # TEMP

import sys, itertools, random
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event
from core.rate import Rate
from core.component import Component
from mock.io_expander import MockIoExpander # used only during dev and testing

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class IoExpander(Component):
    '''
    Wraps an IO Expander board as input from an integrated front sensor
    array of infrareds and bumper switches.

    Optional are a pair of analog imputs wired up as a Moth sensor.

    The bumpers are by default disabled since we've moved them over to
    interrupts on Pi GPIO pins rather than polling (too slow).

    :param config:            the application configuration

    :param enable_infrared:   when True enables infrared polling (default True)
    :param enable_moth:       when True enables moth polling (default True)
    :param enable_bumpers:    when True enables bumper polling (default False)

    :param callback:          the optional callback to be attached to the interrupt
    :param level:             the log level
    '''
    def __init__(self, config, enable_infrared=True, enable_moth=True, enable_bumpers=False, callback=None, level=Level.INFO):
        self._log = Logger('ioe', level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['kros'].get('io_expander')
        self._enable_bumpers   = enable_bumpers
        self._callback         = callback
        # infrared
        self._port_side_ir_pin = _config.get('port_side_ir_pin')  # pin connected to port side infrared
        self._port_ir_pin      = _config.get('port_ir_pin')       # pin connected to port infrared
        self._cntr_ir_pin      = _config.get('cntr_ir_pin')       # pin connected to center infrared
        self._stbd_ir_pin      = _config.get('stbd_ir_pin')       # pin connected to starboard infrared
        self._stbd_side_ir_pin = _config.get('stbd_side_ir_pin')  # pin connected to starboard side infrared
        if enable_infrared: 
            self._log.info('infrared pin assignments:\t' \
                    + Fore.RED + ' port side={:d}; port={:d};'.format(self._port_side_ir_pin, self._port_ir_pin) \
                    + Fore.BLUE + ' center={:d};'.format(self._cntr_ir_pin) \
                    + Fore.GREEN + ' stbd={:d}; stbd side={:d}'.format(self._stbd_ir_pin, self._stbd_side_ir_pin) + Style.RESET_ALL)
        # moth/anti-moth
        self._port_moth_pin = _config.get('port_moth_pin')  # pin connected to port moth sensor
        self._stbd_moth_pin = _config.get('stbd_moth_pin')  # pin connected to starboard moth sensor
        if enable_moth:
            self._log.info('moth pin assignments:\t' \
                    + Fore.RED + ' moth port={:d};'.format(self._port_moth_pin) \
                    + Fore.GREEN + ' moth stbd={:d};'.format(self._stbd_moth_pin) + Style.RESET_ALL)
        # bumpers
        if self._enable_bumpers:
            self._port_bmp_pin = _config.get('port_bmp_pin')      # pin connected to port bumper
            self._cntr_bmp_pin = _config.get('cntr_bmp_pin')      # pin connected to center bumper
            self._stbd_bmp_pin = _config.get('stbd_bmp_pin')      # pin connected to starboard bumper
            self._log.info('bumper pin assignments:\t' \
                    + Fore.RED + ' port={:d};'.format(self._port_bmp_pin) \
                    + Fore.BLUE + ' center={:d};'.format(self._cntr_bmp_pin) \
                    + Fore.GREEN + ' stbd={:d}'.format(self._stbd_bmp_pin) + Style.RESET_ALL)
        # debouncing "charge pumps"
        self._port_bmp_pump = 0
        self._cntr_bmp_pump = 0
        self._stbd_bmp_pump = 0
        self._pump_limit    = 10
        # thread support
        self._thread = None
        self._thread_enabled = False
        # configure board
        try:
            import ioexpander as io
            if self._callback:
                self._log.info(Fore.WHITE + 'configuring interrupts...' + Style.RESET_ALL)
                self._ioe = io.IOE(i2c_addr=0x18, interrupt_pin=4)
                # swap the interrupt pin for the Rotary Encoder breakout

                self._ioe.enable_interrupt_out()
#               self._ioe.enable_interrupt_out(pin_swap=True)
                self._log.info(Fore.WHITE + 'adding callback on interrupt...' + Style.RESET_ALL)
                self._ioe.on_interrupt(self._callback_method)
                self._log.info(Fore.WHITE + 'added callback on interrupt.' + Style.RESET_ALL)

                self._rate = Rate(20)
                self._thread_enabled = True
                self._log.info(Fore.WHITE + 'added monitoring thread...' + Style.RESET_ALL)
                self._thread = Thread(name='monitor', target=self._monitor_interrupt_loop, args=[lambda: self._thread_enabled])
                self._thread.start()

            else:
                # no interrupt
                self._log.info(Fore.RED + 'configuring without interrupts...' + Style.RESET_ALL)
                self._ioe = io.IOE(i2c_addr=0x18)

            self._ioe.set_adc_vref(3.3)  # input voltage of IO Expander, this is 3.3 on Breakout Garden

            if enable_infrared: # analog infrared sensors
                self._ioe.set_mode(self._port_side_ir_pin, io.ADC)
                self._ioe.set_mode(self._port_ir_pin,      io.ADC)
                self._ioe.set_mode(self._cntr_ir_pin,      io.ADC)
                self._ioe.set_mode(self._stbd_ir_pin,      io.ADC)
                self._ioe.set_mode(self._stbd_side_ir_pin, io.ADC)
            if enable_moth: # moth sensors
                self._ioe.set_mode(self._port_moth_pin,    io.ADC)
                self._ioe.set_mode(self._stbd_moth_pin,    io.ADC)
            if enable_bumpers: # digital bumpers
                self._ioe.set_mode(self._port_bmp_pin,     io.IN_PU)
                self._ioe.set_mode(self._cntr_bmp_pin,     io.IN_PU)
                self._ioe.set_mode(self._stbd_bmp_pin,     io.IN_PU)

#       except ImportError:
#           self._log.warning("This script requires the pimoroni-ioexpander module\nInstall with: pip3 install --user pimoroni-ioexpander [1]")
#           self._ioe = None
        except Exception as e:
#           self._log.warning('error configuring IOExpander: {}'.format(e))
#           sys.exit(1)
            self._log.warning('using mock IO Expander: error configuring: {}'.format(e))
            self._ioe = MockIoExpander(config, level)
        self._log.info('ready.')
   
    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _monitor_interrupt_loop(self, f_is_enabled):
        self._log.info(Fore.RED + Style.NORMAL + '🖤 _monitoring interrupt... ' + Style.RESET_ALL)
        while f_is_enabled():
            if self._ioe.get_interrupt():

                self._log.info(Fore.RED + Style.NORMAL + '💔💔💔🖤 interrupt TRIGGERED! ' + Style.RESET_ALL)
                _interrupt_value = self._ioe.get_interrupt()
                if _interrupt_value == 0:
                    self._log.info(Fore.RED + Style.NORMAL + '🖤 triggering callback method...; interrupt: {:d}'.format(_interrupt_value) + Style.RESET_ALL)
                else:
                    self._log.info(Fore.RED + Style.BRIGHT + '💔 triggering callback method...; interrupt: {:d}'.format(_interrupt_value) + Style.RESET_ALL)

                self._callback(_interrupt_value)

                _interrupt_value = self._ioe.get_interrupt()
                if _interrupt_value == 0:
                    self._log.info(Fore.RED + Style.NORMAL + '🖤🖤 triggered callback method...; interrupt: {:d}'.format(_interrupt_value) + Style.RESET_ALL)
                else:
                    self._log.info(Fore.RED + Style.BRIGHT + '💔💔 triggered callback method...; interrupt: {:d}'.format(_interrupt_value) + Style.RESET_ALL)

                self._log.debug(Fore.BLACK + '🖤 CLEAR interrupt...' + Style.RESET_ALL)
                self._ioe.clear_interrupt()
            else:
                self._log.debug(Fore.BLACK + '🖤 waiting...' + Style.RESET_ALL)
            self._rate.wait()

        self._log.info(Fore.GREEN + Style.NORMAL + '💛 exit _monitoring loop. ' + Style.RESET_ALL)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _callback_method(self, *argv):
        self._log.info(Fore.YELLOW + Style.BRIGHT + '💛 triggering callback method...; interrupt: {:d}'.format(self._ioe.get_interrupt()) + Style.RESET_ALL)
        self._callback(argv)
        self._ioe.clear_interrupt()
        self._log.info(Fore.YELLOW + Style.BRIGHT + '💛 triggered callback method; interrupt: {:d}'.format(self._ioe.get_interrupt()) + Style.RESET_ALL)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def is_active(self):
        return self._ioe != None

    # infrared sensors ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def get_port_side_ir_value(self):
        return int(round(self._ioe.input(self._port_side_ir_pin) * 100.0))

    def get_port_ir_value(self):
        return int(round(self._ioe.input(self._port_ir_pin) * 100.0))

    def get_cntr_ir_value(self):
        if not self._ioe:
            return None
        return int(round(self._ioe.input(self._cntr_ir_pin) * 100.0))

    def get_stbd_ir_value(self):
        return int(round(self._ioe.input(self._stbd_ir_pin) * 100.0))

    def get_stbd_side_ir_value(self):
        return int(round(self._ioe.input(self._stbd_side_ir_pin) * 100.0))

    # moth/anti-moth ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def get_moth_values(self):
        return [ int(round(self._ioe.input(self._port_moth_pin) * 100.0)), \
                 int(round(self._ioe.input(self._stbd_moth_pin) * 100.0)) ]

    # bumpers ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def get_port_bmp_value(self):
        if self._enable_bumpers:
            return ( self._ioe.input(self._port_bmp_pin) == 0 )
        else:
            return False

    def get_cntr_bmp_value(self):
        if self._enable_bumpers:
            _value = self._ioe.input(self._cntr_bmp_pin)
            if _value == 0:
                print(Fore.GREEN + 'get_cntr_bmp_value({}): {}'.format(type(_value), _value) + Style.RESET_ALL)
                return True
            else:
                print(Fore.RED + 'get_cntr_bmp_value({}): {}'.format(type(_value), _value) + Style.RESET_ALL)
                return False
        else:
            return False

    def get_stbd_bmp_value(self):
        if self._enable_bumpers:
            return ( self._ioe.input(self._stbd_bmp_pin) == 0 )
        else:
            return False

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    # raw values are unprocessed values from the IO Expander (used for testing)
   
    # raw infrared sensors ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def get_raw_port_side_ir_value(self):
        return self._ioe.input(self._port_side_ir_pin)

    def get_raw_port_ir_value(self):
        return self._ioe.input(self._port_ir_pin)

    def get_raw_cntr_ir_value(self):
        return self._ioe.input(self._cntr_ir_pin)

    def get_raw_stbd_ir_value(self):
        return self._ioe.input(self._stbd_ir_pin)

    def get_raw_stbd_side_ir_value(self):
        return self._ioe.input(self._stbd_side_ir_pin)

    # raw moth sensors ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def get_raw_moth_values(self):
        return [ self._ioe.input(self._port_moth_pin), self._ioe.input(self._stbd_moth_pin) ]

    def get_raw_port_moth_value(self):
        return self._ioe.input(self._port_moth_pin)

    def get_raw_stbd_moth_value(self):
        return self._ioe.input(self._stbd_moth_pin)

    # raw bumpers ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def get_raw_port_bmp_value(self):
        if self._enable_bumpers:
            return self._ioe.input(self._port_bmp_pin)
        else:
            return 1

    def get_raw_cntr_bmp_value(self):
        if self._enable_bumpers:
            return self._ioe.input(self._cntr_bmp_pin)
        else:
            return 1

    def get_raw_stbd_bmp_value(self):
        if self._enable_bumpers:
            return self._ioe.input(self._stbd_bmp_pin)
        else:
            return 1

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        self._log.info(Fore.WHITE + 'close()' + Style.RESET_ALL)
        self._thread_enabled = False
        Component.close(self)
        if self._thread != None:
            self._thread.join(timeout=1.0)
            self._log.info(Fore.WHITE + 'thread joined.' + Style.RESET_ALL)

# EOF
