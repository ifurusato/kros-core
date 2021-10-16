#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-10-15
# modified: 2021-10-16
#

import random

import core.globals as globals
globals.init()

from core.logger import Logger, Level
from core.event import Event
from core.publisher import Publisher
from experimental.experiment import Experiment
from hardware.color import Color

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
class RgbRandom(Experiment, Publisher):
    '''
    An experiment being able to send RGB messages.

    This uses the QueuePublisher if available, otherwise publishes directly
    to the MessageBus.
    '''
    def __init__(self):
        Experiment.__init__(self, 'rgb')
        Publisher.__init__(self, self._name, config=self._config, message_bus=self._message_bus,
                message_factory=self._message_factory, suppressed=True, level=self._level)
        self._fixed_color    = False
        self._random_color   = True # enable randomly-selected Color
        self._all_colors     = Color.all_colors()
        self._log.info('using {:d} predefined colors.'.format(len(self._all_colors)))
        self._queue_publisher = globals.get('queue-publisher')
        if self._queue_publisher:
            self._log.info('using queue publisher.')
        else:
            self._log.info('publishing directly to message bus.')
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'rgb-random'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def suppress(self):
        Publisher.suppress(self)
        Experiment.suppress(self)
        self.clear()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def release(self):
        Publisher.release(self)
        Experiment.release(self)
        if self._queue_publisher:
            self._queue_publisher.put(self._message_factory.create_message(Event.RGB, self.get_color()))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        self._log.info('enabling...')
        if self.enabled:
            self._log.warning('already enabled.')
        else:
            Experiment.enable(self)
            Publisher.enable(self)
            self._log.info('enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        self.clear()
        Experiment.disable(self)
        Publisher.disable(self)
        self._log.info('disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def clear(self):
        if self._queue_publisher:
            self._queue_publisher.put(self._message_factory.create_message(Event.RGB, Color.BLACK))

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
            _max = 255
            rgb = ( random.randint(0, _max), random.randint(0, _max), random.randint(0, _max) )
            self._log.info('generating random color: {},{},{}'.format(*rgb))
            return rgb

#EOF
