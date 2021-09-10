#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-07-21
#
# The beginnings of BHIP: BCD Handshaking Interrupt-Driven Protocol
# Transmits interrupt-drive BCD data over 5 wires.
#

import sys, time, itertools, random, traceback
import asyncio
import concurrent.futures
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.message_factory import MessageFactory
from core.logger import Logger, Level
from core.event import Event
from core.util import Util
from core.publisher import Publisher

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ExternalBumperPublisher(Publisher):

    CLASS_NAME = 'xbmp'
    # constants matching microcontroller .......
    ORIENTATION_NONE = [ 0, Fore.BLACK   + 'none' ]
    ORIENTATION_PORT = [ 1, Fore.RED     + 'port' ]
    ORIENTATION_CNTR = [ 2, Fore.BLUE    + 'cntr' ]
    ORIENTATION_STBD = [ 3, Fore.GREEN   + 'stbd' ]
    ORIENTATION_PAFT = [ 4, Fore.CYAN    + 'paft' ]
    ORIENTATION_MAST = [ 5, Fore.YELLOW  + 'mast' ]
    ORIENTATION_SAFT = [ 6, Fore.MAGENTA + 'saft' ]
    ORIENTATION_ALL  = [ 7, Fore.WHITE   + 'all'  ]
    ORIENTATIONS = [ ORIENTATION_NONE, ORIENTATION_PORT, ORIENTATION_CNTR, ORIENTATION_STBD, ORIENTATION_PAFT, ORIENTATION_MAST, ORIENTATION_SAFT, ORIENTATION_ALL ]

    _LISTENER_LOOP_NAME = '__bmp_listener_loop'

    '''
    A publisher for bumper events from six lever switches wired in three pairs
    for bumpers, as well as aft and mast digital infrared sensors intended to
    catch non-physical "bumps", such as when backing up or upon the mast.

    The bumper lever switches and digital infrared sensors are connected to an
    external microcontroller (a TinyPICO) and their events are sent to the Pi
    using a bespoke 5 pin communications protocol:

        bmp_ack_pin   : output pin sends an 'acknowledge' signal to TinyPICO
        bmp_int_pin   : interrupt pin from TinyPICO indicates data available
        bmp_0_pin     : 0 data  ┒
        bmp_1_pin     : 1 data  ┠─── binary-encoded decimal data
        bmp_2_pin     : 2 data  ┚

    The BCD values match the constants in the microcontroller, with 0 meaning
    no data and the rest indicating a sensor orientation.

    :param config:            the application configuration
    :param message_bus:       the asynchronous message bus
    :param message_factory:   the factory for creating messages
    :param level:             the log level
    '''
    def __init__(self, config, message_bus, message_factory, level=Level.INFO):
        if not isinstance(level, Level):
            raise ValueError('wrong type for log level argument: {}'.format(type(level)))
        self._level = level
        Publisher.__init__(self, ExternalBumperPublisher.CLASS_NAME, config, message_bus, message_factory, level=self._level)
        # configuration ................
        self._counter = itertools.count()
        self._pi      = None
        _cfg = config['kros'].get('publisher').get('external_bumper')
        _loop_freq_hz = _cfg.get('loop_freq_hz')
        self._publish_delay_sec = 1.0 / _loop_freq_hz
        self._reset_trigger(Event.ANY) # initialises all triggers
        self._initd   = False
        # pin assignments
        self._ack_pin = _cfg.get('ack_pin') # ACK pin (output)
        self._int_pin = _cfg.get('int_pin') # INT pin
        self._d0_pin  = _cfg.get('d0_pin')  # data 0
        self._d1_pin  = _cfg.get('d1_pin')  # data 1
        self._d2_pin  = _cfg.get('d2_pin')  # data 2
        self._log.info('bumper pin assignments:\t' \
                + Fore.WHITE    + ' ack={:d};'.format(self._ack_pin) \
                + Fore.YELLOW   + ' int={:d};'.format(self._int_pin) \
                + Fore.RED      + ' d0={:d};'.format(self._d0_pin) \
                + Fore.BLUE     + ' d1={:d};'.format(self._d1_pin) \
                + Fore.GREEN    + ' d2={:d};'.format(self._d2_pin))
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _init(self):
        '''
        Imports pigpio and initialises the input and output pins.
        '''
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
            self._log.info('configuration complete....')
        except Exception as e:
            self._log.warning('error configuring bumper interrupt: {}'.format(e))
        finally:
            self._initd = True

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if not self._initd:
                self._init()
            if self._message_bus.get_task_by_name(ExternalBumperPublisher._LISTENER_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                self._log.info('creating task for bmp listener loop...')
                self._message_bus.loop.create_task(self._bmp_listener_loop(lambda: self.enabled), name=ExternalBumperPublisher._LISTENER_LOOP_NAME)
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable publisher.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def send_ack(self):
        self._log.info(Fore.YELLOW + 'send: ' + Style.BRIGHT + 'ACK')
        self._pi.write(self._ack_pin, 1) # set ACK high
        time.sleep(0.1)
        self._pi.write(self._ack_pin, 0) # set ACK low

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def send_enable(self):
        self._log.info(Fore.YELLOW + 'send: ' + Style.BRIGHT + 'ENABLE')
        self._pi.write(self._ack_pin, 1) # set ACK high
        time.sleep(1.0)
        self._pi.write(self._ack_pin, 0) # set ACK low

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _interrupt_callback(self, gpio, level, ticks):
        '''
        This is the callback method triggered by the pigpio interrupt on the
        designated INT pin. Once triggered it reads the values of the three data
        pins and then sends an ACK message back to the TinyPICO. The TinyPICO
        awaits this and upon receiving ACK drops all the data lines to zero.
        '''
        _d0 = self._pi.read(self._d0_pin)
        _d1 = self._pi.read(self._d1_pin)
        _d2 = self._pi.read(self._d2_pin) 
        _dec = int('{}{}{}'.format(_d2, _d1, _d0)[:4], 2)
        _dec2 = Util.to_decimal('{}{}{}'.format(_d2, _d1, _d0))
        _orientation = ExternalBumperPublisher.ORIENTATIONS[_dec]
        _orientation_name = _orientation[1]

        self._log.info(Fore.BLUE + 'interrupt callback:\t' + Style.BRIGHT + '{}-{}-{}; dec: {:d}; name: {}'.format(_d2, _d1, _d0, _dec, _orientation_name))
        self.send_ack()
        self._log.info(Fore.WHITE + 'interrupt callback:\t' + Style.BRIGHT + 'sent ACK.')

#       if not self._port_triggered:
#           self._port_triggered = dt.now()
#           self._log.info(Fore.RED + 'bumper triggered on GPIO pin {}; logic: {}; {} ticks'.format(gpio, level, ticks))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _bmp_listener_loop(self, f_is_enabled):
        self._log.info('starting bumper listener loop.')
        while f_is_enabled():
            _count = next(self._counter)
            _message = None
            if self._mast_triggered:
                _message = self.message_factory.create_message(Event.BUMPER_MAST, self._mast_triggered)
            elif self._cntr_triggered:
                _message = self.message_factory.create_message(Event.BUMPER_CNTR, self._cntr_triggered)
            elif self._port_triggered:
                _message = self.message_factory.create_message(Event.BUMPER_PORT, self._port_triggered)
            elif self._stbd_triggered:
                _message = self.message_factory.create_message(Event.BUMPER_STBD, self._stbd_triggered)
            elif self._paft_triggered:
                _message = self.message_factory.create_message(Event.BUMPER_PAFT, self._paft_triggered)
            elif self._saft_triggered:
                _message = self.message_factory.create_message(Event.BUMPER_SAFT, self._saft_triggered)
            if _message is not None:
                self._log.info(Style.BRIGHT + 'bmp-publishing message:' + Fore.WHITE + Style.NORMAL + ' {}'.format(_message.name)
                        + Fore.CYAN + ' event: {}; '.format(_message.event.label) + Fore.YELLOW + 'timestamp: {}'.format(_message.value))
                await Publisher.publish(self, _message)
                self._reset_trigger(_message.event)

            await asyncio.sleep(self._publish_delay_sec)
        self._log.info('bmp publish loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _reset_trigger(self, event):
        '''
        Reset the trigger of the event sent (leaving others still triggered?).
        The special case is if the Event type is ANY, all triggers will be cleared.
        '''
        if event is Event.BUMPER_PORT:
            self._port_triggered = None
        elif event is Event.BUMPER_CNTR:
            self._cntr_triggered = None
        elif event is Event.BUMPER_STBD:
            self._stbd_triggered = None
        elif event is Event.BUMPER_PAFT:
            self._paft_triggered = None
        elif event is Event.BUMPER_MAST:
            self._mast_triggered = None
        elif event is Event.BUMPER_SAFT:
            self._saft_triggered = None
        elif event is Event.ANY:
            self._port_triggered = self._cntr_triggered = self._stbd_triggered \
                    = self._paft_triggered = self._mast_triggered = self._saft_triggered = None

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   def reset_trigger(self, orientation):
#       if orientation is Orientation.PORT:
#           self._port_triggered = None
#       elif orientation is Orientation.CNTR:
#           self._cntr_triggered = None
#       elif orientation is Orientation.STBD:
#           self._stbd_triggered = None
#       elif orientation is Orientation.PAFT:
#           self._paft_triggered = None
#       elif orientation is Orientation.MAST:
#           self._mast_triggered = None
#       elif orientation is Orientation.SAFT:
#           self._saft_triggered = None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def poll(self):
        '''
        Poll the bumper sensors, executing callbacks for each.
        '''
        self._log.info('poll...')
        _start_time = dt.now()
        # ...
        _delta = dt.now() - _start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        self._log.info(Fore.BLACK + '[{:04d}] poll end; elapsed processing time: {:d}ms'.format(self._count, _elapsed_ms))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher as well as shut down the message bus.
        '''
        self._message_bus.disable()
        Publisher.disable(self)
        self._log.info('disabled publisher.')

#EOF
