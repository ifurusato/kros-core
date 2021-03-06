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
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.message_factory import MessageFactory
from core.logger import Logger, Level
from core.component import Component
from core.event import Event
from core.message import Message
from core.publisher import Publisher
from hardware.clock_subscriber import ClockSubscriber

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ExternalClock(Publisher):

    CLASS_NAME = 'ext-clock'
    _LISTENER_LOOP_NAME = '__clock_listener_loop'

    '''
    A publisher for events from an external clock source.

    Messages from the clock are published to the asynchronous message bus,
    so timing is not assured. This clock should be used to trigger events
    that aren't stricly time-critical but need to be scheduled.

    This uses an internally-set callback; externally-set, direct callbacks
    are not currently supported.

    :param config:            the application configuration
    :param message_bus:       the asynchronous message bus
    :param message_factory:   the factory for creating messages
    :param level:             the log level
    '''
    def __init__(self, config, message_bus, message_factory, level=Level.INFO):
        if not isinstance(level, Level):
            raise ValueError('wrong type for log level argument: {}'.format(type(level)))
        self._level = level
        Publisher.__init__(self, ExternalClock.CLASS_NAME, config, message_bus, message_factory, level=self._level)
#       self._message_bus = message_bus
        # configuration ................
        self._counter        = itertools.count()
        self._sub_counter    = itertools.count()
        _cfg = config['kros'].get('publisher').get('external_clock')
        _loop_freq_hz        = _cfg.get('loop_freq_hz')
        self._publish_delay_sec = 1.0 / _loop_freq_hz
        self._log.info('external clock publish loop frequency: {:d}Hz (delay: {:4.1f}ms)'.format(_loop_freq_hz, ( self._publish_delay_sec * 1000.0)))
        self._pin = _cfg.get('pin')
        self._log.info('external clock pin:\t{:d}'.format(self._pin))
        self._pi             = None
        self._pi_callback    = None
        self._initd          = False
#       self._callbacks      = [] # direct callbacks
        self._subscribers    = [] # callback via message bus
        self._message        = None # single message placeholder
        self._last_msg_timestamp = dt.now()
        self._millis         = lambda: int(round(time.time() * 1000))
        self._TICK_MESSAGE   = TickMessage(self._millis()) # singleton
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if self._message_bus.get_task_by_name(ExternalClock._LISTENER_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                if not self._initd:
                    self._initialise()
#               for _subscriber in self._subscribers:
#                   _subscriber.enable()
        else:
            self._log.warning('failed to enable publisher.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _initialise(self):
        try:

            self._log.info('importing pigpio...')
            import pigpio
            self._pi = pigpio.pi()
            if not self._pi.connected:
                raise Exception('unable to establish connection to Pi.')
            self._log.info('establishing callback on pin {:d}.'.format(self._pin))
            self._pi.set_mode(gpio=self._pin, mode=pigpio.INPUT) # GPIO 12 as input
            self._pi_callback = self._pi.callback(self._pin, pigpio.EITHER_EDGE, self._irq_callback_method)
            self._log.info('enabled external clock callback.')
            self._log.info('creating task for clock listener loop; enabled: {}'.format(self.enabled))
            self._message_bus.loop.create_task(self._clock_listener_loop(lambda: self.enabled), name=ExternalClock._LISTENER_LOOP_NAME)
            self._log.info('task enabled.')
            self._initd = True
        except Exception as e:
            self._log.error('unable to enable external clock: {}'.format(e))
        finally:
            pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_callback(self, callback, direct=False):
        '''     
        Adds a callback to those triggered by clock ticks. Direct callbacks 
        are not asynchronous and will likely mess up the timing of the bus
        if their processing time is not extremely short.

        :param direct:  if True the callback executes directly from the IRQ;
                        a False will use the message bus. Default is False.
        ''' 
        if direct:
            raise NotImplementedError('direct callbacks not supported.')
#           _count = next(self._counter)
#           self._log.info('adding direct callback {:d}...'.format(_count))
#           self._callbacks.append(callback)
        else:
            _count = next(self._sub_counter)
            self._log.info('adding subscriber callback {:d}...'.format(_count))
            _sub = ClockSubscriber(self._config, 'clk-sub:{:d}'.format(_count), self._message_bus, callback, self._level)
            self._subscribers.append(_sub)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def remove_callback(self, callback, direct=False):
        '''     
        Removes the callback from those triggered by clock ticks.
        You must use the same mode as the callback was registered.
        ''' 
#       self._callbacks.remove(callback)
        raise NotImplementedError('use IrqClock instead.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _irq_callback_method(self, gpio, level, tick):
        '''
        This method is called upon the external clock's interrupt.
        '''
        if self.enabled:
#           for _callback in self._callbacks:
#               _callback()
            self._TICK_MESSAGE.value = self._millis() # update timestamp
            self._message = self._TICK_MESSAGE        # reassign to message

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _clock_listener_loop(self, f_is_enabled):
#       self._log.info('starting clock listener loop.')
        while f_is_enabled():
#           self._log.info('clock listener loop 1.')
            if self._message is not None:
                _elapsed_ms = (dt.now() - self._last_msg_timestamp).total_seconds() * 1000.0
#               self._log.info(Fore.BLUE + 'irq callback on tick message: ' + Fore.YELLOW + ' {:6.3f}ms'.format(_elapsed_ms))
#               self._log.info(Style.BRIGHT + 'clock-publishing message:' + Fore.WHITE + Style.NORMAL + ' {}'.format(self._message.name)
#                       + Fore.CYAN + ' event: {}; '.format(self._message.event.label) + Fore.YELLOW + 'value: {:5.2f}'.format(self._message.value))
                await Publisher.publish(self, self._message)
#               self._log.info(Style.DIM + 'clock-published message:' + Fore.WHITE + Style.NORMAL + ' {}'.format(self._message.name)
#                       + Fore.CYAN + ' event: {}; '.format(self._message.event.label) + Fore.YELLOW + 'value: {:5.2f}'.format(self._message.value))
                self._last_msg_timestamp = dt.now()
                self._message = None

            await asyncio.sleep(self._publish_delay_sec)
        self._log.info('clock publish loop complete.')

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   def disable(self):
#       '''
#       Disable this publisher.
#       '''
#       Publisher.disable(self)
#       self._log.info('disabled publisher.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        try:
            self._log.info('IRQ clock closing...')
            if self._pi_callback:
                self._pi_callback.cancel()
            self._log.info('IRQ clock closed.')
        except Exception as e:
            self._log.error('error closing pigpio: {}'.format(e))
        finally:
            if self._pi:
                self._pi.stop()
            self._log.info('pigpio connection closed.')
        Component.close(self)
        self._log.info('closed.')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TickMessage(Message):
    '''
    A singleton Message.
    '''
    def __init__(self, value):
        Message.__init__(self, Event.TICK, value)

    @property
    def expired(self):
        return False

    def gc(self):
        pass

    @property
    def gcd(self):
        return False

    def acknowledge(self, subscriber):
        pass

    @property
    def fully_acknowledged(self):
        return False

    def acknowledged_by(self, subscriber):
        return False

    @property
    def sent(self):
        return -1

#EOF
