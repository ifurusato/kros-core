#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-05-31
#
# This class interprets the signals arriving from the 8BitDo N30 Pro Gamepad,
# a paired Bluetooth device. This differs from GamepadDemo in that it simply
# displays the Gamepad output signals. No motors, video, etc.
#
# GamepadConnectException at bottom.
#

import time, itertools, traceback
import asyncio
from pathlib import Path
from colorama import init, Fore, Style
init()

from core.event import Event
from core.message_factory import MessageFactory
from core.message_bus import MessageBus
from core.logger import Logger, Level
from core.publisher import Publisher

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class GamepadPublisher(Publisher):

    _PUBLISH_LOOP_NAME = '__gamepad_publish_loop'

    '''
    A Publisher that connects with a bluetooth-based gamepad.
    '''
    def __init__(self, config, message_bus, message_factory, exit_on_complete=True, level=Level.INFO):
        Publisher.__init__(self, 'gamepad', config, message_bus, message_factory, level)
        self._level = level
        self._counter  = itertools.count()
        self._gamepad_enable    = False # TODO
        self._publish_delay_sec = 0.05  # delay after IFS event
        self._loop_delay_sec    = 0.5   # delay on noop loop
        self._limit             = 3

        # attempt to find the gamepad
        self._gamepad = None
#       self._gamepad = Gamepad(config, self._message_bus, self._message_factory, Level.INFO)
        self._log.info('connecting gamepad...')
        self._gamepad_enabled = True
        self._connect_gamepad()

        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _connect_gamepad(self):
        if not self._gamepad_enabled:
            self._log.info('gamepad disabled.')
            return
        if self._gamepad is None:
            self._log.info('creating gamepad...')
            try:
                from mock.gamepad import Gamepad
                self._gamepad = Gamepad(self._config, self._message_bus, self._message_factory, self._level)
            except GamepadConnectException as e:
                self._log.error('unable to connect to gamepad: {}'.format(e))
                self._gamepad = None
                self._gamepad_enabled = False
                self._log.info('gamepad unavailable.')
                return
#           except Exception as e:
            except ModuleNotFoundError as e:
                self._log.error('{} thrown establishing gamepad: {}\n{}'.format(type(e), e, traceback.format_exc()))
        # attempt connection .....................
        if self._gamepad is not None:
            self._log.info(Fore.YELLOW + 'enabling gamepad...')
            try:
                self._gamepad.enable()
                _count = 0
                while not self._gamepad.has_connection():
                    _count += 1
                    if _count == 1:
                        self._log.info(Fore.YELLOW + 'connecting to gamepad...')
                    else:
                        self._log.info(Fore.YELLOW + 'gamepad not connected; re-trying... [{:d}]'.format(_count))
                    self._gamepad.connect()
                    time.sleep(0.5)
                    if self._gamepad.has_connection() or _count > 5:
                        break
            except Exception as e:
                self._log.error('🐶 {} thrown connecting to gamepad: {}\n{}'.format(type(e), e, traceback.format_exc()))

        if self._gamepad is None:
            self._gamepad = MockGamepad(self._message_bus, self._message_factory)
            self._log.info(Fore.YELLOW + 'using mocked gamepad.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def has_connected_gamepad(self):
        return self._gamepad is not None and self._gamepad.has_connection()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if self._message_bus.get_task_by_name(GamepadPublisher._PUBLISH_LOOP_NAME):
                self._log.warning('already enabled.')
                return
            if self._gamepad:
                self._gamepad.enable()
                self._message_bus.loop.create_task(self._gamepad._gamepad_loop(self._gamepad_publish_loop, lambda: self.enabled), name=GamepadPublisher._PUBLISH_LOOP_NAME)
#               self._message_bus.loop.create_task(self._gamepad._gamepad_loop(self._gamepad_listener_loop, lambda: self.enabled), name='__gamepad_loop')
#               self._message_bus.loop.create_task(self._gamepad._gamepad_loop(self._publish_message, lambda: self.enabled), name='__gamepad_loop')
            self._log.info('enabled')
        else:
            self._log.info(Fore.BLACK + '<<< enabled: {}'.format(self.enabled))

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   async def _publish_message(self, message):
#       '''
#       Unless there is a class-level usage this can be replaced by a direct
#       call to the superclass' method.
#       '''
#       self._log.info('🎲 gamepad callback for message:\t' + Fore.YELLOW + '{}'.format(message.event.label))
#       await Publisher.publish(self, message)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _gamepad_publish_loop(self, message):
        self._log.info('🎲 gamepad callback for message:\t' + Fore.YELLOW + '{}'.format(message.event.label))
        await Publisher.publish(self, message)
        await asyncio.sleep(self._publish_delay_sec)

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   async def _gamepad_listener_loop(self, f_is_enabled):
#       self._log.info('starting key listener loop: ' + Fore.YELLOW + 'type \'?\' for help, \'q\' or Ctrl-C to exit.')
#       try:
#           while f_is_enabled():
#               _count = next(self._counter)
#               self._log.info('[{:03d}] BEGIN loop...'.format(_count))
#               _event = None # TODO
#               if _event is not None:
#                   self._log.info('"{}" ({}) pressed; publishing message for event: {}'.format(_event))
#                   _message = self._message_factory.create_message(_event, True)
#                   _message.value = 0
#                   self._log.info('key-publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.label))
#                   await Publisher.publish(self, _message)
#                   self._log.info('key-published message:' + Fore.WHITE + ' {}.'.format(_message.name))
#                   await asyncio.sleep(self._publish_delay_sec)
#               else:
#                   self._log.warning('no event generated.')
#                   await asyncio.sleep(self._loop_delay_sec)
#               self._log.debug('[{:03d}] END loop.'.format(_count))
#
#           self._log.info('publish loop complete.')
#       finally:
#           self._log.info('publish loop finally.')
#           pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher as well as shut down the message bus.
        '''
        if self._gamepad:
            self._gamepad.disable()
        self._message_bus.disable()
        Publisher.disable(self)
        self._log.info(Fore.YELLOW + 'disabled publisher.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def read_cpu_temperature(self):
        temp_file = Path('/sys/class/thermal/thermal_zone0/temp')
        if temp_file.is_file():
            with open(temp_file, 'r') as f:
                data = int(f.read())
                temperature = data / 1000
                return temperature
        else:
            return None

    # message handling ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _print_event(self, color, event, value):
        self._log.info('event:\t' + color + Style.BRIGHT + '{}; value: {}'.format(event.label, value))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_keymap(self):
#        1         2         3         4         5         6         7         8         9         C         1         2
#23456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890
        self._log.info('''button map:

     ┏━━━━━━━━┳━━━━━━┓                                             ┏━━━━━━┳━━━━━━━━┓
     ┃    L1  ┃  L2  ┃                                             ┃  R2  ┃  R1    ┃
     ┃   ┏━━━━┻━━━━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┻━━━━━━┻━━━━┓   ┃
     ┃   ┃                                                     ┏━━━━━┓         ┃   ┃
     ┃   ┃        ┏━━━━━┓                                      ┃  X  ┃         ┃   ┃
     ┗━━━┫        ┃  U  ┃                                      ┗━━━━━┛         ┣━━━┛
         ┃   ┏━━━━┛     ┗━━━━┓     ┏━━━━━┓    ┏━━━━━┓     ┏━━━━━┓   ┏━━━━━┓    ┃
         ┃   ┃ L           R ┃     ┃ SEL ┃    ┃ STR ┃     ┃  Y  ┃   ┃  A  ┃    ┃
         ┃   ┗━━━━┓     ┏━━━━┛     ┗━━━━━┛    ┗━━━━━┛     ┗━━━━━┛   ┗━━━━━┛    ┃
         ┃        ┃  D  ┃                                      ┏━━━━━┓         ┃
         ┃        ┗━━━━━┛                                      ┃  B  ┃         ┃
         ┃                   ┏━━━━━━━━┓          ┏━━━━━━━━┓    ┗━━━━━┛         ┃
         ┃                   ┃        ┃          ┃        ┃                    ┃
         ┃                   ┃   JL   ┃          ┃   JR   ┃                    ┃
         ┃                   ┃        ┃          ┃        ┃                    ┃
         ┃                   ┗━━━━━━━━┛          ┗━━━━━━━━┛                    ┃
         ┃                                                                     ┃
         ┗━━━━━━━━━┻━━━━━━━━━┻━━┳━━━━━━┻━┳━━━━━┳━┻━━━━━━┳━━┻━━━━━━━━━┻━━━━━━━━━┛
                                ┃   B1   ┃  P  ┃   B2   ┃
                                ┗━━━━━━━━┻━━━━━┻━━━━━━━━┛

   L1:        description                                                                   R1:        description
   L2:        description                                                                   R2:        description
   U:         description                     SEL:       description                        X:         description
   L:         description                     STR:       description                        Y:         description
   R:         description                                                                   A:         description
   D:         description                                                                   B:         description

               JL:        description                            JR:        description
                                              B1:        description
                                              P:         description
                                              B2:        description
        ''')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_event_for_char(self, och):
        '''
        Below are the mapped characters for IFS-based events, including several others:

           oct   dec   hex   char   usage

            54   44    2C    , *    increase motors speed (both)
            56   46    2E    . *    decrease motors speed (both)

           141   97    61    a *    port side IR
           142   98    62    b *    brake
           143   99    63    c
           144   100   64    d *    cntr IR
           145   101   65    e *    sniff
           146   102   66    f *    stbd IR
           147   103   67    g *    stbd side IR
           150   104   68    h
           151   105   69    i      info
           152   106   6A    j *    port BMP
           153   107   6B    k *    cntr BMP
           154   108   6C    l *    stbd BMP
           155   109   6D    m *    stop
           156   110   6E    n *    halt
           157   111   6F    o      clear task list
           160   112   70    p      pop message
           161   113   71    q
           162   114   72    r      roam
           163   115   73    s *    port IR
           164   116   74    t      noop (test message)
           165   117   75    u
           166   118   76    v      verbose
           167   119   77    w      toggle flood mode with random messages
           170   120   78    x
           171   121   79    y
           172   122   7A    z
           177   127   7f   del     shut down

        * represents robot sensor or control input.
        '''

        if och   == 44:  # ,
            return Event.DECREASE_VELOCITY
        elif och == 46:  # .
            return Event.INCREASE_VELOCITY
        elif och == 97:  # a
            return Event.INFRARED_PSID
        elif och == 98:  # b
            return Event.BRAKE
        elif och == 100: # d
            return Event.INFRARED_CNTR
        elif och == 101: # e
            return Event.SNIFF
        elif och == 102: # f
            return Event.INFRARED_STBD
        elif och == 103: # g
            return Event.INFRARED_SSID
        elif och == 106: # j
            return Event.BUMPER_PORT
        elif och == 107: # k
            return Event.BUMPER_CNTR
        elif och == 108: # l
            return Event.BUMPER_STBD
        elif och == 109: # m
            return Event.STOP
        elif och == 110: # h
            return Event.HALT
        elif och == 114: # r
            return Event.ROAM
        elif och == 115: # s
            return Event.INFRARED_PORT
        elif och == 116: # s
            return Event.NOOP
        elif och == 127: # del
            return Event.SHUTDOWN
        else:
            return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class GamepadConnectException(Exception):
    '''
    Exception raised when unable to connect to Gamepad.
    '''
    pass

#EOF
