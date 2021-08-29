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
# _Getch at bottom.
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
from core.publisher import Publisher
from hardware.ifs import IntegratedFrontSensor

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class IfsPublisher(Publisher):

    _LISTENER_LOOP_NAME = '__ifs_listener_loop'

    '''
    A publisher for events from the Integrated Front Sensor, which contains
    five analog infrared sensors, a pair of light sensors used for a "moth"
    behaviour, and six lever switches wired in three pairs for bumpers.

    The bumpers are no longer managed by the IO Expander but here instead,
    connected directly to GPIO pins and using pigpio for interrupt handling.

    :param config:            the application configuration
    :param message_bus:       the asynchronous message bus
    :param message_factory:   the factory for creating messages
    :param level:             the log level
    '''
    def __init__(self, config, message_bus, message_factory, level=Level.INFO):
        if not isinstance(level, Level):
            raise ValueError('wrong type for log level argument: {}'.format(type(level)))
        self._level = level
        Publisher.__init__(self, 'ifs', config, message_bus, message_factory, level=self._level)
        # during calibration the IFS uses DEBUG level
        self._use_analog_pot  = config['kros'].get('integrated_front_sensor').get('use_analog_potentiometer')
        self._use_digital_pot = config['kros'].get('integrated_front_sensor').get('use_digital_potentiometer')
        self._ifs_level = ( Level.DEBUG if self._use_analog_pot or self._use_digital_pot  else self._level )
        self._ifs = IntegratedFrontSensor(config, message_bus=self.message_bus, message_factory=self.message_factory, level=self._ifs_level)
        # configuration ................
        self._group   = 0
        self._counter = itertools.count()
        _cfg = config['kros'].get('publisher').get('integrated_front_sensor')
        _loop_freq_hz        = _cfg.get('loop_freq_hz')
        self._publish_delay_sec = 1.0 / _loop_freq_hz
        self._port_bmp_pin   = _cfg.get('port_bmp_pin')
        self._cntr_bmp_pin   = _cfg.get('cntr_bmp_pin')
        self._stbd_bmp_pin   = _cfg.get('stbd_bmp_pin')
        self._one_shot       = _cfg.get('one_shot') # if true require reset before retriggering
        self._log.info('bumper pin assignments:\t' \
                + Fore.RED + ' port={:d};'.format(self._port_bmp_pin) \
                + Fore.BLUE + ' center={:d};'.format(self._cntr_bmp_pin) \
                + Fore.GREEN + ' stbd={:d}'.format(self._stbd_bmp_pin))
        self._pi             = None
        self._debounce_ms    = _cfg.get('debounce_ms') # 50ms default 
        self._debounce_µs    = self._debounce_ms * 1000 # callback uses microseconds
        self._port_triggered = None  # timestamps upon trigger, None if reset
        self._cntr_triggered = None
        self._stbd_triggered = None
        self._port_ticks     = 0
        self._cntr_ticks     = 0
        self._stbd_ticks     = 0
        self._initd          = False
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if not self._initd:
                try:
                    self._log.info('importing pigpio ...')
                    import pigpio
                    # establish pigpio interrupts for bumper pins
                    self._log.info('enabling bumper interrupts...')
                    self._pi = pigpio.pi()
                    if not self._pi.connected:
                        raise Exception('unable to establish connection to Pi.')
                    # configure port bumper callback .................
                    self._pi.set_mode(gpio=self._port_bmp_pin, mode=pigpio.INPUT)
                    _port_callback = self._pi.callback(self._port_bmp_pin, pigpio.FALLING_EDGE, self._port_callback_method)
                    self._log.info('configured port bumper callback on pin {:d}.'.format(self._port_bmp_pin))
                    # configure center bumper callback ...............
                    self._pi.set_mode(gpio=self._cntr_bmp_pin, mode=pigpio.INPUT)
                    _cntr_callback = self._pi.callback(self._cntr_bmp_pin, pigpio.FALLING_EDGE, self._cntr_callback_method)
                    self._log.info('configured cntr bumper callback on pin {:d}.'.format(self._cntr_bmp_pin))
                    # configure starboard bumper callback ............
                    self._pi.set_mode(gpio=self._stbd_bmp_pin, mode=pigpio.INPUT)
                    _stbd_callback = self._pi.callback(self._stbd_bmp_pin, pigpio.FALLING_EDGE, self._stbd_callback_method)
                    self._log.info('configured stbd bumper callback on pin {:d}.'.format(self._stbd_bmp_pin))
                except Exception as e:
                    self._log.warning('error configuring bumper interrupts: {}'.format(e))
                finally:
                    self._initd = True
            if self._message_bus.get_task_by_name(IfsPublisher._LISTENER_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                self._log.info('creating task for ifs listener loop...')
                self._message_bus.loop.create_task(self._ifs_listener_loop(lambda: self.enabled), name=IfsPublisher._LISTENER_LOOP_NAME)
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable publisher.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def reset_trigger(self, orientation):
        if orientation is Orientation.PORT:
            self._port_triggered = None
        elif orientation is Orientation.CNTR:
            self._cntr_triggered = None
        elif orientation is Orientation.STBD:
            self._stbd_triggered = None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _port_callback_method(self, gpio, level, ticks):
        if not self._port_triggered or not self._one_shot:
            if ticks - self._port_ticks > self._debounce_µs:
                self._port_triggered = dt.now()
                self._port_ticks = ticks
#               self._log.debug(Fore.RED + 'port bumper triggered on GPIO pin {}; logic level: {}; ticks: {}'.format(gpio, level, ticks))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _cntr_callback_method(self, gpio, level, ticks):
        if not self._cntr_triggered or not self._one_shot:
            if ticks - self._cntr_ticks > self._debounce_µs:
                self._cntr_triggered = dt.now()
                self._cntr_ticks = ticks
#               self._log.debug(Fore.BLUE + 'cntr bumper triggered on GPIO pin {}; logic level: {}; ticks: {}'.format(gpio, level, ticks))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _stbd_callback_method(self, gpio, level, ticks):
        if not self._stbd_triggered or not self._one_shot:
            if ticks - self._stbd_ticks > self._debounce_µs:
                self._stbd_triggered = dt.now()
                self._stbd_ticks = ticks
#               self._log.debug(Fore.GREEN + 'stbd bumper triggered on GPIO pin {}; logic level: {}; ticks: {}'.format(gpio, level, ticks))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _ifs_listener_loop(self, f_is_enabled):
        self._log.info('starting ifs listener loop:\t' + Fore.YELLOW + 'type \'?\' for help, \'q\' or Ctrl-C to exit.')
        while f_is_enabled():
            _count = next(self._counter)
            if self._cntr_triggered:
                _message = self.message_factory.create_message(Event.BUMPER_CNTR, self._cntr_triggered)
            elif self._port_triggered:
                _message = self.message_factory.create_message(Event.BUMPER_PORT, self._port_triggered)
            elif self._stbd_triggered:
                _message = self.message_factory.create_message(Event.BUMPER_STBD, self._stbd_triggered)
            else:
                _message = self._ifs.poll_cntr_infrared()
            if _message is not None:
                if Event.is_bumper_event(_message.event):
                    self._log.info(Style.BRIGHT + 'ifs-publishing message:' + Fore.WHITE + Style.NORMAL + ' {}'.format(_message.name)
                            + Fore.CYAN + ' event: {}; '.format(_message.event.label) + Fore.YELLOW + 'timestamp: {}'.format(_message.value))
                else:
                    self._log.info(Style.BRIGHT + 'ifs-publishing message:' + Fore.WHITE + Style.NORMAL + ' {}'.format(_message.name)
                            + Fore.CYAN + ' event: {}; '.format(_message.event.label) + Fore.YELLOW + 'value: {:5.2f}cm'.format(_message.value))
                await Publisher.publish(self, _message)
                # reset the trigger of the event sent (leaving others still triggered?)
                if _message.event is Event.BUMPER_PORT:
                    self._port_triggered = None
                elif _message.event is Event.BUMPER_CNTR:
                    self._cntr_triggered = None
                elif _message.event is Event.BUMPER_STBD:
                    self._stbd_triggered = None
#               if self._ifs_level != Level.DEBUG:
#                   self._log.info('ifs-published message:' + Fore.WHITE + ' {}'.format(_message.name)
#                           + Fore.CYAN + ' event: {}; '.format(_message.event.label) + Fore.YELLOW + 'value: {:5.2f}cm'.format(_message.value))
            await asyncio.sleep(self._publish_delay_sec)
        self._log.info('ifs publish loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def poll(self):
        '''
        Polls the Integrated Front Sensor.
        Poll the various infrared and bumper sensors, executing callbacks for each.
        In tests this typically takes 173ms using an ItsyBitsy, 85ms from a 
        Pimoroni IO Expander (which uses a Nuvoton MS51 microcontroller).

        The bumpers are handled via callbacks. 

        For the infrared sensors this uses 'poll groups' so that a specific group
        of IR sensors are read upon each poll:

          Group 0: the center infrared sensor
          Group 1: the oblique infrared sensors
          Group 2: the side infrared sensors

        Note that the bumpers are handled entirely differently, using a "charge pump" debouncer,
        running off a modulo of the clock TICKs.
        '''
        self._log.info('poll...')
        _group = self._get_sensor_group()

        self._log.info(Fore.YELLOW + '[{:04d}] sensor group: {}'.format(self._count, _group))
        _start_time = dt.now()
#       if _group == 0: # bumper group .........................................
#           self._log.info(Fore.WHITE + '[{:04d}] BUMP ifs poll start; group: {}'.format(self._count, _group))
#           self._poll_bumpers()
        if _group == 1: # center infrared group ..............................
            self._log.info(Fore.BLUE + '[{:04d}] CNTR ifs poll start; group: {}'.format(self._count, _group))
            self._ifs._poll_cntr_infrared()
        elif _group == 2: # oblique infrared group .............................
            self._log.info(Fore.YELLOW + '[{:04d}] OBLQ ifs poll start; group: {}'.format(self._count, _group))
            self._ifs._poll_oblique_infrared()
        elif _group == 3: # side infrared group ................................
            self._log.info(Fore.RED + '[{:04d}] SIDE ifs poll start; group: {}'.format(self._count, _group))
            self._ifs._poll_side_infrared()
        else:
            raise Exception('invalid group number: {:d}'.format(_group))
        _delta = dt.now() - _start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        self._log.info(Fore.BLACK + '[{:04d}] poll end; elapsed processing time: {:d}ms'.format(self._count, _elapsed_ms))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_sensor_group(self):
        '''
        Loops 0-3 to select the sensor group.
        '''
        if self._group == 2:
            self._group = 0
        else:
            self._group += 1
        self._log.info(Fore.BLACK + 'sensor group: {:d}'.format(self._group))
        return self._group

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher as well as shut down the message bus.
        '''
        self._message_bus.disable()
        Publisher.disable(self)
        self._log.info('disabled publisher.')

#EOF
