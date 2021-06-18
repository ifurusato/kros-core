#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-06-04
#
# EventPublisher extends the Publisher class providing robot events from three
# sources:
#
# First, a mock Integrated Front Sensor (IFS) that responds to key presses,
# acting as a robot front sensor array for when you don't actually have a
# robot. Rather than provide simply a second key-input mechanism, this can
# also be used for keyboard control of the mocked robot, i.e., it includes
# events unrelated to the original IFS.
#
# Second, if a Bluetooth-based Gamepad is paired and connected, this will
# forward events generated by the Gamepad class to the MessageBus.
#
# Finally, there is also has a "flood" mode that auto-generates random
# event-bearing messages at a random interval.
#

import sys, time, itertools, psutil, random, traceback
import select, tty, termios # used by _Getch
import select
import asyncio
import concurrent.futures
from pathlib import Path
from colorama import init, Fore, Style
init()

from core.event import Event
from core.message_factory import MessageFactory
from core.logger import Logger, Level
from core.publisher import Publisher
from mock.mock_gamepad import MockGamepad

# ...............................................................
class EventPublisher(Publisher):

    _PUBLISH_LOOP_NAME = '__publish-loop__'

    '''
    A mock IFS, Gamepad and 'Flood' event source.
    '''
    def __init__(self, config, message_bus, message_factory, exit_on_complete=True, level=Level.INFO):
        super().__init__('event', message_bus, message_factory, level)
        if config is None:
            raise ValueError('no configuration provided.')
        self._config = config
        self._level   = level
#       self._exit_on_complete = exit_on_complete
        self._counter  = itertools.count()
        self._triggered_ir_port_side = self._triggered_ir_port  = self._triggered_ir_cntr  = self._triggered_ir_stbd  = \
        self._triggered_ir_stbd_side = self._triggered_bmp_port = self._triggered_bmp_cntr = self._triggered_bmp_stbd = 0
        self._getch           = _Getch()
        self._flood_enable    = False
        # TODO configuration
        self._gamepad_publish_delay_sec = 0.01 # delay after Gamepad event
        self._publish_delay_sec = 0.01         # delay after IFS event
        self._loop_delay_sec  = 0.01           # delay on noop loop
        self._limit           = 3

        self._motors          = None
        # attempt to find the gamepad ......................
        self._gamepad = None
        self._log.info('connecting gamepad...')
        self._gamepad_enabled = False
        self._log.info('ready.')

    # ..........................................................................
    def set_motors(self, motors):
        self._motors = motors

    # ..........................................................................
    def _connect_gamepad(self):
        self._log.info('🐢 _connect_gamepad BEGIN.')
        if not self._gamepad_enabled:
            self._log.info('gamepad disabled.')
            return
        if self._gamepad is None:
            self._log.info('creating gamepad...')
            try:
                from mock.gamepad import Gamepad
                self._gamepad = Gamepad(self._config, self._message_bus, self._message_factory, self._level)
            except ModuleNotFoundError as e:
                self._log.error('gamepad missing supporting library: {}'.format(e))
                self._gamepad = None
#               self._gamepad_enabled = False
            except GamepadConnectException as e:
                self._log.error('unable to connect to gamepad.')
#               self._log.error('unable to connect to gamepad: {}'.format(e))
                self._gamepad = None
                self._gamepad_enabled = False
                self._log.info('gamepad unavailable.')
                return
#           except Exception as e:
            except ModuleNotFoundError as e:
                self._log.error('{} thrown establishing gamepad: {}\n{}'.format(type(e), e, traceback.print_stack()))
        # attempt connection ..................................
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
                self._log.error('🐶 {} thrown connecting to gamepad: {}\n{}'.format(type(e), e, traceback.print_stack()))

        if self._gamepad is None:
            self._gamepad = MockGamepad(self._message_bus, self._message_factory)
            self._log.info(Fore.YELLOW + 'using mocked gamepad.')
        self._log.info('🐢 _connect_gamepad END.')

    # ..........................................................................
    def has_connected_gamepad(self):
        return self._gamepad is not None and self._gamepad.has_connection()

    # ................................................................
    def enable(self):
        super().enable()
        if self.enabled:
            if self._message_bus.get_task_by_name(EventPublisher._PUBLISH_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                self._log.info('creating task for key listener loop...')
                self._message_bus.loop.create_task(self._key_listener_loop(lambda: self.enabled), name='__key_listener_loop')
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable publisher.')

    # ................................................................
    async def _key_listener_loop(self, f_is_enabled):
        self._log.info('starting key listener loop: ' + Fore.YELLOW + 'type \'?\' for help, \'q\' or Ctrl-C to exit.')
        try:
            while f_is_enabled():
                _count = next(self._counter)
                self._log.debug('[{:03d}] BEGIN loop...'.format(_count))
                _event = None
                if self._getch.available():
                    ch = self._getch.readchar()
                    if ch != None and ch != '':
                        och = ord(ch)
                        self._log.debug('key "{}" ({}) pressed, processing...'.format(ch, och))
                        if och == 10 or och == 13: # LF or CR to print 48 newlines
                            print(Logger._repeat('\n',48))
                            continue
                        elif och == 104: # 'h' help
                            self.print_help()
                            continue
                        elif och == 105: # 'i' print info
                            self._log.heading('System Information','Memory, CPU and Message Bus Information.')
                            self.print_sys_info()
                            self._message_bus.print_bus_info()
                            continue
                        elif och == 111: # 'o'
                            self._message_bus.clear_tasks()
                            continue
                        elif och == 112: # 'p'
#                           raise NotImplementedError
                            await self._message_bus.pop_queue()
                            continue
                        elif och == 3 or och == 113: # 'q'
                            self.disable()
                            self._log.info(Fore.YELLOW + 'exit on \'q\' or Ctrl-C...')
                            continue
                        elif och == 47 or och == 63: # '/' or '?' for help
                            self.print_help()
                            continue
                        elif och == 118: # 'v' toggle verbose
                            self._toggle_verbosity()
                            continue
                        elif och == 101: # 'e' toggle gamepad
                            self._toggle_gamepad()
                            continue
                        elif och == 119: # 'w' toggle flood mode
                            self._toggle_flood()
                            continue
                        elif och == 122: # 'z' toggle motors loop
                            self._toggle_motors()
                            continue
                        # otherwise handle as event
                        _event = self.get_event_for_char(och)
                        if _event is not None:
                            self._log.info('"{}" ({}) pressed; publishing message for event: {}'.format(ch, och, _event))
                            _message = self._message_factory.get_message(_event, True)
                            _message.value = 0
                            self._log.info('key-publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
                            await super().publish(_message)
                            self._log.info('key-published message:' + Fore.WHITE + ' {}.'.format(_message.name))
                            self._accumulate_message(_message)
                            if Event.is_ifs_event(_event):
                                self._waiting_for_message()
                                if self.all_triggered:
                                    self.disable()
                                    self._log.info(Fore.YELLOW + 'exit having triggered all sensors.')
                        else:
                            self._log.warning('unmapped key "{}" ({}) pressed.'.format(ch, och))
                        await asyncio.sleep(self._publish_delay_sec)
                    else:
                        self._log.warning('readchar returned null.')
                elif self._flood_enable:
                    _event = self._get_random_event()
                    _message = self._message_factory.get_message(_event, True)
                    self._log.info('flood-publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
                    await super().publish(_message)
                    self._log.info('flood-published message:' + Fore.WHITE + ' {}.'.format(_message.name))
                    await asyncio.sleep(random.triangular(0.2, 5.0, 2.0))
                else:
                    # nothing happening...
                    self._log.debug('[{:03d}] waiting for key press...'.format(_count))
                    await asyncio.sleep(self._loop_delay_sec)

                self._log.debug('[{:03d}] END loop.'.format(_count))
            self._log.info('publish loop complete.')
        finally:
            if self._getch:
                self._getch.close()

    # ................................................................
    async def _gamepad_callback(self, message):
        self._log.info('gamepad callback for message:\t' + Fore.YELLOW + '{}'.format(message.event.description))
        await super().publish(message)

    # ..........................................................................
    def _toggle_verbosity(self):
        self._message_bus.verbose = not self._message_bus.verbose
        if self._message_bus.verbose:
            self._log.info('setting verbosity to: ' + Fore.YELLOW + '{}'.format(self._message_bus.verbose))
        else:
            print(Fore.CYAN + Logger._repeat(' ',60) + ': setting verbosity to: ' + Fore.YELLOW + '{}'.format(self._message_bus.verbose))

    # ..........................................................................
    def _toggle_gamepad(self):
        if self._gamepad_enabled:
            self._gamepad_enabled = False
            if self._gamepad:
                self._log.info('gamepad disabled: ' + Fore.YELLOW + 'type \'e\' to enable.')
            else:
                self._log.warning('unable to disable gamepad: no gamepad found.')
        else:
            GAMEPAD_TASK_NAME = '__gamepad_callback'
            self._gamepad_enabled = True
            self._log.info('gamepad enabled: ' + Fore.YELLOW + 'type \'e\' to disable.')
            if not self._gamepad:
                self._connect_gamepad()
                self._log.info(Fore.GREEN + '🈯 creating task for gamepad...')
                self._message_bus.loop.create_task(self._gamepad._gamepad_loop(self._gamepad_callback, lambda: self._gamepad_enabled), name=GAMEPAD_TASK_NAME)
            else:
                _tasks = self._message_bus.get_all_tasks(True)
                self._log.info('{} existing tasks.'.format(len(_tasks)))
                for _task in _tasks:
                    if _task.get_name() == GAMEPAD_TASK_NAME:
                        self._log.warning('existing gamepad task:\t' + Fore.YELLOW + '{}...'.format(_task.get_name()))
                        # TODO instead remove any existing task
                        raise Exception('gamepad task already exists.')
                    else:
                        self._log.info('existing task:\t' + Fore.BLUE + '{}...'.format(_task.get_name()))
                self._log.info(Fore.GREEN + '🈯 creating task for existing gamepad...')
                self._message_bus.loop.create_task(self._gamepad._gamepad_loop(self._gamepad_callback, lambda: self._gamepad_enabled), name=GAMEPAD_TASK_NAME)

    # ..........................................................................
    def _toggle_flood(self):
        if self._flood_enable:
            self._flood_enable = False
            self._log.info('flood disabled: ' + Fore.YELLOW + 'type \'w\' to enable.')
        else:
#           await asyncio.sleep(3.0) # delay before starting flood loop
            self._flood_enable = True
            self._log.info('flood enabled: ' + Fore.YELLOW + 'type \'w\' to disable.')

    # ..........................................................................
    def _toggle_motors(self):
        if self._motors:
            self._log.info('toggle motors...')
            if self._motors.loop_is_running():
                self._motors.stop_loop()
            else:
                self._motors.start_loop()
            self._log.debug('loop is running? ' + Fore.YELLOW + '{}'.format(self._motors.loop_is_running()))
        else:
            self._log.warning('no motors available.')

    # ..........................................................................
    def disable(self):
        '''
        Disable this publisher as well as shut down the message bus.
        '''
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

    # ..........................................................................
    def _waiting_for_message(self):
        _div = Fore.CYAN + Style.NORMAL + ' | '
        self._log.info('waiting for: | ' \
                + self._get_output(Fore.RED, 'PSID', self._triggered_ir_port_side) \
                + _div \
                + self._get_output(Fore.RED, 'PORT', self._triggered_ir_port) \
                + _div \
                + self._get_output(Fore.BLUE, 'CNTR', self._triggered_ir_cntr) \
                + _div \
                + self._get_output(Fore.GREEN, 'STBD', self._triggered_ir_stbd) \
                + _div \
                + self._get_output(Fore.GREEN, 'SSID', self._triggered_ir_stbd_side) \
                + _div \
                + self._get_output(Fore.RED, 'BPRT', self._triggered_bmp_port) \
                + _div \
                + self._get_output(Fore.BLUE, 'BCNT', self._triggered_bmp_cntr) \
                + _div \
                + self._get_output(Fore.GREEN, 'BSTB', self._triggered_bmp_stbd) \
                + _div )

    # message handling .........................................................

    def _accumulate_message(self, message):
        '''
        Processes the message, keeping count and providing a display of status.
        '''
        _event = message.event
        if _event is Event.BUMPER_PORT:
            self._print_event(Fore.RED, _event, message.value)
            if self._triggered_bmp_port < self._limit:
                self._triggered_bmp_port += 1
        elif _event is Event.BUMPER_CNTR:
            self._print_event(Fore.BLUE, _event, message.value)
            if self._triggered_bmp_cntr < self._limit:
                self._triggered_bmp_cntr += 1
        elif _event is Event.BUMPER_STBD:
            self._print_event(Fore.GREEN, _event, message.value)
            if self._triggered_bmp_stbd < self._limit:
                self._triggered_bmp_stbd += 1
        elif _event is Event.INFRARED_PORT_SIDE:
            self._print_event(Fore.RED, _event, message.value)
            if self._triggered_ir_port_side < self._limit:
                self._triggered_ir_port_side += 1
        elif _event is Event.INFRARED_PORT:
            self._print_event(Fore.RED, _event, message.value)
            if self._triggered_ir_port < self._limit:
                self._triggered_ir_port += 1
        elif _event is Event.INFRARED_CNTR:
            self._print_event(Fore.BLUE, _event, message.value)
            if self._triggered_ir_cntr < self._limit:
                self._triggered_ir_cntr += 1
        elif _event is Event.INFRARED_STBD:
            self._print_event(Fore.GREEN, _event, message.value)
            if self._triggered_ir_stbd < self._limit:
                self._triggered_ir_stbd += 1
        elif _event is Event.INFRARED_STBD_SIDE:
            self._print_event(Fore.GREEN, _event, message.value)
            if self._triggered_ir_stbd_side < self._limit:
                self._triggered_ir_stbd_side += 1
        else:
            self._log.debug(Fore.BLACK + Style.BRIGHT + 'other event: {}'.format(_event.description))

    # ......................................................
    def _print_event(self, color, event, value):
        self._log.info('event:\t' + color + Style.BRIGHT + '{}; value: {}'.format(event.description, value))

    # ......................................................
    def _get_output(self, color, label, value):
        if ( value == 0 ):
            _style = color + Style.BRIGHT
        elif ( value == 1 ):
            _style = color + Style.NORMAL
        elif ( value == 2 ):
            _style = color + Style.DIM
        else:
            _style = Fore.BLACK + Style.DIM
        return _style + '{0:>9}'.format( label if ( value < self._limit ) else '' )

    # ......................................................
    @property
    def all_triggered(self):
        return self._triggered_ir_port_side  >= self._limit \
            and self._triggered_ir_port      >= self._limit \
            and self._triggered_ir_cntr      >= self._limit \
            and self._triggered_ir_stbd      >= self._limit \
            and self._triggered_ir_stbd_side >= self._limit \
            and self._triggered_bmp_port     >= self._limit \
            and self._triggered_bmp_cntr     >= self._limit \
            and self._triggered_bmp_stbd     >= self._limit

    # ..........................................................................
    def print_help(self):
#        1         2         3         4         5         6         7         8         9         C         1         2         3         4
#2345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890
        self._log.info('''key map:

  ┏━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓
  ┃    1    ┃    2    ┃    3    ┃    4    ┃    5    ┃    6    ┃    7    ┃    8    ┃    9    ┃    0    ┃    -    ┃    +    ┃   DEL   ┃
  ┃ FUL AST ┃ HAF AST ┃ SLO AST ┃ DSL AST ┃  STOP   ┃ DSL AHD ┃ SLO AHD ┃ HAF AHD ┃ FUL AHD ┃  HALT   ┃  BRAKE  ┃  EVEN   ┃ SHUTDWN ┃
  ┗━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┛
       ┃    Q    ┃    W    ┃    E    ┃    R    ┃    T    ┃    Y    ┃    U    ┃    I    ┃    O    ┃    P    ┃    [    ┃    ]    ┃
       ┃  QUIT   ┃  FLOOD  ┃ GAMEPAD ┃  ROAM   ┃  NOOP   ┃  SNIFF  ┃         ┃  INFO   ┃ CLR TSK ┃ POP_MSG ┃ IN_PORT ┃ IN_STBD ┃
       ┗━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┓
            ┃    A    ┃    S    ┃    D    ┃    F    ┃    G    ┃    H    ┃    J    ┃    K    ┃    L    ┃    :    ┃    "    ┃   RET   ┃
            ┃ IR_PSID ┃ IR_PORT ┃ IR_CNTR ┃ IR_STBD ┃ IR_SSID ┃  HELP   ┃ BM_PORT ┃ BM_CNTR ┃ BM_STBD ┃ DE_PORT ┃ DE_STBD ┃  CLEAR  ┃
            ┗━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━━━━━━┛
                 ┃    Z    ┃    X    ┃    C    ┃    V    ┃    B    ┃    N    ┃    M    ┃    <    ┃    >    ┃    ?    ┃
                 ┃ MOTORS  ┃ SP_PORT ┃ TN_PORT ┃ VERBOSE ┃ TN_STBD ┃ SP_STBD ┃         ┃ DE_VELO ┃ IN_VELO ┃  HELP   ┃
                 ┗━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┛
    
  FUL AST:   full astern        QUIT:     quit application              IR_PSID:  port side infrared            MOTORS:   toggle motors
  HAF AST:   half astern        FLOOD:    toggle flood publisher        IR_PORT:  port infrared                 SP_PORT:  spin port
  SLO AST:   slow astern        SNIFF:    tirgger SNIFF behaviour       IR_CNTR:  center infrared               TN_PORT:  turn to port
  DSL AST:   dead slow astern   ROAM:     trigger ROAM behaviour        IR_STBD:  starboard infrared            VERBOSE:  toggle verbosity
  STOP:      stop               NOOP:     no operation event            IR_SSID:  starboard side infrared       TN_STBD:  turn to starboard 
  DSL AHD:   dead slow ahead    INFO:     print system information      HELP:     print help                    SP_STBD:  spin starboard
  SLO AHD:   slow ahead         CLR_TSK:  clear completed tasks         BM_PORT:  port bumper                    
  HAF AHD:   half ahead         POP_MSG:  pop messages from queue       BM_CNTR:  center bumper                 DE_VELO:  decrease velocity
  FUL AHD:   full ahead         IN_PORT:  increase port velocity        BM_STBD:  starboard bumper              IN_VELO:  increase velocity
  HALT:      halt               IN_STBD:  increase starboard velocity   DE_PORT:  decrease port velocity        HELP:     print help
  BRAKE:     brake                                                      DE_STBD:  decrease starboard velocity
  EVEN:      even velocity, port and stbd motors
  SHUTDOWN:  shut down robot
        ''')

    # ..........................................................................
    def get_event_for_char(self, och):
        '''
        Below are the mapped characters for IFS-based events, including several others:

           dec   char   usage

            39   ' *    increase stbd velocity
            59   ; *    increase port velocity
            44   , *    decrease velocity
            46   . *    increase velocity
            47   /      help
            61   + *    even velocity
            91   [ *    increase port velocity
            93   ] *    increase stbd velocity

            97   a *    port side infrared
            98   b *    turn to stbd
            99   c *    turn to port
           100   d *    cntr infrared
           101   e      gamepad
           102   f *    stbd infrared
           103   g *    stbd side infrared
           104   h
           105   i      info
           106   j *    port bumper
           107   k *    cntr bumper
           108   l *    stbd bumper
           109   m 
           110   n *    spin stbd
           111   o      clear task list
           112   p      pop message
           113   q
           114   r *    roam
           115   s *    port infrared
           116   t      noop (test message)
           117   u
           118   v      verbose
           119   w      toggle flood mode with random messages
           120   x *    spin port
           121   y *    sniff
           122   z      toggle motors loop
           127   del    shut down

        * represents robot sensor or control input.
        '''
        if och   == 39:  # ' decrease stbd velocity
            return Event.DECREASE_STBD_VELOCITY
        elif och == 44:  # , decrease velocity
            return Event.DECREASE_VELOCITY
        elif och == 45:  # - break
            return Event.BRAKE
        elif och == 46:  # . increase port velocity
            return Event.INCREASE_VELOCITY
        elif och == 48:  # 0 halt
            return Event.HALT
        elif och == 49:  # 1 full astern
            return Event.FULL_ASTERN
        elif och == 50:  # 2 half astern
            return Event.HALF_ASTERN
        elif och == 51:  # 3 slow astern
            return Event.SLOW_ASTERN
        elif och == 52:  # 4 dead slow astern
            return Event.DEAD_SLOW_ASTERN 
        elif och == 53:  # 5 stop
            return Event.STOP
        elif och == 54:  # 6 dead slow ahead
            return Event.DEAD_SLOW_AHEAD
        elif och == 55:  # 7 slow ahead
            return Event.SLOW_AHEAD    
        elif och == 56:  # 8 half ahead
            return Event.HALF_AHEAD   
        elif och == 57:  # 9 full ahead
            return Event.FULL_AHEAD  
        elif och == 59:  # . decrease port velocity
            return Event.DECREASE_PORT_VELOCITY
        elif och == 61:  # + even
            return Event.EVEN  
        elif och == 91:  # [ increase port velocity
            return Event.INCREASE_PORT_VELOCITY
        elif och == 93:  # . increase stbd velocity
            return Event.INCREASE_STBD_VELOCITY
        elif och == 97:  # a
            return Event.INFRARED_PORT_SIDE
        elif och == 98:  # b
            return Event.TURN_TO_STBD
        elif och == 99:  # c
            return Event.TURN_TO_PORT
        elif och == 100: # d
            return Event.INFRARED_CNTR
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
#       elif och == 109: # m
#           return Event.STOP
        elif och == 110: # n
            return Event.SPIN_STBD
        elif och == 114: # r
            return Event.ROAM
        elif och == 115: # s
            return Event.INFRARED_PORT
        elif och == 116: # s
            return Event.NOOP
        elif och == 120: # x
            return Event.SPIN_PORT
        elif och == 121: # y
            return Event.SNIFF
        elif och == 127: # del
            return Event.SHUTDOWN
        else:
            return None

# ..............................................................................
class _Getch():
    '''
    Provides non-blocking key input from stdin.
    '''
    def __init__(self):
        self._old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

    def available(self):
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

    def readchar(self):
        return sys.stdin.read(1)

    def close(self):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)

# ..............................................................................
class GamepadConnectException(Exception):
    '''
    Exception raised when unable to connect to Gamepad.
    '''
    pass

#EOF
#EOF