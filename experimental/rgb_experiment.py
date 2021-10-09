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
import asyncio
import itertools
from datetime import datetime as dt
from colorama import init, Fore, Style
init(autoreset=True)

from core.logger import Logger, Level
from core.event import Event
from core.orient import Orientation
from core.publisher import Publisher
from experimental.experiment import Experiment

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
class RgbExperiment(Experiment, Publisher):

    _PUBLISHER_LOOP = '__rgb_publisher_loop'

    '''
    An experiment being able to send RGB messages.
    '''
    def __init__(self):
        Experiment.__init__(self, 'x-rgb')
        Publisher.__init__(self, self._name, config=self._config, message_bus=self._message_bus, 
                message_factory=self._message_factory, suppressed=True, level=self._level)
        self._counter   = itertools.count()
        self._loop_task   = None
        self._loop_delay_sec = 0.5 # _cfg.get('loop_delay_sec')
        self._sic_transit_gloria_mundi = False
#       self._ext_clock.add_callback(self._callback)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        self._log.info('⭐ enabling...')
        if self.enabled:
            self._log.warning('already enabled.')
        else:
            self._configure()
            Experiment.enable(self)
            Publisher.enable(self)
            self._log.info('⭐ enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        self._log.info('⭐ disabling...')
        Experiment.disable(self)
        Publisher.disable(self)
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
        try:

            self._log.info('⭐ configuring...')
#           coro = serial_asyncio.create_serial_connection(self._message_bus.loop, Output, _port, baudrate=_baud_rate)
#           self._message_bus.loop.run_until_complete(coro)
            self._loop_task = self._message_bus.loop.create_task(self._publisher_loop(lambda: self.enabled), name=RgbExperiment._PUBLISHER_LOOP)
            self.release() # FIXME TEMP
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
            _start_time = dt.now()
            _count = next(self._counter)
            if not self.suppressed:
                self._log.info('[{:03d}] ⭐ begin publisher loop; suppressed: {}'.format(_count, self.suppressed))
                if _count > 1 and not self._sic_transit_gloria_mundi:
                    self._sic_transit_gloria_mundi = True
                    self._log.info(Fore.MAGENTA + '⭐ processing...')
                    try:

                        self._log.info('😛 waiting for gotod... ')
                        _packet = 'r100,g226,b90'
                        _message = self.message_factory.create_message(Event.RGB, _packet)
                        await self._message_bus.publish_message(_message)

                    except KeyboardInterrupt:
                        self._log.info('Ctrl-C caught; exiting...')
                    except Exception as e:
                        self._log.error('{} encountered, exiting: {}'.format(type(e), e))
                        traceback.print_exc(file=sys.stdout)
                    finally:
                        _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
                        self._log.info(Style.DIM + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))
                        self._sic_transit_gloria_mundi = False
                else:
                    self._log.info(Fore.MAGENTA + Style.DIM + '⭐ currently processing...')
                # once around the mulberry bush...
                self.suppress()

#           self._log.info(Fore.MAGENTA + Style.DIM + '⭐ loop delay; enabled: {}'.format(f_is_enabled()))
            await asyncio.sleep(self._loop_delay_sec)

        self._log.info(Fore.MAGENTA + '⭐ publisher loop complete. 🍠 ')

## ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#def main():
#
#    _log = Logger('test', Level.INFO)
#
#    _log.info('creating RgbExperiment...')
#    _experiment = RgbExperiment()
#    _log.info('created RgbExperiment.')
#    _experiment.enable()
#
#if __name__== "__main__":
#    main()

#EOF
