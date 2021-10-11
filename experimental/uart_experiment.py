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

serial_asyncio_available = False
try:
    import serial_asyncio
    import aioserial
    import asyncio
    serial_asyncio_available = True
except ModuleNotFoundError as e:
    raise Exception('unable to load module: {}; install using: sudo pip3 install pyserial-asyncio; using mock.'.format(e))
#   print('unable to load module: {}; using mock.'.format(e))

import itertools
from datetime import datetime as dt
from colorama import init, Fore, Style
init(autoreset=True)

import core.globals as globals
globals.init()

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
        self._counter   = itertools.count()
        self._queue_publisher = globals.get('queue-publisher')
        self._loop_task   = None
        self._loop_delay_sec = 0.05 # _cfg.get('loop_delay_sec')
        self._sic_transit_gloria_mundi = False
#       self._ext_clock.add_callback(self._callback)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        if self.enabled:
            self._log.warning('⭐ already enabled.')
        else:
            self._log.info('⭐ enabling...')
            self._configure()
            self._log.info('❄️  enabling A. enabled: {}'.format(self.enabled))
            Experiment.enable(self)
            self._log.info('❄️  enabling B. enabled: {}'.format(self.enabled))
            Publisher.enable(self)
            self._log.info('❄️  enabling C. enabled: {}'.format(self.enabled))
            self._log.info('⭐ enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        self._log.info('❄️  disabling 1. enabled: {}'.format(self.enabled))
        Experiment.disable(self)
        self._log.info('❄️  disabling 2. enabled: {}'.format(self.enabled))
        Publisher.disable(self)
        self._log.info('❄️  disabling 3. enabled: {}'.format(self.enabled))
        if self._serial:
            try:
                self._log.info('⭐ closing serial port...')
                self._serial.close()
                self._log.info('⭐ closed serial port.')
            except Exception as e:
                self._log.error('⭐ error closing  serial port: {}'.format(e))
        if self._loop_task:
            try:
                self._log.info('⭐ cancelling loop task...')
                self._loop_task.cancel()
                self._log.info('⭐ cancelled loop task.')
            except Exception as e:
                self._log.error('⭐ error closing  serial port: {}'.format(e))
            finally:
                self._loop_task = None
        self._log.info('⭐ disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _configure(self):
        self._log.info('⭐ configuring...')
        _port = '/dev/serial0'
        _baud_rate = 38400
#       (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400,
#        460800, 500000, 576000, 921600, 1000000, 1152000, 1500000, 2000000, 2500000, 3000000, 3500000, 4000000)

#       _loop = self._message_bus.loop

        try:
#           self._serial = serial.Serial(port='/dev/serial0', baudrate=19200) #parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE) # timeout=1)
#           self._serial = serial.Serial(port=_port, baudrate=_baud_rate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE) # timeout=1)

            if serial_asyncio_available and os.path.exists(_port):
#                   raise Exception('port {} does not exist.'.format(_port))
                self._serial = None
#               self._serial = aioserial.AioSerial(port=_port, baudrate=_baud_rate, parity=aioserial.PARITY_NONE, stopbits=aioserial.STOPBITS_ONE, \
#                   loop=self._message_bus.loop, cancel_read_timeout=1, cancel_write_timeout=1) # timeout=1)

#                loop = asyncio.get_event_loop()
#                _coro = serial_asyncio.create_serial_connection(loop, Output, _port, baudrate=_baud_rate)
#                loop.run_until_complete(_coro)
#                loop.run_forever()

                self._log.info('⭐ configuring serial_asyncio...')
#               loop = asyncio.get_event_loop()

#               _coro = serial_asyncio.create_serial_connection(self._message_bus.loop, Output, _port, baudrate=_baud_rate)

                self._loop_task = self._message_bus.loop.create_task(self._publisher_loop(lambda: self.enabled), name=UartExperiment._PUBLISHER_LOOP)
#               self._message_bus.loop.run_until_complete(_coro)
#               _loop.run_forever()


            else:
                self._log.info('⭐ using mock serial_asyncio...')
#               self._serial = MockAioSerial()
                self._serial = MockSerialAsyncio(_loop, Output)

            self.release() 
            self._log.info('⭐ configured.')

        except Exception as e:
            self._log.error('{} encountered, exiting: {}'.format(type(e), e))
            traceback.print_exc(file=sys.stdout)
            self.disable()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _publisher_loop(self, f_is_enabled):
        if not self.enabled:
            self._log.warning('⭐ not enabled.')
            return
        self._log.info(Fore.MAGENTA + '⭐ start publisher loop; enabled: {}'.format(f_is_enabled()))
        while f_is_enabled():
            _count = next(self._counter)
            self._log.info('[{:03d}] ⭐ begin publisher loop; suppressed: {}'.format(_count, self.suppressed))
            if _count > 10 and not self.suppressed:
                if not self._sic_transit_gloria_mundi:
                    self._sic_transit_gloria_mundi = True
                    self._log.info(Fore.MAGENTA + '⭐ processing...')
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
#                               self._queue_publisher.put(_message)
                                self._log.info('🤡 😛 PUBLISHING MESSAGE HERE... ')

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
                    self._log.info(Fore.MAGENTA + Style.DIM + '⭐ currently processing...')

            self._log.info(Fore.MAGENTA + Style.DIM + '⭐ loop delay; enabled: {}'.format(f_is_enabled()))
            await asyncio.sleep(self._loop_delay_sec)

        self._log.info(Fore.MAGENTA + '⭐ publisher loop complete. 🍠 ')


## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MockSerialAsyncio(object):

    def __init__(self, loop, output_class, level=Level.INFO):
        self._log = Logger('mock-ser-async', level)
        self._loop = loop
        self._output = output_class()
        self._log.info('ready');

    def close(self):
        pass

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MockAioSerial(object):

    def __init__(self):
        pass

    async def read_until_async(self): # read until '\n' terminated line
        return 'mast\n'

    def close(self):
        pass

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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Output(asyncio.Protocol):

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def connection_made(self, transport):
        self.transport = transport
        print(Fore.GREEN + 'port opened'.format(transport))
        transport.serial.rts = False  # You can manipulate Serial object via transport
        transport.write(b'Hello, World!\n')  # Write serial data via transport

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def data_received(self, data):
        global g_counter
        _count = next(g_counter)
        print(Fore.YELLOW + 'data {:d} received: {}'.format(_count, repr(data)))
        if b'\n' in data and _count > 5:
            self.transport.close()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def connection_lost(self, exc):
        print(Fore.RED + 'port closed')
        self.transport.loop.stop()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def pause_writing(self):
        print(Fore.MAGENTA + 'pause writing')
        print(self.transport.get_write_buffer_size())

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print(Fore.CYAN + 'resume writing')


## ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈┈ ┈┈┈
#loop = None
#
#g_counter = itertools.count()
#
#try:
#
#except KeyboardInterrupt:
#    print(Style.BRIGHT + 'caught Ctrl-C; exiting...' + Style.RESET_ALL)
#except Exception as e:
#    print(e)
#finally:
#    if loop:
#        loop.close()
#
#
