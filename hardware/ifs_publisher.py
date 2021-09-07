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
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if self._message_bus.get_task_by_name(IfsPublisher._LISTENER_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                self._log.info('creating task for ifs listener loop...')
                self._message_bus.loop.create_task(self._ifs_listener_loop(lambda: self.enabled), name=IfsPublisher._LISTENER_LOOP_NAME)
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable publisher.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _ifs_listener_loop(self, f_is_enabled):
        self._log.info('starting infrared listener loop.')
        while f_is_enabled():
            _count = next(self._counter)
            _message = self._ifs.poll_cntr_infrared()
            if _message is not None:
                self._log.info(Style.BRIGHT + 'ifs-publishing message:' + Fore.WHITE + Style.NORMAL + ' {}'.format(_message.name)
                        + Fore.CYAN + ' event: {}; '.format(_message.event.label) + Fore.YELLOW + 'value: {:5.2f}cm'.format(_message.value))
                await Publisher.publish(self, _message)
            await asyncio.sleep(self._publish_delay_sec)
        self._log.info('ifs publish loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def poll(self):
        '''
        Poll the various infrared sensors of the Integrated Front Sensor.
        This uses 'poll groups' so that a specific group of IR sensors are
        read upon each poll:

          Group 0: the center infrared sensor
          Group 1: the oblique infrared sensors
          Group 2: the side infrared sensors

        '''
        self._log.info('poll...')
        _group = self._get_sensor_group()
        self._log.info(Fore.YELLOW + '[{:04d}] sensor group: {}'.format(self._count, _group))
        _start_time = dt.now()
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
