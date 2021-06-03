#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2020-11-06
#
# A mock Integrated Front Sensor (IFS) that responds to key presses. Acts as a
# robot front sensor array for when you don't actually have a robot. Rather
# than provide simply a second key-input mechanism, this can also be used for
# keyboard control of the mocked robot, i.e., it includes events unrelated to
# the original IFS. It also has a "flood" mode that auto-generates random
# event-bearing messages at a random interval.
#

import sys, time, itertools, psutil, random
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

# ...............................................................
class IfsPublisher(Publisher):

    _PUBLISH_LOOP_NAME = '__publish-loop__'

    '''
    A mock IFS.
    '''
    def __init__(self, message_bus, message_factory, exit_on_complete=True, level=Level.INFO):
        super().__init__('ifs', message_bus, message_factory, level)
        self._exit_on_complete = exit_on_complete
        self._counter  = itertools.count()
        self._triggered_ir_port_side = self._triggered_ir_port  = self._triggered_ir_cntr  = self._triggered_ir_stbd  = \
        self._triggered_ir_stbd_side = self._triggered_bmp_port = self._triggered_bmp_cntr = self._triggered_bmp_stbd = 0
        self._getch          = _Getch()
        self._flood_enable   = False
        self._gamepad_enable = False
        # TODO configuration
        self._publish_delay_sec   = 0.05 # delay after IFS event
        self._loop_delay_sec      = 0.5  # delay on noop loop
        self._limit               = 3
        self._log.info('ready.')

    # ................................................................
    def enable(self):
        super().enable()
        if self.enabled:
            if self._message_bus.get_task_by_name(IfsPublisher._PUBLISH_LOOP_NAME):
                self._log.warning('already enabled.')
                return
            self._message_bus.loop.create_task(self._key_listener_loop(lambda: self.enabled), name='__key_listener_loop')
            self._log.info('enabled')
        else:
            self._log.info(Fore.BLACK + '<<< enabled: {}'.format(self.enabled))

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
                            self.print_keymap()
                            continue
                        elif och == 118: # 'v' toggle verbose
                            self._message_bus.verbose = not self._message_bus.verbose
                            self._log.info('setting verbosity to: ' + Fore.YELLOW + '{}'.format(self._message_bus.verbose))
                            continue
                        elif och == 101: # 'e' toggle gamepad
                            await self._toggle_gamepad()
                            continue
                        elif och == 119: # 'w' toggle flood mode
                            self._toggle_flood()
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

    # ..........................................................................
    async def _toggle_gamepad(self):
        if self._gamepad_enable:
            self._gamepad_enable = False
            self._log.info('gamepad disabled: ' + Fore.YELLOW + 'type \'e\' to enable.')
        else:
            self._gamepad_enable = True
            self._log.info('gamepad enabled: ' + Fore.YELLOW + 'type \'e\' to disable.')
        _message = self._message_factory.get_message(Event.GAMEPAD, self._gamepad_enable)
        self._log.info('gamepad control-publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
        await super().publish(_message)

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
            self._log.info(Fore.BLACK + Style.BRIGHT + 'other event: {}'.format(_event.description))

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
    def print_keymap(self):
#        1         2         3         4         5         6         7         8         9         C         1         2
#23456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890
        self._log.info('''key map:
                                                                                                           ┅━┳━━━━━━━━━┓
   ┏━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓     ┃   DEL   ┃
   ┃    Q    ┃    W    ┃    E    ┃    R    ┃    T    ┃    Y    ┃    U    ┃    I    ┃    O    ┃    P    ┃     ┃ SHUTDWN ┃
   ┃  QUIT   ┃  FLOOD  ┃ GAMEPAD ┃  ROAM   ┃  NOOP   ┃  SNIFF  ┃         ┃  INFO   ┃ CLR TSK ┃ POP_MSG ┃   ┅━┻━━━━━━━━━┛
   ┗━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┛   ┅━┳━━━━━━━━━┓
        ┃    A    ┃    S    ┃    D    ┃    F    ┃    G    ┃    H    ┃    J    ┃    K    ┃    L    ┃          ┃   RET   ┃
        ┃ IR_PSID ┃ IR_PORT ┃ IR_CNTR ┃ IR_STBD ┃ IR_SSID ┃         ┃ BM_PORT ┃ BM_CNTR ┃ BM_STBD ┃          ┃  CLEAR  ┃
        ┗━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━━┻━━━┳━━━━━┛
             ┃    Z    ┃    X    ┃    C    ┃    V    ┃    B    ┃    N    ┃    M    ┃    <    ┃    >    ┃    ?    ┃
             ┃         ┃         ┃         ┃ VERBOSE ┃  BRAKE  ┃  HALT   ┃  STOP   ┃ DN_VELO ┃ UP_VELO ┃  HELP   ┃
             ┗━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┛

   QUIT:      quit application                IR_PSID:   port side infrared event
   FLOOD:     toggle flood publisher          IR_PORT:   port infrared event
   SNIFF:     tirgger SNIFF behaviour         IR_CNTR:   center infrared event
   ROAM:      trigger ROAM behaviour          IR_STBD:   starboard infrared event           VERBOSE:   toggle verbosity
   NOOP:      no operation event              IR_SSID:   starboard side infrared event      BRAKE:     brake motors
   INFO:      print system information                                                      HALT:      halt motors
   CLR_TSK:   clear completed tasks           BM_PORT:   port bumper                        STOP:      stop motors
   POP_MSG:   pop messages from queue         BM_CNTR:   center bumper                      DN_VELO:   slow down motors
                                              BM_STBD:   starboard bumper                   UP_VELO:   speed up motors
   SHUTDOWN:  shut down robot                 CLEAR:     clear screen                       HELP:      print help

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
           145   101   65    e      gamepad
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
           171   121   79    y *    sniff
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

#EOF
