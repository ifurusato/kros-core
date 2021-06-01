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

import sys, time, itertools, psutil, random, traceback
#from threading import Thread
import asyncio
import concurrent.futures
from pathlib import Path
from colorama import init, Fore, Style
init()

from core.event import Event
from core.message_factory import MessageFactory
from core.message_bus import MessageBus
from core.logger import Logger, Level
from core.rate import Rate
from core.publisher import Publisher

# ...............................................................
class MockGamepad(object):
    def __init__(self, message_bus, message_factory, level=Level.INFO):
        self._level = level
        self._log = Logger("mock-gp", level)
        self._enabled = False
        self._closed  = False
        self._thread  = None
        _loop_freq_hz = 1
        self._rate = Rate(_loop_freq_hz)
        self._log.info('ready.')

    # ..........................................................................
    def enable(self):
        if self._thread:
            self._log.info('already enabled.')
        else:
            self._enabled = True
            self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        self._enabled = False

    # ..........................................................................
    async def _read_loop(self):
        await sleep(2.0 * random.random())
        self._log.info('🤙 read_loop called.')
        _loop  = []
        _loop.append(Event.MOTION_DETECT)
        _loop.append(Event.COLLISION_DETECT)
        _loop.append(Event.HIGH_TEMPERATURE)
        return _loop

    # ..........................................................................
    def gamepad_callback(self, obj):
        self._log.info(Fore.YELLOW + 'gamepad callback for obj: {}'.format(type(obj)))

    # ..........................................................................
    def start_gamepad_loop(self, callback):
        '''
        This is the method to call to actually start the loop.

        The arguments to the callback method include the event.
        '''
        self._log.info(Fore.YELLOW + 'start gamepad loop...')
        if not self._enabled:
            self._log.error('attempt to start gamepad event loop while disabled.')
#       elif self._gamepad is None:
#           self._log.error(Gamepad._NOT_AVAILABLE_ERROR + ' [no gamepad found]')
#           sys.exit(3)
        elif not self._closed:
            if self._thread is None:
                self._enabled = True
#               self._thread = Thread(name='mock-gp', target=MockGamepad._gamepad_loop, args=[self, callback, lambda: self._enabled], daemon=True)
#               self._thread.setDaemon(False)
#               self._thread.start()
                self._log.info('enabled.')
            else:
                self._log.warning('cannot enable: process already running.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    async def _gamepad_loop(self, callback, f_is_enabled):
        self._log.info('🤚 starting event loop with enabled argument: {}...'.format(f_is_enabled()))
        __enabled = True
        try:
            while __enabled and f_is_enabled():
                self._log.info('🤚 START gamepad loop.')
                self._log.info(Fore.BLUE + 'gamepad enabled: {}; f_is_enabled: {}'.format(__enabled, f_is_enabled()))
#                   if self._gamepad is None:
#                       raise Exception(Gamepad._NOT_AVAILABLE_ERROR + ' [gamepad no longer available]')
                    # loop and filter by event code and print the mapped label
#               for event in self._read_loop():
                _event = await self._read_loop()
#                   if callback:
                callback(event)
#               self._handleEvent(event)
                if not f_is_enabled():
                    self._log.info(Fore.BLACK + '🚫 breaking from event loop.')
                    break
                self._rate.wait()
                self._log.info('🤚 END gamepad loop with enabled argument: {}...'.format(f_is_enabled()))

        except KeyboardInterrupt:
            self._log.info('🚫 caught Ctrl-C, exiting...')
            __enabled = False
        except Exception as e:
            self._log.error('🚫 gamepad device error: {}'.format(e))
            __enabled = False
        except OSError as e:
            self._log.error(Gamepad._NOT_AVAILABLE_ERROR + '🚫 [lost connection to gamepad]')
            __enabled = False
        finally:
            '''
            Note that closing the InputDevice is a bit tricky, and we're currently
            masking an exception that's always thrown. As there is no data loss on
            a gamepad event loop being closed suddenly this is not an issue.
            '''
            try:
                self._log.info('😨 closing gamepad device...')
                self._gamepad.close()
                self._log.info(Fore.YELLOW + '😨 gamepad device closed.')
            except Exception as e:
                self._log.info('😨 error closing gamepad device: {}'.format(e))
            finally:
                __enabled = False
                self._gamepad_closed = True

        self._log.info('exited event loop.')


# ...............................................................
class GamepadPublisher(Publisher):

    _PUBLISH_LOOP_NAME = '__publish-loop__'

    '''
    A Publisher that connects with a bluetooth-based gamepad.
    '''
    def __init__(self, config, message_bus, message_factory, exit_on_complete=True, level=Level.INFO):
        super().__init__('gp', message_bus, message_factory, level)
        if config is None:
            raise ValueError('no configuration provided.')
        if message_bus is None:
            raise ValueError('null message bus argument.')
        elif isinstance(message_bus, MessageBus):
            self._message_bus = message_bus
        else:
            raise ValueError('unrecognised message bus argument: {}'.format(type(message_bus)))
        if message_factory is None:
            raise ValueError('null message factory argument.')
        elif isinstance(message_factory, MessageFactory):
            self._message_factory = message_factory
        else:
            raise ValueError('unrecognised message factory argument: {}'.format(type(message_bus)))

        self._exit_on_complete = exit_on_complete
        self._counter  = itertools.count()
        self._triggered_ir_port_side = self._triggered_ir_port  = self._triggered_ir_cntr  = self._triggered_ir_stbd  = \
        self._triggered_ir_stbd_side = self._triggered_bmp_port = self._triggered_bmp_cntr = self._triggered_bmp_stbd = 0
        self._flood_enable      = False
        self._publish_delay_sec = 0.05 # delay after IFS event
        self._loop_delay_sec    = 0.5  # delay on noop loop
        self._limit             = 3

        # attempt to find the gamepad
        self._gamepad = None
#       self._gamepad = Gamepad(config, self._message_bus, self._message_factory, Level.INFO)
        self._log.info('connecting gamepad...')
        self._gamepad_enabled = True
        self._connect_gamepad()

        self._log.info('ready.')

    # ..........................................................................
    def _connect_gamepad(self):
        if not self._gamepad_enabled:
            self._log.info('gamepad disabled.')
            return
        if self._gamepad is None:
            self._log.info('creating gamepad...')
            try:
                from mock.gamepad import Gamepad
                self._gamepad = Gamepad(self._config, self._queue, Level.INFO)
            except GamepadConnectException as e:
                self._log.error('unable to connect to gamepad: {}'.format(e))
                self._gamepad = None
                self._gamepad_enabled = False
                self._log.info('gamepad unavailable.')
                return
#           except Exception as e:
            except ModuleNotFoundError as e:
                self._log.error('{} thrown establishing gamepad: {}\n{}'.format(type(e), e, traceback.print_stack()))

        if self._gamepad is not None:
            self._log.info(Fore.YELLOW + 'enabling gamepad...')
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
        else:
            self._gamepad = MockGamepad(self._message_bus, self._message_factory)
            self._log.info(Fore.YELLOW + 'using mocked gamepad.')

#   # ..........................................................................
#   def gamepad_callback(self, event):
#       self._log.info(Fore.YELLOW + 'gamepad callback for event: {}'.format(event))

    # ..........................................................................
    def has_connected_gamepad(self):
        return self._gamepad is not None and self._gamepad.has_connection()

    # ................................................................
    def enable(self):
        super().enable()
        if self.enabled:
            if self._message_bus.get_task_by_name(GamepadPublisher._PUBLISH_LOOP_NAME):
                self._log.warning('already enabled.')
                return
#           if self._gamepad:
            self._gamepad.enable()
#           self._gamepad.start_gamepad_loop(self.gamepad_callback)
            self._message_bus.loop.create_task(self._gamepad._gamepad_loop(self._gamepad.gamepad_callback, lambda: self.enabled), name='__gamepad_loop')
            self._log.info('enabled')
        else:
            self._log.info(Fore.BLACK + '<<< enabled: {}'.format(self.enabled))

    # ................................................................
    async def _key_listener_loop(self, f_is_enabled):
        self._log.info('starting key listener loop: ' + Fore.YELLOW + 'type \'?\' for help, \'q\' or Ctrl-C to exit.')
        try:

            while f_is_enabled():
                _count = next(self._counter)
                self._log.info('[{:03d}] BEGIN loop...'.format(_count))
                _event = None # TODO
                if _event is not None:
                    self._log.info('"{}" ({}) pressed; publishing message for event: {}'.format(_event))
                    _message = self._message_factory.get_message(_event, True)
                    _message.value = 0
                    self._log.info('key-publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
                    await super().publish(_message)
                    self._log.info('key-published message:' + Fore.WHITE + ' {}.'.format(_message.name))
                    await asyncio.sleep(self._publish_delay_sec)
                else:
                    self._log.warning('no event generated.')
                    await asyncio.sleep(self._loop_delay_sec)
                self._log.debug('[{:03d}] END loop.'.format(_count))

            self._log.info('publish loop complete.')
        finally:
            self._log.info('publish loop finally.')
            pass
      
    # ..........................................................................
    def disable(self):
        '''
        Disable this publisher as well as shut down the message bus.
        '''
        if self._gamepad:
            self._gamepad.disable()
        self._message_bus.disable()
        super().disable()
        self._log.info(Fore.YELLOW + 'disabled publisher.')

    # ................................................................
    def print_sys_info(self):
        _M = 1000000
        _vm = psutil.virtual_memory()
        self._log.info('virtual memory: \t' + Fore.YELLOW + 'total: {:4.1f}MB; available: {:4.1f}MB ({:5.2f}%); used: {:4.1f}MB; free: {:4.1f}MB'.format(\
                _vm[0]/_M, _vm[1]/_M, _vm[2], _vm[3]/_M, _vm[4]/_M))
        # svmem(total=n, available=n, percent=n, used=n, free=n, active=n, inactive=n, buffers=n, cached=n, shared=n)
        _sw = psutil.swap_memory()
        # sswap(total=n, used=n, free=n, percent=n, sin=n, sout=n)
        self._log.info('swap memory:    \t' + Fore.YELLOW + 'total: {:4.1f}MB; used: {:4.1f}MB; free: {:4.1f}MB ({:5.2f}%)'.format(\
                _sw[0]/_M, _sw[1]/_M, _sw[2]/_M, _sw[3]))
        temperature = self.read_cpu_temperature()
        if temperature:
            self._log.info('cpu temperature:\t' + Fore.YELLOW + '{:5.2f}°C'.format(temperature))

    # ................................................................
    def read_cpu_temperature(self):
        temp_file = Path('/sys/class/thermal/thermal_zone0/temp')
        if temp_file.is_file():
            with open(temp_file, 'r') as f:
                data = int(f.read())
                temperature = data / 1000
                return temperature
        else:
            return None

    # message handling .........................................................

    # ......................................................
    def _print_event(self, color, event, value):
        self._log.info('event:\t' + color + Style.BRIGHT + '{}; value: {}'.format(event.description, value))

    # ..........................................................................
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

    # ..........................................................................
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
            return Event.DECREASE_SPEED
        elif och == 46:  # .
            return Event.INCREASE_SPEED
        elif och == 97:  # a
            return Event.INFRARED_PORT_SIDE
        elif och == 98:  # b
            return Event.BRAKE
        elif och == 100: # d
            return Event.INFRARED_CNTR
        elif och == 101: # e
            return Event.SNIFF
        elif och == 102: # f
            return Event.INFRARED_STBD
        elif och == 103: # g
            return Event.INFRARED_STBD_SIDE
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

# ..............................................................................
class GamepadConnectException(Exception):
    '''
    Exception raised when unable to connect to Gamepad.
    '''
    pass

#EOF
