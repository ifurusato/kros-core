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

import itertools
import asyncio
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.message_factory import MessageFactory
from core.logger import Logger, Level
from core.event import Event
from core.publisher import Publisher

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class BumperPublisher(Publisher):
  
    CLASS_NAME = 'bmp'
    _LISTENER_LOOP_NAME = '__bmp_listener_loop'

    '''
    A publisher for bumper events from six lever switches wired in three pairs
    for bumpers, as well as aft and mast digital infrared sensors intended to
    catch non-physical "bumps", such as when backing up or upon the mast. The
    latter are connected directly to GPIO pins and use pigpio for interrupt
    handling.

    This publisher functions with the inputs mapped directly to the GPIO pins.
    The newer alternative to this Publisher is the ExternalBumperPublisher,
    where the bumpers are connected to an external microcontroller and their
    events are sent to the Pi using a bespoke 5 pin communications protocol.

    :param config:            the application configuration
    :param message_bus:       the asynchronous message bus
    :param message_factory:   the factory for creating messages
    :param level:             the log level
    '''
    def __init__(self, config, message_bus, message_factory, level=Level.INFO):
        if not isinstance(level, Level):
            raise ValueError('wrong type for log level argument: {}'.format(type(level)))
        self._level = level
        Publisher.__init__(self, BumperPublisher.CLASS_NAME, config, message_bus, message_factory, level=self._level)
        # configuration ................
        self._counter = itertools.count()
        self._pi             = None
        _cfg = config['kros'].get('publisher').get('bumper')
        _loop_freq_hz        = _cfg.get('loop_freq_hz')
        self._publish_delay_sec = 1.0 / _loop_freq_hz
        self._one_shot       = _cfg.get('one_shot') # if true require reset before retriggering
        self._debounce_ms    = _cfg.get('debounce_ms') # 50ms default
        self._debounce_µs    = self._debounce_ms * 1000 # callback uses microseconds
        self._reset_trigger(Event.ANY) # initialises all triggers
        self._reset_ticks(Event.ANY)   # initialises all tick counters
        self._initd          = False
        # pin assignments
        self._bmp_port_pin   = _cfg.get('bmp_port_pin')
        self._bmp_cntr_pin   = _cfg.get('bmp_cntr_pin')
        self._bmp_stbd_pin   = _cfg.get('bmp_stbd_pin')
        self._bmp_paft_pin   = _cfg.get('bmp_paft_pin')
        self._bmp_mast_pin   = _cfg.get('bmp_mast_pin')
        self._bmp_saft_pin   = _cfg.get('bmp_saft_pin')
        self._log.info('bumper pin assignments:\t' \
                + Fore.RED      + ' port={:d};'.format(self._bmp_port_pin) \
                + Fore.BLUE     + ' cntr={:d};'.format(self._bmp_cntr_pin) \
                + Fore.GREEN    + ' stbd={:d};'.format(self._bmp_stbd_pin))
        self._log.info(Fore.RED + ' paft={:d};'.format(self._bmp_paft_pin) \
                + Fore.BLUE     + ' mast={:d};'.format(self._bmp_mast_pin) \
                + Fore.GREEN    + ' saft={:d}'.format(self._bmp_saft_pin))
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
                    self._log.info('importing pigpio ...')
                    if not self._pi.connected:
                        raise Exception('unable to establish connection to Pi.')
                    # configure callbacks on the various bumpers.
                    self._log.info('configuring callbacks...')
                    # configure port bumper callback .............................
                    self._pi.set_mode(gpio=self._bmp_port_pin, mode=pigpio.INPUT)
                    _port_callback = self._pi.callback(self._bmp_port_pin, pigpio.FALLING_EDGE, self._port_callback_method)
                    self._log.info('configured port bumper callback on pin {:d}.'.format(self._bmp_port_pin))
                    # configure center bumper callback ...........................
                    self._pi.set_mode(gpio=self._bmp_cntr_pin, mode=pigpio.INPUT)
                    _cntr_callback = self._pi.callback(self._bmp_cntr_pin, pigpio.FALLING_EDGE, self._cntr_callback_method)
                    self._log.info('configured cntr bumper callback on pin {:d}.'.format(self._bmp_cntr_pin))
                    # configure starboard bumper callback ........................
                    self._pi.set_mode(gpio=self._bmp_stbd_pin, mode=pigpio.INPUT)
                    _stbd_callback = self._pi.callback(self._bmp_stbd_pin, pigpio.FALLING_EDGE, self._stbd_callback_method)
                    self._log.info('configured stbd bumper callback on pin {:d}.'.format(self._bmp_stbd_pin))
                    # configure port aft bumper callback .........................
                    self._pi.set_mode(gpio=self._bmp_paft_pin, mode=pigpio.INPUT)
                    _paft_callback = self._pi.callback(self._bmp_paft_pin, pigpio.FALLING_EDGE, self._paft_callback_method)
                    self._log.info('configured port aft bumper callback on pin {:d}.'.format(self._bmp_paft_pin))
                    # configure mast bumper callback .............................
                    self._pi.set_mode(gpio=self._bmp_mast_pin, mode=pigpio.INPUT)
                    _mast_callback = self._pi.callback(self._bmp_mast_pin, pigpio.FALLING_EDGE, self._mast_callback_method)
                    self._log.info('configured mast bumper callback on pin {:d}.'.format(self._bmp_mast_pin))
                    # configure starboard aft bumper callback ....................
                    self._pi.set_mode(gpio=self._bmp_saft_pin, mode=pigpio.INPUT)
                    _saft_callback = self._pi.callback(self._bmp_saft_pin, pigpio.FALLING_EDGE, self._saft_callback_method)
                    self._log.info('configured stbd aft bumper callback on pin {:d}.'.format(self._bmp_saft_pin))
                    self._log.info('callback configuration complete....')
                except Exception as e:
                    self._log.warning('error configuring bumper interrupts: {}'.format(e))
                finally:
                    self._initd = True
            if self._message_bus.get_task_by_name(BumperPublisher._LISTENER_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                self._log.info('creating task for bmp listener loop...')
                self._message_bus.loop.create_task(self._bmp_listener_loop(lambda: self.enabled), name=BumperPublisher._LISTENER_LOOP_NAME)
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable publisher.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _port_callback_method(self, gpio, level, ticks):
        if not self._port_triggered or not self._one_shot:
            if ticks - self._port_ticks > self._debounce_µs:
                self._port_triggered = dt.now()
                self._port_ticks = ticks
                self._log.info(Fore.RED + 'port bumper triggered on GPIO pin {}; logic level: {}; ticks: {}'.format(gpio, level, ticks))
        else:
            self._reset_ticks(Event.BUMPER_PORT)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _cntr_callback_method(self, gpio, level, ticks):
        if not self._cntr_triggered or not self._one_shot:
            if ticks - self._cntr_ticks > self._debounce_µs:
                self._cntr_triggered = dt.now()
                self._cntr_ticks = ticks
                self._log.info(Fore.BLUE + 'cntr bumper triggered on GPIO pin {}; logic level: {}; ticks: {}'.format(gpio, level, ticks))
        else:
            self._reset_ticks(Event.BUMPER_CNTR)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _stbd_callback_method(self, gpio, level, ticks):
        if not self._stbd_triggered or not self._one_shot:
            if ticks - self._stbd_ticks > self._debounce_µs:
                self._stbd_triggered = dt.now()
                self._stbd_ticks = ticks
                self._log.info(Fore.GREEN + 'stbd bumper triggered on GPIO pin {}; logic level: {}; ticks: {}'.format(gpio, level, ticks))
        else:
            self._reset_ticks(Event.BUMPER_STBD)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _paft_callback_method(self, gpio, level, ticks):
        if not self._paft_triggered or not self._one_shot:
            if ticks - self._paft_ticks > self._debounce_µs:
                self._paft_triggered = dt.now()
                self._paft_ticks = ticks
                self._log.info(Fore.RED + 'port aft bumper triggered on GPIO pin {}; logic level: {}; ticks: {}'.format(gpio, level, ticks))
        else:
            self._reset_ticks(Event.BUMPER_PAFT)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _mast_callback_method(self, gpio, level, ticks):
        if not self._mast_triggered or not self._one_shot:
            if ticks - self._mast_ticks > self._debounce_µs:
                self._mast_triggered = dt.now()
                self._mast_ticks = ticks
                self._log.info(Fore.BLUE + 'mast bumper triggered on GPIO pin {}; logic level: {}; ticks: {}'.format(gpio, level, ticks))
        else:
            self._reset_ticks(Event.BUMPER_MAST)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _saft_callback_method(self, gpio, level, ticks):
        if not self._saft_triggered or not self._one_shot:
            if ticks - self._saft_ticks > self._debounce_µs:
                self._saft_triggered = dt.now()
                self._saft_ticks = ticks
                self._log.info(Fore.GREEN + 'saft bumper triggered on GPIO pin {}; logic level: {}; ticks: {}'.format(gpio, level, ticks))
        else:
            self._reset_ticks(Event.BUMPER_SAFT)

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

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _reset_ticks(self, event):
        '''
        Reset the tick count of the event type. The special case is if the
        Event type is ANY, all will be cleared.
        '''
        if event is Event.BUMPER_PORT:
            self._port_ticks = 0
        elif event is Event.BUMPER_CNTR:
            self._cntr_ticks = 0
        elif event is Event.BUMPER_STBD:
            self._stbd_ticks = 0
        elif event is Event.BUMPER_PAFT:
            self._paft_ticks = 0
        elif event is Event.BUMPER_MAST:
            self._mast_ticks = 0
        elif event is Event.BUMPER_SAFT:
            self._saft_ticks = 0
        elif event is Event.ANY:
            self._port_ticks = self._cntr_ticks = self._stbd_ticks \
                    = self._paft_ticks = self._mast_ticks = self._saft_ticks = 0

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
