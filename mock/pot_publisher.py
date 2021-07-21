#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-06-26
#

from abc import ABC, abstractmethod
import itertools
import asyncio
from math import isclose
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.fsm import State
from core.event import Event, Group
from core.util import Util
from core.subscriber import Subscriber
from core.publisher import Publisher
from mock.potentiometer import Potentiometer
from behave.trigger_behaviour import TriggerBehaviour

# ...............................................................
class PotentiometerPublisher(Publisher):

    _PUBLISHER_LOOP = '__pot_publisher_loop'

    '''
    A Publisher that publishes motor speed controls from a digital potentiometer.

    :param name:            the name of this behaviour
    :param config:          the application configuration
    :param message_bus:     the asynchronous message bus
    :param message_factory: the factory for messages
    :param level:           the optional log level
    '''
    def __init__(self, config, message_bus, message_factory, level=Level.INFO):
        Publisher.__init__(self, 'pot', config, message_bus, message_factory, suppressed=False, level=level)
        _cfg = self._config['kros'].get('mock').get('pot_publisher')
        self._loop_delay_sec = _cfg.get('loop_delay_sec') # 0.05 is 50ms/20Hz, so each loop is 1/20th second or 20 loops/sec
        self._publish_loop_running = False
        self._counter              = itertools.count()
        self._last_scaled_value    = -999.0
        self._pot = Potentiometer(config, level)
        self._pot.set_output_limits(-90, 90)
        self._hysteresis_value     = 3.0
        self._hysteresis = lambda n: n if ( n < ( -1 * self._hysteresis_value ) or n > self._hysteresis_value ) else 0.0
        self._log.info('ready.')

    # ..........................................................................
    def get_trigger_behaviour(self, event):
        return TriggerBehaviour.TOGGLE # or RELEASE

    # ..........................................................................
    @property
    def trigger_event(self):
        '''
        This returns the event used to enable/disable the behaviour manually.
        '''
        return Event.AVOID

    # ..........................................................................
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        if self.state is not State.STARTED:
            Publisher.start(self)

    # ................................................................
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if self._message_bus.get_task_by_name(PotentiometerPublisher._PUBLISHER_LOOP) or self._publish_loop_running:
                raise Exception('already enabled.')
#               self._log.warning('already enabled.')
            else:
                self._log.info('creating task for publisher loop...')
                self._publish_loop_running = True
                self._message_bus.loop.create_task(self._publisher_loop(lambda: self.enabled), name=PotentiometerPublisher._PUBLISHER_LOOP)
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable publisher loop.')

    # ..........................................................................
    def callback(self):
        self._log.info('👾 pot callback.')

    # ..........................................................................
    @property
    def name(self):
        return 'pot_publisher'

    # ................................................................
    async def _publisher_loop(self, f_is_enabled):
        '''
        We get a message from the queue and publish it.

        Then we loop. The published message's value is the number
        of loop ticks to wait until getting the next message.

        We continue to loop but without getting another message 
        until the delay_tick_counter reaches zero.
        '''
        self._log.info('starting pot publisher loop:\t' + Fore.YELLOW + ( '; (suppressed, type \'m\' to release)' if self.suppressed else '.') )
        while f_is_enabled():
            _count = next(self._counter)
            self._log.debug('[{:03d}] begin publisher loop...'.format(_count))
            if not self.suppressed:
                self._log.debug('[{:03d}] publisher released.'.format(_count))

                # get value with hysteresis around zero
                _scaled_value = self._hysteresis(round(self._pot.get_scaled_value(False)))
                if _scaled_value != self._last_scaled_value: # if not the same as last time
                    if isclose(_scaled_value, 0.0, abs_tol=1e-2):
                        self._pot.set_black()
                    else:
                        self._pot.set_rgb(self._pot.value)
                    self._log.info(Fore.YELLOW + '[{:03d}] pot value; {:<5.2f}'.format(_count, _scaled_value))
                    # populate message with value and publish...
                    _message = self._message_factory.create_message(Event.VELOCITY, _scaled_value)
                    self._log.info('💠 publishing message:' + Fore.WHITE + ' {}; event: {} with value: {}'.format(_message.name, _message.event.label, _message.payload.value))
                    await Publisher.publish(self, _message)
                    self._log.info('published message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.label))
                self._last_scaled_value = _scaled_value
            else:
                self._log.debug('[{:03d}] publisher suppressed.'.format(_count))

            await asyncio.sleep(self._loop_delay_sec)
            self._log.debug('[{:03d}] end of loop.'.format(_count))

        self._log.info('publisher loop complete.')

    # ..........................................................................
    def execute(self, message):
        '''
        The method called upon each loop iteration. This receives a message and
        executes a ballistic behaviour for either a bumper or infrared event (if
        the latter is closer than a specified threshold distance).

        :param message:  an optional Message passed along by the message bus
        '''
        raise Exception('what is this doing here?')

#EOF
