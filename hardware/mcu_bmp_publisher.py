#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-10-11
# modified: 2021-11-30
#
# lazily installs serial module
#

import os, itertools
import asyncio
from colorama import init, Fore, Style
init()

import core.globals as globals
globals.init()

from core.logger import Logger, Level
from core.dequeue import DeQueue
from core.event import Event
from core.orientation import Orientation
from core.publisher import Publisher

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class McuBumperPublisher(Publisher):

    _PUBLISHER_LOOP = '__mcu_bmp_publisher_loop'

    '''
    A Publisher that publishes messages from a microcontroller connected via
    UART connected to hardware bumpers.

    This is currently subclassing Publisher but more as an experiment as it
    actually relies upon the QueuePublisher for the actual passing of messages
    to the MessageBus, and hence could be downclassed to a Component. We'll
    see how performance works out before making that change.

    :param config:          the application configuration
    :param message_bus:     the asynchronous message bus
    :param message_factory: the factory for messages
    :param level:           the optional log level
    '''
    def __init__(self, config, message_bus, message_factory, level=Level.INFO):
        Publisher.__init__(self, 'mcu-bmp', config, message_bus, message_factory, suppressed=False, level=level)
        _cfg = self._config['kros'].get('publisher').get('mcu_bumper')

        self._queue_publisher = globals.get('queue-publisher')
        if self._queue_publisher:
            self._log.info('using queue publisher.')
        else:
            raise Exception('cannot continue: no queue publisher available.')

        _loop_freq_hz  = _cfg.get('loop_freq_hz')
        self._log.info('mcu bumper publisher loop frequency: {:d}Hz'.format(_loop_freq_hz))
        self._publish_delay_sec = 1.0 / _loop_freq_hz
        self._loop_delay_sec    = 0.1
        self._queue             = DeQueue()
        self._counter           = itertools.count()
        self._serial            = None
        # configure serial port ............................
        self._port = '/dev/serial0'
        # available:  50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800, 9600, 19200, 38400, 57600, 115200,
        # 230400, 460800, 500000, 576000, 921600, 1000000, 1152000, 1500000, 2000000, 2500000, 3000000, 3500000, 4000000
        self._baud_rate = 38400
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'mcu-bmp'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        if not self.enabled:
            self._serial = self.configure_serial_port()
            if self._serial:
                if self._message_bus.get_task_by_name(McuBumperPublisher._PUBLISHER_LOOP):
                    raise Exception('already enabled.')
                else:
                    Publisher.enable(self)
                    self._log.info('creating task for publisher loop...')
                    self._message_bus.loop.create_task(self._publisher_loop(lambda: self.enabled), name=McuBumperPublisher._PUBLISHER_LOOP)
                    self._log.info('enabled.')
            else:
                self._log.warning('cannot enable publisher loop: no serial interface available.')
        else:
            self._log.warning('failed to enable publisher loop.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def configure_serial_port(self):
        '''
        Configure and return an active serial port, None if unable.
        '''
        if not os.path.exists(self._port):
            self._log.info('disabled: port {} does not exist.'.format(self._port))
        else:
            self._log.info('starting serial port...\t' + Fore.YELLOW + 'type Ctrl-C to exit.')
            try:
                import serial
                return serial.Serial(port=self._port, baudrate=self._baud_rate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.5)
            except ModuleNotFoundError as e:
                self._log.error("This script requires the serial module\nInstall with: pip3 install --user serial")
            except Exception as e:
                self._log.error("{} thrown configuring the serial port: {}".format(type(e), e))
        return None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _publisher_loop(self, f_is_enabled):
        self._log.info('starting mcu bumper publisher loop:\t' + Fore.YELLOW + ( '; (suppressed, type \'m\' to release)' if self.suppressed else '(released)') )
        while f_is_enabled():
            _count = next(self._counter)
#           self._log.info('[{:03d}] begin publisher loop...'.format(_count))
            try:
#               self._log.info('waiting for serial read line... ')
                _bytes = self._serial.readline() # read until '\n' terminated line
#               self._log.debug('serial read line returned.')
                if len(_bytes) > 1:
                    _data = _bytes.decode('UTF-8')
                    if len(_data) == 5:
                        self._publish_message_for_orientation(Orientation.from_label(_data.strip()))
                    else:
                        self._log.warning('errant serial data \'{}\'; type: \'{}\'; length: {:d} chars.'.format(_data, type(_data), len(_data)))
#                   if not self.suppressed:
#                       while not self._queue.empty():
#                           _message = self._queue.poll()
#                           await Publisher.publish(self, _message)
#                           self._log.info('[{:03d}] published message '.format(_count)
#                                   + Fore.WHITE + '{} '.format(_message.name)
#                                   + Fore.CYAN + 'for event \'{}\' with value: '.format(_message.event.label)
#                                   + Fore.YELLOW + '{}'.format(_message.payload.value))
                await asyncio.sleep(self._loop_delay_sec)
            except UnicodeDecodeError as ude:
                self._log.error(Fore.BLACK + 'Unicode Decode Error: {} (ignoring)'.format(ude))
            await asyncio.sleep(self._publish_delay_sec)
        self._log.info('publisher loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def put(self, message):
        if not self.is_active:
            self._log.warning('message {} ignored: queue publisher inactive.'.format(message))
        else:
            self._queue.put(message)
            self._log.info('put message \'{}\' ({}) into queue ({:d} {})'.format(
                    message.event.label, message.name, self._queue.size, 'item' if self._queue.size == 1 else 'items'))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _publish_message_for_orientation(self, orientation):
        if orientation is Orientation.PORT:
            self._log.info('orientation:\t' + Fore.RED + Style.BRIGHT     + '{} ({})'.format(orientation.name, orientation.label))
            self._queue_publisher.put(self._message_factory.create_message(Event.BUMPER_PORT, None))
        elif orientation is Orientation.CNTR:
            self._log.info('orientation:\t' + Fore.BLUE + Style.BRIGHT    + '{} ({})'.format(orientation.name, orientation.label))
            self._queue_publisher.put(self._message_factory.create_message(Event.BUMPER_CNTR, None))
        elif orientation is Orientation.STBD:
            self._log.info('orientation:\t' + Fore.GREEN + Style.BRIGHT   + '{} ({})'.format(orientation.name, orientation.label))
            self._queue_publisher.put(self._message_factory.create_message(Event.BUMPER_STBD, None))
        elif orientation is Orientation.PAFT:
            self._log.info('orientation:\t' + Fore.CYAN + Style.BRIGHT    + '{} ({})'.format(orientation.name, orientation.label))
            self._queue_publisher.put(self._message_factory.create_message(Event.BUMPER_PAFT, None))
        elif orientation is Orientation.MAST:
            self._log.info('orientation:\t' + Fore.YELLOW + Style.BRIGHT  + '{} ({})'.format(orientation.name, orientation.label))
            self._queue_publisher.put(self._message_factory.create_message(Event.BUMPER_MAST, None))
        elif orientation is Orientation.SAFT:
            self._log.info('orientation:\t' + Fore.MAGENTA + Style.BRIGHT + '{} ({})'.format(orientation.name, orientation.label))
            self._queue_publisher.put(self._message_factory.create_message(Event.BUMPER_SAFT, None))
        else:
            self._log.warning('unmatched: \'{}\'; ({:d} chars)'.format(_data, len(_data)))

#EOF
