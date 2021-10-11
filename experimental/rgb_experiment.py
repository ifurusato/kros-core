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
import asyncio, random, itertools
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
from hardware.color import Color

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
class RgbExperiment(Experiment, Publisher):

    _PUBLISHER_LOOP = '__rgb_publisher_loop'

    '''
    An experiment being able to send RGB messages.

    This uses the QueuePublisher if available, otherwise publishes directly
    to the MessageBus.
    '''
    def __init__(self):
        Experiment.__init__(self, 'rgb')
        Publisher.__init__(self, self._name, config=self._config, message_bus=self._message_bus,
                message_factory=self._message_factory, suppressed=True, level=self._level)
        self._counter        = itertools.count()
        self._loop_task      = None
        self._loop_delay_sec = 0.5 # _cfg.get('loop_delay_sec')
        self._sic_transit_gloria_mundi = False
        self._fixed_color    = False
        self._random_color   = True # enable randomly-selected Color
        self._all_colors     = Color.all_colors()
        self._log.info('using {:d} predefined colors.'.format(len(self._all_colors)))
        self._queue_publisher = globals.get('queue-publisher')
        if self._queue_publisher:
            self._log.info('💕 using queue publisher.')
        else:
            self._log.info('💕 publishing directly to message bus.')
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        self._log.info('enabling...')
        if self.enabled:
            self._log.warning('already enabled.')
        else:
            self._configure()
            Experiment.enable(self)
            Publisher.enable(self)
            self._log.info('enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        Experiment.disable(self)
        Publisher.disable(self)
        if self._loop_task:
            try:
                self._loop_task.cancel()
            finally:
                self._loop_task = None
        self._log.info('disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _configure(self):
        if self._loop_task:
            self._log.warning('already configured.')
        else:
            try:
                self._log.info('configuring...')
                self._loop_task = self._message_bus.loop.create_task(self._publisher_loop(lambda: self.enabled), name=RgbExperiment._PUBLISHER_LOOP)
#               self.release() # FIXME TEMP
                self._log.info('configured.')
            except Exception as e:
                self._log.error('{} encountered, exiting: {}'.format(type(e), e))
                traceback.print_exc(file=sys.stdout)
                self.disable()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _publisher_loop(self, f_is_enabled):
        if not self.enabled:
            self._log.warning('not enabled.')
            return
        self._log.info('start publisher loop')
        while f_is_enabled():
            _start_time = dt.now()
            _count = next(self._counter)
            if not self.suppressed:
#               self._log.info('[{:03d}] begin publisher loop.'.format(_count))
                if _count > 1 and not self._sic_transit_gloria_mundi:
                    self._sic_transit_gloria_mundi = True
                    try:
                        _message = self.message_factory.create_message(Event.RGB, self.get_color())
                        if self._queue_publisher:
                            self._queue_publisher.put(_message)
                        else:
                            await self._message_bus.publish_message(_message)
                    except Exception as e:
                        self._log.error('{} encountered, exiting: {}'.format(type(e), e))
                        traceback.print_exc(file=sys.stdout)
                    finally:
                        _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
                        self._log.info(Style.DIM + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))
                        self._sic_transit_gloria_mundi = False
                # once complete re-suppress...
                self.suppress()

            await asyncio.sleep(self._loop_delay_sec)

        self._log.info('publisher loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_color(self):
        '''
        Return a fixed color, a randomly-selected Color, or a randomly-generated
        RGB color.
        '''
        if self._fixed_color:
            return Color.SKY_BLUE
        elif self._random_color and bool(random.getrandbits(1)):
            _color = self._all_colors[random.randint(0, len(self._all_colors)-1)]
            self._log.info('randomly selecting color: {}'.format(_color))
            return _color
        else:
            _max = 64 # 255
            rgb = ( random.randint(0, _max), random.randint(0, _max), random.randint(0, _max) )
            self._log.info('generating random color: {},{},{}'.format(*rgb))
            return rgb

#EOF
