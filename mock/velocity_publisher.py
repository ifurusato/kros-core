#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-08-17
#
# MockPotentiometer at bottom.
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
from behave.trigger_behaviour import TriggerBehaviour

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class VelocityPublisher(Publisher):

    _PUBLISHER_LOOP = '__velocity_publisher_loop'

    '''
    A Publisher that publishes motor target velocity controls from a digital
    potentiometer.

    :param name:            the name of this behaviour
    :param config:          the application configuration
    :param message_bus:     the asynchronous message bus
    :param message_factory: the factory for messages
    :param level:           the optional log level
    '''
    def __init__(self, config, message_bus, message_factory, level=Level.INFO):
        Publisher.__init__(self, 'velo', config, message_bus, message_factory, suppressed=False, level=level)
        _cfg = self._config['kros'].get('mock').get('velocity_publisher')
        self._loop_delay_sec = _cfg.get('loop_delay_sec') # 0.05 is 50ms/20Hz, so each loop is 1/20th second or 20 loops/sec
        if not isinstance(level, Level):
            raise ValueError('wrong type for log level argument: {}'.format(type(level)))
        self._publish_loop_running = False
        self._counter              = itertools.count()
        self._last_scaled_value    = 0.0
        try:
            from hardware.digital_pot import DigitalPotentiometer
            self._pot = DigitalPotentiometer(config, level=level)
        except Exception as e:
            self._log.warning('using mock, could not start hardware potentiometer; error: {}'.format(e))
            self._pot = MockPotentiometer(level)
            self._pot.set_output_limits(-90, 90)
        _hysteresis_value          = _cfg.get('hysteresis')
        self._hysteresis = lambda n: n if ( n < ( -1 * _hysteresis_value ) or n > _hysteresis_value ) else 0.0
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_trigger_behaviour(self, event):
        return TriggerBehaviour.TOGGLE # or RELEASE

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def trigger_event(self):
        '''
        This returns the event used to enable/disable the behaviour manually.
        '''
        return Event.AVOID

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        if self.state is not State.STARTED:
            Publisher.start(self)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if self._message_bus.get_task_by_name(VelocityPublisher._PUBLISHER_LOOP) or self._publish_loop_running:
                raise Exception('already enabled.')
#               self._log.warning('already enabled.')
            else:
                self._log.info('creating task for publisher loop...')
                self._publish_loop_running = True
                self._message_bus.loop.create_task(self._publisher_loop(lambda: self.enabled), name=VelocityPublisher._PUBLISHER_LOOP)
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable publisher loop.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def callback(self):
        self._log.info('👾 pot callback.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'pot'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _publisher_loop(self, f_is_enabled):
        '''
        After ignoring the first few messages to avoid pot startup noise,
        we look for changing values and publish them to the message bus.
        '''
        self._log.info('starting pot publisher loop:\t' + Fore.YELLOW + ( '; (suppressed, type \'m\' to release)' if self.suppressed else '(released)') )
        while f_is_enabled():
            _count = next(self._counter)
            self._log.debug('[{:03d}] begin publisher loop...'.format(_count))
            if _count > 10 and not self.suppressed:
                self._log.debug('[{:03d}] publisher released.'.format(_count))
                # get value with hysteresis around zero
                _scaled_value = self._pot.get_scaled_value(False)
#               _scaled_value = self._hysteresis(round(_scaled_value))
                if _scaled_value != self._last_scaled_value: # if not the same as last time
                    if isclose(_scaled_value, 0.0, abs_tol=0.05 * 90):
                        self._pot.set_black()
                        _message = self._message_factory.create_message(Event.VELOCITY, 0.0)
                    else:
                        self._pot.set_rgb(self._pot.value)
                        _message = self._message_factory.create_message(Event.VELOCITY, _scaled_value)
                    # populate message with value and publish...
                    self._log.debug('publishing message: {}; event: {} '.format(_message.name, _message.event.label) 
                             + Fore.WHITE + ' with value: {:5.2f}'.format(_message.payload.value))
                    await Publisher.publish(self, _message)
                self._last_scaled_value = _scaled_value
            else:
                self._log.debug('[{:03d}] publisher suppressed.'.format(_count))

            await asyncio.sleep(self._loop_delay_sec)
            self._log.debug('[{:03d}] end of loop.'.format(_count))

        self._log.info('publisher loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def execute(self, message):
        '''
        The method called upon each loop iteration. This receives a message and
        executes a ballistic behaviour for either a bumper or infrared event (if
        the latter is closer than a specified threshold distance).

        :param message:  an optional Message passed along by the message bus
        '''
        raise Exception('what is this doing here?')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher.
        '''
        self._log.info('🍄 disabling velocity publisher...')
        if self.enabled:
            self._pot.disable()
            Publisher.disable(self)
            self._log.info('🍄 velocity publisher disabled.')
        else:
            self._log.warning('🍄 velocity publisher already disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        '''
        Close this publisher.
        '''
        self._log.info('👾 closing velocity publisher...')
        if not self.closed:
#           self._pot.close()
            Publisher.close(self)
            self._log.info('👾 velocity publisher closed.')
        else:
            self._log.warning('👾 velocity publisher already closed.')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MockPotentiometer(object):
    def __init__(self, level=Level.INFO):
        super().__init__()
        self._log = Logger('mock-pot', level)
        self._log.info('ready.')

    def set_output_limits(self, out_min, out_max):
        pass

    def get_scaled_value(self, update_led=True):
        return 0.0

    def set_black(self):
        pass

    def disable(self):
        pass

    def close(self):
        pass

#EOF
