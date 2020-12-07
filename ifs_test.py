#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-30
# modified: 2020-05-24
#
# This tests the five infrared sensors and three bumper sensors of the
# KR01's Integrated Front Sensor (IFS). Its signals are returned via a
# Pimoroni IO Expander Breakout Garden board, an I²C-based microcontroller.
#

import pytest
import time, itertools, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.event import Event
from lib.message import Message
from lib.message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.clock import Clock, Tick, Tock
from lib.queue import MessageQueue
from lib.ifs import IntegratedFrontSensor
#from lib.indicator import Indicator

# ..............................................................................
class MockMessageQueue():
    '''
    This message queue just displays IFS events as they arrive.
    '''
    def __init__(self, level):
        super().__init__()
        self._count = 0
        self._counter = itertools.count()
        self._log = Logger("queue", Level.INFO)
        self._listeners = []
        self._port_side = False
        self._port      = False
        self._cntr      = False
        self._stbd      = False
        self._stbd_side = False
        self._bmp_port  = False
        self._bmp_cntr  = False
        self._bmp_stbd  = False
        self._log.info('ready.')

    # ......................................................
    def add(self, message):
        self._count = next(self._counter)
        message.number = self._count
        _event = message.event
        self._log.debug('added message #{}; priority {}: {}; event: {}'.format(message.number, message.priority, message.description, _event))
        _value = message.value

        if _event is Event.INFRARED_PORT_SIDE and not self._port_side:
            self._log.debug(Fore.RED  + '> INFRARED_PORT_SIDE: {}; value: {}'.format(_event.description, _value))
            self._port_side = True
        elif _event is Event.INFRARED_PORT and not self._port:
            self._log.debug(Fore.RED  + '> INFRARED_PORT: {}; value: {}'.format(_event.description, _value))
            self._port      = True
        elif _event is Event.INFRARED_CNTR and not self._cntr:
            self._log.debug(Fore.BLUE + '> INFRARED_CNTR:     distance: {:>5.2f}cm'.format(_value))
            self._cntr      = True
        elif _event is Event.INFRARED_STBD and not self._stbd:
            self._log.debug(Fore.GREEN + '> INFRARED_STBD: {}; value: {}'.format(_event.description, _value))
            self._stbd      = True
        elif _event is Event.INFRARED_STBD_SIDE and not self._stbd_side:
            self._log.debug(Fore.GREEN + '> INFRARED_STBD_SIDE: {}; value: {}'.format(_event.description, _value))
            self._stbd_side = True
        elif _event is Event.BUMPER_PORT:
            self._log.debug(Fore.RED + Style.BRIGHT + 'BUMPER_PORT: {}'.format(_event.description))
            self._bmp_port  = True
        elif _event is Event.BUMPER_CNTR:
            self._log.debug(Fore.BLUE + Style.BRIGHT + 'BUMPER_CNTR: {}'.format(_event.description))
            self._bmp_cntr  = True
        elif _event is Event.BUMPER_STBD:
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'BUMPER_STBD: {}'.format(_event.description))
            self._bmp_stbd  = True
        else:
            self._log.debug(Fore.BLACK + Style.BRIGHT + 'other event: {}'.format(_event.description))


    # ..........................................................................
    def add_listener(self, listener):
        '''
        Add a listener to the optional list of message listeners.
        '''
        return self._listeners.append(listener)

    # ..........................................................................
    def remove_listener(self, listener):
        '''
        Remove the listener from the list of message listeners.
        '''
        try:
            self._listeners.remove(listener)
        except ValueError:
            self._log.warn('message listener was not in list.')

    # ......................................................
    @property
    def all_triggered(self):
        return self._port_side and self._port and self._cntr and self._stbd and self._stbd_side \
               and self._bmp_port and self._bmp_cntr and self._bmp_stbd 

    # ......................................................
    @property
    def count(self):
        return self._count

    # ......................................................
    def handle(self, message):
#       self._log.info(Fore.BLUE + 'handle message {}'.format(message))
        self.add(message)

    # ..........................................................................
    def waiting_for_message(self):
        _fmt = '{0:>9}'
        self._log.info('waiting for: | ' \
                + Fore.RED   + _fmt.format( 'PORT_SIDE' if not self._port_side else '' ) \
                + Fore.CYAN  + ' | ' \
                + Fore.RED   + _fmt.format( 'PORT' if not self._port else '' ) \
                + Fore.CYAN  + ' | ' \
                + Fore.BLUE  + _fmt.format( 'CNTR' if not self._cntr else '' ) \
                + Fore.CYAN  + ' | ' \
                + Fore.GREEN + _fmt.format( 'STBD' if not self._stbd else '' ) \
                + Fore.CYAN  + ' | ' \
                + Fore.GREEN + _fmt.format( 'STBD_SIDE' if not self._stbd_side else '' ) 
                + Fore.CYAN  + ' || ' \
                + Fore.RED   + _fmt.format( 'BMP_PORT' if not self._bmp_port else '' ) \
                + Fore.CYAN  + ' | ' \
                + Fore.BLUE  + _fmt.format( 'BMP_CNTR' if not self._bmp_cntr else '' ) \
                + Fore.CYAN  + ' | ' \
                + Fore.GREEN + _fmt.format( 'BMP_STBD' if not self._bmp_stbd else '' ) \
                + Fore.CYAN  + ' |' )

# ..............................................................................
@pytest.mark.unit
def test_ifs():

    _log = Logger("test-ifs", Level.INFO)

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _message_factory = MessageFactory(Level.INFO)
    _queue = MockMessageQueue(Level.INFO)
    _message_bus = MessageBus(Level.INFO)
    _message_bus.add_handler(Message, _queue.handle)
    _clock = Clock(_config, _message_bus, _message_factory, Level.INFO)
    _ifs = IntegratedFrontSensor(_config, _clock, _message_bus, _message_factory, Level.INFO)

#   _indicator = Indicator(Level.INFO)
    # add indicator as message listener
#   _queue.add_listener(_indicator)

    _ifs.enable()
    _clock.enable()
    while not _queue.all_triggered:
        _queue.waiting_for_message()
        time.sleep(0.1)
    _ifs.disable()

    assert _queue.count > 0
    _log.info('test complete.' + Style.RESET_ALL)

# ..............................................................................
def main():

    try:
        test_ifs()
    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error testing ifs: {}\n{}'.format(e, traceback.format_exc()) + Style.RESET_ALL)

if __name__== "__main__":
    main()

#EOF