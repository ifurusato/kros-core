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
from core.orient import Orientation
from core.message import Message
from core.publisher import Publisher
from hardware.ifs import IntegratedFrontSensor

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class IfsPublisher(Publisher):

    CLASS_NAME = 'ifs'
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
        Publisher.__init__(self, IfsPublisher.CLASS_NAME, config, message_bus, message_factory, suppressed=False, level=self._level)
        # during calibration the IFS uses DEBUG level
        self._use_analog_pot  = config['kros'].get('integrated_front_sensor').get('use_analog_potentiometer')
        self._use_digital_pot = config['kros'].get('integrated_front_sensor').get('use_digital_potentiometer')
        self._ifs_level = ( Level.DEBUG if self._use_analog_pot or self._use_digital_pot  else self._level )
        self._ifs = IntegratedFrontSensor(config, message_bus=self.message_bus, message_factory=self.message_factory, level=self._ifs_level)
        # configuration ................
        self._counter = itertools.count()
        _cfg = config['kros'].get('publisher').get('integrated_front_sensor')
        _loop_freq_hz = _cfg.get('loop_freq_hz')
        self._log.info('ifs publish loop frequency: {:d}Hz'.format(_loop_freq_hz))
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
                self._ifs.enable()
                self._ifs.release()
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable publisher.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def toggle(self):
        self._log.info('👁️ ifs publisher: ' + Fore.YELLOW + 'suppressed? {}'.format(self.suppressed))
        if self.suppressed:
            self.release()
            self._log.info('👁️ ifs publisher: ' + Fore.YELLOW + 'released.')
        else:
            self.suppress()
            self._log.info('👁️ ifs publisher: ' + Fore.YELLOW + 'suppressed.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def release(self):
        '''
        Releases (un-suppresses) this Publisher.
        '''
        if not self.enabled:
            self._log.warning('ifs publisher not enabled.')
        else:
            Publisher.release(self)
            self._ifs.release()
            self._log.info('ifs publisher released.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def suppress(self):
        '''
        Suppresses this Publisher.
        '''
        if not self.enabled:
            self._log.warning('ifs publisher not enabled.')
        else:
            Publisher.suppress(self)
            self._ifs.suppress()
            self._log.info('ifs publisher suppressed.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _ifs_listener_loop(self, f_is_enabled):
        '''
        This polls each sensor in sequence on each loop iteration.
        '''
        self._log.info('starting infrared listener loop.')
        while f_is_enabled():
            _count = next(self._counter)
            for _orientation, n in list(enumerate([Orientation.CNTR, Orientation.PORT, Orientation.STBD, Orientation.PSID, Orientation.SSID])):
                self._log.info('polling infrared {} (n:{})...'.format(_orientation, n))
                _message = self._ifs.poll_infrared(_orientation)
                if _message:
                    if not isinstance(_message, Message):
                        raise Exception('expected Message, not {}'.format(type(_message)))
                    self._log.info(Style.BRIGHT + 'ifs-publishing message:' + Fore.WHITE + Style.NORMAL + ' {}'.format(_message.name)
                            + Fore.CYAN + ' event: {}; '.format(_message.event.label) + Fore.YELLOW + 'value: {:5.2f}cm'.format(_message.value))
                    await Publisher.publish(self, _message)
            await asyncio.sleep(self._publish_delay_sec)
        self._log.info('ifs publish loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher as well as the IntegratedFrontSensor.
        '''
        self._ifs.disable()
        Publisher.disable(self)
        self._log.info('disabled publisher.')

#EOF
