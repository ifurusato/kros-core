#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-09-11
# modified: 2021-09-11
#
# A client for the Handshaking Interrupt-Driven Hexadecimal Protocol (HIHP).
# Transmits interrupt-drive hexadecimal data over six wires.
#

import sys, time, itertools, traceback
import asyncio
import concurrent.futures
from colorama import init, Fore, Style
init()

from core.message_factory import MessageFactory
from core.logger import Logger, Level
from core.event import Event
from core.util import Util
from core.publisher import Publisher

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class HihpClient():

    # constants copied from microcontroller ................
    #                     3  2  1  0  D   DESC
    ORIENTATION_NONE  = [ 0, 0, 0, 0, 0, Fore.BLACK   + 'none' ] # none
    ORIENTATION_PORT  = [ 0, 0, 0, 1, 1, Fore.RED     + 'port' ] # port
    ORIENTATION_CNTR  = [ 0, 0, 1, 0, 2, Fore.BLUE    + 'cntr' ] # center
    ORIENTATION_STBD  = [ 0, 0, 1, 1, 3, Fore.GREEN   + 'stbd' ] # starboard
    ORIENTATION_PAFT  = [ 0, 1, 0, 0, 4, Fore.CYAN    + 'paft' ] # port-aft
    ORIENTATION_MAST  = [ 0, 1, 0, 1, 5, Fore.YELLOW  + 'mast' ] # mast
    ORIENTATION_SAFT  = [ 0, 1, 1, 0, 6, Fore.MAGENTA + 'saft' ] # starboard-aft    s
    ORIENTATION_ALL   = [ 1, 1, 1, 1, 7, Fore.WHITE   + 'all'  ] # unused (all bits high)
    ORIENTATIONS = [ ORIENTATION_NONE, ORIENTATION_PORT, ORIENTATION_CNTR, ORIENTATION_STBD, ORIENTATION_PAFT, ORIENTATION_MAST, ORIENTATION_SAFT, ORIENTATION_ALL ]

    '''
    Implements the BHIP (BCD Handshaking Interrupt-Driven Protocol). This uses
    five pins on the Pi GPIO and five pins on a microcontroller to perform
    interrupt-driven transfer of BCD data. The pins are as follows:

        ack_pin  : output pin sends an 'acknowledge' signal to TinyPICO
        int_pin  : interrupt pin from TinyPICO indicates data available
        d0_pin   : 0 data  ┒
        d1_pin   : 1 data  ┠─── hexadecimal-encoded data
        d2_pin   : 2 data  ┃ 
        d3_pin   : 3 data  ┚

    The hex values match the constants in the microcontroller, with 0 meaning
    no data and the rest indicating the triggering of a specified sensor
    orientation, but could be used to tranfer any single hexadecimal number.

    :param config:            the application configuration
    :param level:             the log level
    '''
    def __init__(self, config, level=Level.INFO):
        if not isinstance(level, Level):
            raise ValueError('wrong type for log level argument: {}'.format(type(level)))
        self._log = Logger('rate', level)
        # configuration ................
        self._counter = itertools.count()
        self._pi      = None
        _cfg = config['kros'].get('hihp')
        # pin assignments
        self._ack_pin = _cfg.get('ack_pin') # ACK pin (output)
        self._int_pin = _cfg.get('int_pin') # INT pin
        self._d0_pin  = _cfg.get('d0_pin')  # data 0
        self._d1_pin  = _cfg.get('d1_pin')  # data 1
        self._d2_pin  = _cfg.get('d2_pin')  # data 2
        self._d3_pin  = _cfg.get('d3_pin')  # data 3
        self._log.info('bumper pin assignments:\t' \
                + Fore.WHITE    + ' ack={:d};'.format(self._ack_pin) \
                + Fore.MAGENTA  + ' int={:d};'.format(self._int_pin) \
                + Fore.RED      + ' d0={:d};'.format(self._d0_pin) \
                + Fore.GREEN    + ' d1={:d};'.format(self._d1_pin) \
                + Fore.BLUE     + ' d2={:d};'.format(self._d2_pin) \
                + Fore.YELLOW   + ' d3={:d};'.format(self._d3_pin))
        self._ack_delay_sec     = 0.05 # ACK normal acknowledgement
        self._enable_delay_sec  = 0.66  # ACK for this time will enable server
        self._disable_delay_sec = 1.2  # ACK for this time will disable server
        self._enabled = False
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        '''
        Imports pigpio and initialises the input and output pins.
        '''
        if not self._enabled:
            try:
                self._log.info('importing pigpio ...')
                import pigpio
                # establish pigpio interrupts for bumper pins
                self._log.info('enabling bumper interrupts...')
                self._pi = pigpio.pi()
                self._log.info('importing pigpio ...')
                if not self._pi.connected:
                    raise Exception('unable to establish connection to Pi.')
                # acknowledge pin (output)
                self._pi.set_mode(self._ack_pin, pigpio.OUTPUT) # ack
    
                # configure int callback .....................................
                self._log.info('configuring callback...')
                self._pi.set_mode(gpio=self._int_pin, mode=pigpio.INPUT)
                _port_callback = self._pi.callback(self._int_pin, pigpio.FALLING_EDGE, self._interrupt_callback)
                self._log.info('configured INT callback on pin {:d}.'.format(self._int_pin))
    #                   self._pi.set_mode(self._int_pin, pigpio.INPUT)  # int
                # data pins ................................................
                self._pi.set_mode(self._d0_pin, pigpio.INPUT)    # data 0
                self._pi.set_mode(self._d1_pin, pigpio.INPUT)    # data 1
                self._pi.set_mode(self._d2_pin, pigpio.INPUT)    # data 2
                self._pi.set_mode(self._d3_pin, pigpio.INPUT)    # data 3
                self._log.info('configuration complete....')
            except Exception as e:
                self._log.warning('error configuring bumper interrupt: {}'.format(e))
            finally:
                self._enabled = True

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def send_ack(self):
        self._log.info(Fore.YELLOW + 'send: ' + Style.BRIGHT + 'ACK')
        self._pi.write(self._ack_pin, 0)
        time.sleep(self._ack_delay_sec)
        self._pi.write(self._ack_pin, 1)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def send_enable(self):
        self._log.info(Fore.YELLOW + 'send: ' + Style.BRIGHT + 'ENABLE')
        self._pi.write(self._ack_pin, 0)
        time.sleep(self._enable_delay_sec)
        self._pi.write(self._ack_pin, 1)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def send_disable(self):
        self._log.info(Fore.YELLOW + 'send: ' + Style.BRIGHT + 'DISABLE')
        self._pi.write(self._ack_pin, 0)
        time.sleep(self._disable_delay_sec)
        self._pi.write(self._ack_pin, 1)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _interrupt_callback(self, gpio, level, ticks):
        '''
        This is the callback method triggered by the pigpio interrupt on the
        designated INT pin. Once triggered it reads the values of the three data
        pins and then sends an ACK message back to the TinyPICO. The TinyPICO
        awaits this and upon receiving ACK drops all the data lines to zero.
        '''
        #                       0  1  2  3  4  5
        #                       3  2  1  0  D  Description
        # ORIENTATION_MAST  = [ 0, 1, 0, 1, 5, Fore.YELLOW  + 'mast' ] # mast
        _d0 = self._pi.read(self._d0_pin)
        _d1 = self._pi.read(self._d1_pin)
        _d2 = self._pi.read(self._d2_pin) 
        _d3 = self._pi.read(self._d3_pin) 
        _dec = int('{}{}{}{}'.format(_d3, _d2, _d1, _d0)[:4], 2)
        _dec2 = Util.to_decimal('{}{}{}{}'.format(_d3, _d2, _d1, _d0))
        _orientation = HihpClient.ORIENTATIONS[_dec]
        _desc = _orientation[5]

        self._log.info(Fore.BLUE + 'interrupt callback:\t' + Style.BRIGHT + '{}-{}-{}-{}; dec: {:d}; name: {}'.format(_d3, _d2, _d1, _d0, _dec, _desc))
        self.send_ack()
        self._log.info(Fore.WHITE + 'interrupt callback:\t' + Style.BRIGHT + 'sent ACK.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        self.send_disable()
        if self._pi:
            self._pi.stop()
        self._log.info('closed.')

#EOF
