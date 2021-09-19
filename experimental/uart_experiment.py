#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-09-10
# modified: 2021-09-13
#
# see: https://pypi.org/project/aioserial/
# see: https://pyserial-asyncio.readthedocs.io/en/latest/
# see: https://pythonhosted.org/pyserial/shortintro.html
#

import os, sys, time, traceback
#import serial
try:
    import aioserial
    import asyncio
except Exception as e:
    print('exception type: {}'.format(type(e)))
import itertools
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event
from core.orient import Orientation
from core.publisher import Publisher

from experimental.experiment import Experiment

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
class UartExperiment(Experiment, Publisher):

    _PUBLISHER_LOOP = '__uart_publisher_loop'

    '''
    An experiment using a UART to receive messages.
    '''
    def __init__(self):
        Experiment.__init__(self, 'x-uart')
        Publisher.__init__(self, self._name, config=self._config, message_bus=self._message_bus, 
                message_factory=self._message_factory, suppressed=True, level=self._level)
        self._serial  = None
        self._counter = itertools.count()
        self._loop_delay_sec = 0.05 # _cfg.get('loop_delay_sec')
        self._sic_transit_gloria_mundi = False
#       self._ext_clock.add_callback(self._callback)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):

        if self.enabled:
            self._log.warning('💊 already enabled.')
        else:
            self._log.info('💊 enabling...')
            self._configure()
#           Experiment.enable(self)
            Publisher.enable(self)
            self._log.info('💊 enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _configure(self):
        self._log.info('💊 configuring...')
        _port = '/dev/serial0'
        _baud_rate = 38400
#       (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400,
#        460800, 500000, 576000, 921600, 1000000, 1152000, 1500000, 2000000, 2500000, 3000000, 3500000, 4000000)
        try:
            if not os.path.exists(_port):
                raise Exception('port {} does not exist.'.format(_port))
#           self._serial = serial.Serial(port='/dev/serial0', baudrate=19200) #parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE) # timeout=1)
#           self._serial = serial.Serial(port=_port, baudrate=_baud_rate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE) # timeout=1)

            self._serial = aioserial.AioSerial(port=_port, baudrate=_baud_rate, parity=aioserial.PARITY_NONE, stopbits=aioserial.STOPBITS_ONE, \
                loop=self._message_bus.loop, cancel_read_timeout=1, cancel_write_timeout=1) # timeout=1)

            self._message_bus.loop.create_task(self._publisher_loop(lambda: self.enabled), name=UartExperiment._PUBLISHER_LOOP)

            self.release() # FIXME TEMP

            self._log.info('💊 configured.')
        except Exception as e:
            self._log.error('{} encountered, exiting: {}'.format(type(e), e))
            traceback.print_exc(file=sys.stdout)
            self.disable()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _publisher_loop(self, f_is_enabled):
        if not self.enabled:
            self._log.warning('💊 not enabled.')
            return
        self._log.info(Fore.MAGENTA + '💊 start publisher loop...')
        while f_is_enabled():
            _count = next(self._counter)
            self._log.info('[{:03d}] 💊 begin publisher loop; suppressed: {}'.format(_count, self.suppressed))
            if _count > 10 and not self.suppressed:
                if not self._sic_transit_gloria_mundi:
                    self._sic_transit_gloria_mundi = True
                    self._log.info(Fore.MAGENTA + '💊 processing...')
                    _start_time = dt.now()
                    try:
                        self._log.info('😛 waiting for serial read line... ')
        
        #               _bytes = await self._serial.readline_async() # read until '\n' terminated line
                        _bytes = await self._serial.read_until_async() # read until '\n' terminated line
        
                        self._log.debug('serial read line returned.')
                        if len(_bytes) > 1:
                            _data = _bytes.decode('UTF-8')
                            if len(_data) == 5:
                                _label = _data.strip()
                                _orientation = Orientation.from_label(_label)
                                if _orientation is Orientation.PORT:
                                    self._log.info('orientation:\t' + Fore.RED + Style.BRIGHT     + '{} ({})'.format(_orientation.name, _orientation.label))
                                elif _orientation is Orientation.CNTR:
                                    self._log.info('orientation:\t' + Fore.BLUE + Style.BRIGHT    + '{} ({})'.format(_orientation.name, _orientation.label))
                                elif _orientation is Orientation.STBD:
                                    self._log.info('orientation:\t' + Fore.GREEN + Style.BRIGHT   + '{} ({})'.format(_orientation.name, _orientation.label))
                                elif _orientation is Orientation.PAFT:
                                    self._log.info('orientation:\t' + Fore.CYAN + Style.BRIGHT    + '{} ({})'.format(_orientation.name, _orientation.label))
                                elif _orientation is Orientation.MAST:
                                    self._log.info('orientation:\t' + Fore.YELLOW + Style.BRIGHT  + '{} ({})'.format(_orientation.name, _orientation.label))
                                elif _orientation is Orientation.SAFT:
                                    self._log.info('orientation:\t' + Fore.MAGENTA + Style.BRIGHT + '{} ({})'.format(_orientation.name, _orientation.label))
                                else:
                                    self._log.warning('unmatched: \'{}\'; ({:d} chars)'.format(_data, len(_data)))

                                # FIXME publish message here...

                            else:
                                self._log.warning('🤡 errant data \'{}\'; type: \'{}\'; length: {:d} chars.'.format(_data, type(_data), len(_data)))
#                           time.sleep(0.1)
                    except UnicodeDecodeError as ude:
                        self._log.error(Fore.BLACK + 'Unicode Decode Error: {} (ignoring)'.format(ude))
                    except KeyboardInterrupt:
                        self._log.info('Ctrl-C caught; exiting...')
                    except Exception as e:
                        self._log.error('{} encountered, exiting: {}'.format(type(e), e))
                        traceback.print_exc(file=sys.stdout)
                    finally:
                        _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
                        self._log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))
                        self._sic_transit_gloria_mundi = False
                else:
                    self._log.info(Fore.MAGENTA + Style.DIM + '💊 currently processing...')

            self._log.info(Fore.MAGENTA + Style.DIM + '💊 loop delay...')
            await asyncio.sleep(self._loop_delay_sec)

## ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#def main():
#
#    _log = Logger('test', Level.INFO)
#
#    _log.info('creating UartExperiment...')
#    _experiment = UartExperiment()
#    _log.info('created UartExperiment.')
#    _experiment.enable()
#
#if __name__== "__main__":
#    main()

#EOF
