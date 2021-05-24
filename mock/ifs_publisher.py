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
# A mock Integrated Front Sensor (IFS) that responds to key presses. Kinda a
# robot front end when you don't actually # have a robot. This expands the
# notion a bit, as rather than provide a second key-input mechanism, this one
# is also used for keyboard control of the mocked robot, i.e., it includes
# events unrelated to the original IFS.
#

import sys, time, itertools, psutil, random
#from threading import Thread
import asyncio
import concurrent.futures
from asyncio.queues import Queue
from pathlib import Path
from colorama import init, Fore, Style
init()
try:
    import readchar
except ImportError:
    sys.exit(Fore.RED + "This script requires the readchar module.\nInstall with: pip3 install --user readchar" + Style.RESET_ALL)

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
        self._limit = 3
        self._fmt = '{0:>9}'
        self._log.info('ready.')

    # ................................................................
    def enable(self):
        super().enable()
        if self.enabled:
            for _task in asyncio.all_tasks(self._message_bus.loop):
                self._log.info('🐰 task: {}'.format(_task.get_name()))
                if _task.get_name() == IfsPublisher._PUBLISH_LOOP_NAME:
                    self._log.warning('already enabled.')
                    return
            # start loop as new task
            self._message_bus.loop.create_task(self._start_loop(), name=IfsPublisher._PUBLISH_LOOP_NAME)
            self._log.info('enabled')
        else:
            self._log.info(Fore.BLACK + '<<< enabled: {}'.format(self.enabled))

    async def _start_loop(self):
        # run in a custom thread pool:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            self._log.info('starting publish loop...')
            _result = self._message_bus.loop.run_in_executor(
                pool, await self._publish_loop(lambda: self.enabled))
            self._log.info('ending publish loop; result done: {}'.format(_result.done()))

    async def _publish_loop(self, f_is_enabled):
        self._log.info('🍏 start publish loop.')
        _loop_freq_hz  = 20
        while f_is_enabled():
            _count = next(self._counter)
            self._log.info(Fore.BLUE + '🍏 [{:03d}] begin loop...'.format(_count))
            # get key press, see if any sensor (key) has been activated
            ch  = readchar.readchar()
            och = ord(ch)
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
                await self._message_bus.pop_queue()
                continue
            elif och == 3 or och == 113: # 'q'
                self.disable()
                self._message_bus.disable()
                self._log.info(Fore.YELLOW + 'type Ctrl-C to exit.')
                continue
            elif och == 47 or och == 63: # '/' or '?' for help
                self.print_keymap()
                continue
            elif och == 118: # 'v' toggle verbose
                self._message_bus.verbose = not self._message_bus.verbose
                self._log.info('setting verbosity to: ' + Fore.YELLOW + '{}'.format(self._message_bus.verbose))
                continue
            elif och == 119: # 'w'
                self.flood_zone()
                continue
            # otherwise handle as event
            _event = self.get_event_for_char(och)
            if _event is not None:
                self._log.info('🍏 [{:03d}] "{}" ({}) pressed; publishing message for event: {}'.format(_count, ch, och, _event))
                _message = self._message_factory.get_message(_event, True)
#               await self._publish_queue.put(_message)
                await super().publish(_message)
                self._log.info('publish_loop() loop end...')
            else:
                self._log.info('[{:03d}] unmapped key "{}" ({}) pressed.'.format(_count, ch, och))
            await asyncio.sleep(0.05)
            self._log.info(Fore.BLUE + '🍏 [{:03d}] end publish loop.'.format(_count))
        self._log.info('🍏 publish loop complete.')

    # ..........................................................................
    def flood_zone(self):
        _flood = self._message_bus.get_publisher('flood')
        if _flood:
            _flood.suppress(not _flood.suppressed)
            if _flood.suppressed:
                self._log.info('publisher \'{}\' suppressed.'.format(_flood.name))
            else:
                self._log.info('publisher \'{}\' not suppressed.'.format(_flood.name))
        else:
            self._log.warning('no \'flood\' publisher found on bus.'.format(_flood.name))

    # ................................................................
    def print_sys_info(self):
        _M = 1000000
        _vm = psutil.virtual_memory()
        self._log.info('virtual memory: \t' + Fore.YELLOW + 'total: {:4.1f}MB; available: {:4.1f}MB ({:5.2f}%); used: {:4.1f}MB; free: {:4.1f}MB'.format(\
                _vm[0]/_M, _vm[1]/_M, _vm[2], _vm[3]/_M, _vm[4]/_M))
        # svmem(total=10367352832, available=6472179712, percent=37.6, used=8186245120, free=2181107712, active=4748992512, inactive=2758115328, buffers=790724608, cached=3500347392, shared=787554304)
        _sw = psutil.swap_memory()
        # sswap(total=2097147904, used=296128512, free=1801019392, percent=14.1, sin=304193536, sout=677842944)
        self._log.info('swap memory:    \t' + Fore.YELLOW + 'total: {:4.1f}MB; used: {:4.1f}MB; free: {:4.1f}MB ({:5.2f}%)'.format(\
                _sw[0]/_M, _sw[1]/_M, _sw[2]/_M, _sw[3]))
        temperature = self.read_cpu_temperature()
        if temperature:
            self._log.info('cpu temperature:\t' + Fore.YELLOW + '{:5.2f}°C'.format(temperature))
        else:
#           self._log.info('cpu temperature:\t' + Fore.YELLOW + 'n/a')
            pass

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
    def waiting_for_message(self):
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

    def process_message(self, message):
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
        return _style + self._fmt.format( label if ( value < self._limit ) else '' )

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
   ┃  QUIT   ┃  FLOOD  ┃  SNIFF  ┃  ROAM   ┃  NOOP   ┃         ┃         ┃  INFO   ┃ CLR TSK ┃ POP_MSG ┃   ┅━┻━━━━━━━━━┛
   ┗━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┛   ┅━┳━━━━━━━━━┓
        ┃    A    ┃    S    ┃    D    ┃    F    ┃    G    ┃    H    ┃    J    ┃    K    ┃    L    ┃          ┃   RET   ┃
        ┃ IR_PSID ┃ IR_PORT ┃ IR_CNTR ┃ IR_STBD ┃ IR_SSID ┃  HALT   ┃         ┃         ┃         ┃          ┃  CLEAR  ┃
        ┗━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━━┻━━━┳━━━━━┛
             ┃    Z    ┃    X    ┃    C    ┃    V    ┃    B    ┃    N    ┃    M    ┃    <    ┃    >    ┃    ?    ┃
             ┃ BM_PORT ┃ BM_CNTR ┃ BM_STBD ┃ VERBOSE ┃  BRAKE  ┃  STOP   ┃         ┃ DN_VELO ┃ UP_VELO ┃  HELP   ┃
             ┗━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┛

   QUIT:      quit application                IR_PSID:   port side infrared event           BM_PORT:   port bumper
   FLOOD:     toggle flood publisher          IR_PORT:   port infrared event                BM_CNTR:   center bumper
   SNIFF:     tirgger SNIFF behaviour         IR_CNTR:   center infrared event              BM_STBD:   starboard bumper
   ROAM:      trigger ROAM behaviour          IR_STBD:   starboard infrared event           VERBOSE:   toggle verbosity
   NOOP:      no operation event              IR_SSID:   starboard side infrared event      BRAKE:     brake motors
   INFO:      print system information        HALT:      halt motors                        STOP:      stop motors
   CLR_TSK:   clear completed tasks                                                         DN_VELO:   slow down motors
   POP_MSG:   pop messages from queue                                                       UP_VELO:   speed up motors
   SHUTDOWN:  shut down robot                 CLEAR:     clear screen                       HELP:      print help

        ''')
#           elif _event == Event.AHEAD:
#           elif _event == Event.ASTERN:
        self._log.info('note:\t' + Fore.YELLOW + 'will exit after receiving 3 events on each sensor.')
        print('')

    # ..........................................................................
    def get_event_for_char(self, och):
        '''
        Below are the mapped characters for IFS-based events, including several others:

           oct   dec   hex   char   usage

            54   44    2C    , *    increase motors speed (both)
            56   46    2E    . *    decrease motors speed (both)

           141   97    61    a *    port side IR
           142   98    62    b *    brake
           143   99    63    c *    stbd BMP
           144   100   64    d *    cntr IR
           145   101   65    e *    sniff
           146   102   66    f *    stbd IR
           147   103   67    g *    stbd side IR
           150   104   68    h *    halt
           151   105   69    i      info
           152   106   6A    j
           153   107   6B    k
           154   108   6C    l
           155   109   6D    m
           156   110   6E    n *    stop
           157   111   6F    o      clear task list
           160   112   70    p      pop message
           161   113   71    q
           162   114   72    r *    roam
           163   115   73    s *    port IR
           164   116   74    t      noop (test message)
           165   117   75    u
           166   118   76    v      verbose
           167   119   77    w      flood with random messages
           170   120   78    x *    cntr BMP
           171   121   79    y
           172   122   7A    z  *   port BMP
           177   127   7f   del     shut down

        * represents robot sensor or control input.
        '''
        if och   == 44:  # ,
            return Event.DECREASE_SPEED
        elif och   == 46:  # .
            return Event.INCREASE_SPEED
        elif och   == 97:  # a
            return Event.INFRARED_PORT_SIDE
        elif och == 98:  # b
            return Event.BRAKE
        elif och == 99:  # c
            return Event.BUMPER_STBD
        elif och == 100: # d
            return Event.INFRARED_CNTR
        elif och == 101: # e
            return Event.SNIFF
        elif och == 102: # f
            return Event.INFRARED_STBD
        elif och == 103: # g
            return Event.INFRARED_STBD_SIDE
        elif och == 104: # h
            return Event.HALT
        elif och == 110: # n
            return Event.STOP
        elif och == 114: # r
            return Event.ROAM
        elif och == 115: # s
            return Event.INFRARED_PORT
        elif och == 116: # s
            return Event.NOOP
        elif och == 120: # x
            return Event.BUMPER_CNTR
        elif och == 122: # z
            return Event.BUMPER_PORT
        elif och == 127: # del
            return Event.SHUTDOWN
        else:
            return None

#EOF
