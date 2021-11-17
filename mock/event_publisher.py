#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-10-16
#
# _Getch at bottom.
#

import sys, time, itertools, random, traceback
import select, tty, termios # used by _Getch
import select
import asyncio
import concurrent.futures
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

import core.globals as globals
globals.init()

from core.message_factory import MessageFactory
from core.logger import Logger, Level
from core.event import Event
from core.util import Util
from core.publisher import Publisher

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class EventPublisher(Publisher):

    _LISTENER_LOOP_NAME = '__key_listener_loop'

    _KEY_EVENT_MAP = dict([
        ( 27,  Event.SHUTDOWN ),
        ( 33,  Event.EXPERIMENT_1 ), # '!' (on US keyboard)
        ( 64,  Event.EXPERIMENT_2 ), # '@'
        ( 35,  Event.EXPERIMENT_3 ), # '#'
        ( 36,  Event.EXPERIMENT_4 ), # '$'
        ( 37,  Event.EXPERIMENT_5 ), # '%'
        ( 94,  Event.EXPERIMENT_6 ), # '^'
        ( 38,  Event.EXPERIMENT_7 ), # '&'
        ( 39,  Event.DECREASE_STBD_VELOCITY ),
        ( 44,  Event.DECREASE_VELOCITY ),
        ( 45,  Event.BRAKE ),
        ( 46,  Event.INCREASE_VELOCITY ),
        ( 48,  Event.STOP ),
        ( 49,  Event.FULL_ASTERN ),
        ( 50,  Event.HALF_ASTERN ),
        ( 51,  Event.SLOW_ASTERN ),
        ( 52,  Event.DEAD_SLOW_ASTERN ),
        ( 53,  Event.HALT ),
        ( 54,  Event.DEAD_SLOW_AHEAD ),
        ( 55,  Event.SLOW_AHEAD ),
        ( 56,  Event.HALF_AHEAD ),
        ( 57,  Event.FULL_AHEAD ),
        ( 59,  Event.DECREASE_PORT_VELOCITY ),
        ( 61,  Event.EVEN ),
        ( 91,  Event.INCREASE_PORT_VELOCITY ),
        ( 93,  Event.INCREASE_STBD_VELOCITY ),
        ( 97,  Event.INFRARED_PSID ),
        ( 98,  Event.TURN_TO_STBD ),
        ( 99,  Event.TURN_TO_PORT ),
        ( 100, Event.INFRARED_CNTR ),
        ( 102, Event.INFRARED_STBD ),
        ( 103, Event.INFRARED_SSID ),
        ( 106, Event.BUMPER_PORT ),
        ( 107, Event.BUMPER_CNTR ),
        ( 108, Event.BUMPER_STBD ),
        ( 109, Event.MOTH ),
        ( 110, Event.SPIN_STBD ),
        ( 111, Event.SWERVE ),
        ( 114, Event.ROAM ),
        ( 115, Event.INFRARED_PORT ),
        ( 116, Event.AVOID ),
        ( 117, Event.IDLE ),
        ( 120, Event.SPIN_PORT ),
#       ( 121, Event.SNIFF ),
        ( 127, Event.SHUTDOWN ),
    ])

    _RANDOM_EVENTS = [
            Event.INFRARED_PSID, Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD, Event.INFRARED_SSID,
            Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD,
            Event.INCREASE_VELOCITY, Event.DECREASE_VELOCITY,
            Event.BRAKE, Event.HALT, Event.STOP,
            Event.ROAM, Event.AVOID, Event.MOTH, Event.SNIFF, Event.IDLE,
            Event.NOOP, Event.SHUTDOWN,
        ]

    '''
    A mock IFS, Gamepad and 'Flood' event source.
    EventPublisher extends the Publisher class providing robot events from three
    sources:

    First, a mock Integrated Front Sensor (IFS) that responds to key presses,
      acting as a robot front sensor array for when you don't actually have a
      robot. Rather than provide simply a second key-input mechanism, this can
      also be used for keyboard control of the mocked robot, i.e., it includes
      events unrelated to the original IFS.

    Second, if a Bluetooth-based Gamepad is paired and connected, this will
      forward events generated by the Gamepad class to the MessageBus.

    Finally, there is also has a "flood" mode that auto-generates random
      event-bearing messages at a random interval. This is currently disabled
      to free up its key for something else.

    :param config:            the application configuration
    :param message_bus:       the asynchronous message bus
    :param message_factory:   the factory for creating messages
    :param motor_controller:  the motor controller
    :param system:            access to system information
    :param level:             the log level
    '''
    def __init__(self, config, message_bus, message_factory, motor_controller, system, level=Level.INFO):
        Publisher.__init__(self, 'event', config, message_bus, message_factory, level=level)
        self._motor_ctrl      = motor_controller
        self._system          = system
        self._level           = level
        self._counter         = itertools.count()
        self._getch           = _Getch()
        self._flood_enable    = False
        self._message_limit   = 3 # fixed message limit (testing only)
        self._clip = lambda n: self._ir_min if n <= self._ir_min else self._ir_max if n >= self._ir_max else n
        # configuration ....................................
        _cfg = config['kros'].get('mock').get('event_publisher')
        self._ir_value        = _cfg.get('ir_init_value')       # initial value of mocked center IR
        self._ir_min          = _cfg.get('ir_min')              # minimum center IR value
        self._ir_max          = _cfg.get('ir_max')              # maximum center IR value
        self._ir_incr         = _cfg.get('ir_incr')             # IR step increment
        self._ir_direction    = -1                              # initial direction (down)
        self._publish_delay_sec = _cfg.get('publish_delay_sec') # delay after IFS event
        self._loop_delay_sec  = _cfg.get('noop_loop_delay_sec') # delay on noop loop
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if self._message_bus.get_task_by_name(EventPublisher._LISTENER_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                self._log.info('creating task for key listener loop...')
                self._message_bus.loop.create_task(self._key_listener_loop(lambda: self.enabled), name=EventPublisher._LISTENER_LOOP_NAME)
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable publisher.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _key_listener_loop(self, f_is_enabled):
        self._log.info('starting key listener loop:\t' + Fore.YELLOW + 'type \'?\' for help, \'q\' or Ctrl-C to exit.')
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
                        if och == 9: # 'tab' toggle gamepad
                            self._toggle_gamepad()
                            continue
                        if och == 10 or och == 13: # LF or CR to print 48 newlines
                            print(Util.repeat('\n',48))
                            continue
                        elif och == 101: # 'e' toggle pot
                            self._toggle_pot()
                            continue
                        elif och == 104: # 'h' help
                            self.print_help()
                            continue
                        elif och == 105: # 'i' print info
                            self._print_info()
                            continue
#                       elif och == 111: # 'o'
#                           self._message_bus.clear_tasks()
#                           continue
                        elif och == 112: # 'p'
#                           raise NotImplementedError
                            await self._message_bus.pop_queue()
                            continue
                        elif och == 3 or och == 113: # 'q'
                            self._log.info(Fore.YELLOW + 'shutting down on \'q\' or Ctrl-C...')
                            _event = Event.SHUTDOWN
#                           self.disable()
#                           continue
                        elif och == 47 or och == 63: # '/' or '?' for help
                            self.print_help()
                            continue
                        elif och == 92: # '\' toggle system clock
                            self._toggle_clock()
                            continue
                        elif och == 118: # 'v' toggle verbose
                            self._toggle_verbosity()
                            continue
                        elif och == 119: # 'w' toggle IFS publisher
#                           self._toggle_flood()
                            self._toggle_ifs()
                            continue
                        elif och == 121: # 'y'
                            self._toggle_behaviour_manager()
                            continue
                        elif och == 122: # 'z' toggle motors loop
                            self._toggle_motors()
                            continue
                        elif och in [ 33, 64, 35, 36, 37, 94, 38 ]: # shift-numeric
                            _event = EventPublisher._KEY_EVENT_MAP[och]
                            self._toggle_experiment(_event)
                            continue
                        elif 65 <= och <= 90: # then we're uppercased alpha
                            self._ir_direction *= -1 # toggle direction
                            self._log.info('toggle increment direction: {:d}'.format(self._ir_direction))
                            och += 32
                        else:
                            pass
                        if not _event:
                            try:
                                # otherwise handle as event
                                _event = EventPublisher._KEY_EVENT_MAP[och]
                            except KeyError as e:
                                self._log.error('unmapped key \'{}\' ({}) pressed.'.format(ch, och))
                        if _event is not None:
                            self._log.info('key \'{}\' ({}) pressed; key-publishing message for event: {}'.format(ch, och, _event))
                            _message = self._message_factory.create_message(_event, True)
                            if Event.is_infrared_event(_event):
                                _message.value = self._get_infrared_value() # we use a rising and falling value
                            elif Event.is_bumper_event(_event):
                                _message.value = 0 # bumpers by definition have a distance of zero
                            else:
                                _message.value = dt.now() # we use a timestamp to guarantee each message is different
                            self._log.info('key-publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.label))
                            await Publisher.publish(self, _message)
                            self._log.info('key-published message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.label))
                        else:
                            self._log.warning('unmapped key \'{}\' ({}) pressed.'.format(ch, och))
                        await asyncio.sleep(self._publish_delay_sec)
                    else:
                        self._log.warning('readchar returned null.')
                elif self._flood_enable:
                    _event = self._get_random_event()
                    _message = self._message_factory.create_message(_event, True)
                    self._log.info('flood-publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.label))
                    await Publisher.publish(self, _message)
                    self._log.info('flood-published message:' + Fore.WHITE + ' {}.'.format(_message.name))
                    await asyncio.sleep(random.triangular(0.2, 5.0, 2.0))
                else:
                    # nothing happening...
                    self._log.debug('[{:03d}] waiting for key press...'.format(_count))
                    await asyncio.sleep(self._loop_delay_sec)

                self._log.debug('[{:03d}] END loop.'.format(_count))
            self._log.info('publish loop complete.')
        except Exception as e:
            self._log.error('{} in publish loop: {}\n{}'.format(type(e), e, traceback.format_exc()))
        finally:
            if self._getch:
                self._getch.close()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _print_info(self):
        try:
            self._log.heading('System Information','Memory, CPU and Message Bus Information.')
            self._system.print_sys_info()
            self._print_power_info()
            self._message_bus.print_system_status()
            self._print_behaviour_info()
            self._motor_ctrl.print_motor_status()
            self._motor_ctrl.print_info(None)
            self._print_ifs_info()
            self._print_macro_info()
            self._print_experiment_info()
            self._print_log_info()
        except Exception as e:
            self._log.error('error printing system info: {}'.format(e))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _print_power_info(self):
        _battery_check = self._message_bus.get_publisher('battery')
        if _battery_check:
            _msg = _battery_check.get_battery_info()
        else:
            _msg = 'no power information available.'
        self._log.info('power supply: \t' + Fore.YELLOW + '{}'.format(_msg))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _print_ifs_info(self):
        _battery_check = self._message_bus.get_publisher('battery')
        _ifs = globals.get('ifs')
        if _ifs:
            _ifs.print_info()
        else:
            self._log.info('integrated front sensor:  \t' + Fore.YELLOW + 'no ifs information available.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _print_macro_info(self):
        _kros = globals.get('kros')
        _macro_publisher = _kros.get_macro_publisher()
        if _macro_publisher:
            _macro_publisher.print_info()
        else:
            self._log.info('macro processor:      \t' + Fore.YELLOW + 'disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _print_experiment_info(self):
        _kros = globals.get('kros')
        _experiment_mgr = _kros.get_experiment_manager()
        if _experiment_mgr:
            _experiment_mgr.print_info()
        else:
            self._log.info('experimental features:\t' + Fore.YELLOW + 'disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _print_log_info(self):
        '''
        Print global statistics about the log.
        '''
        self._log.info('log statistics:\t' + Fore.YELLOW
                + '{:d} debug; {:d} info; {:d} warnings; {:d} errors; {:d} critical.'.format(*self._log.stats.counts))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_infrared_value(self):
        '''
        Returns a continuually rising and falling value.
        This goes from a minimum of 50 to a maximum of 250,
        stepping by an increment of 10.

        This is a special case; does it belong here?
        '''
        self._ir_value += ( self._ir_incr * self._ir_direction )
        if self._ir_value <= self._ir_min:
            self._ir_direction = 1
        elif self._ir_value >= self._ir_max:
            self._ir_direction = -1
        self._ir_value = self._clip(self._ir_value)
        self._log.info('infrared center: {:d}'.format(self._ir_value))
        return self._ir_value

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_random_event(self):
        '''
        Returns one of the randomly-assigned event types.
        '''
        return EventPublisher._RANDOM_EVENTS[random.randint(0, len(EventPublisher._RANDOM_EVENTS)-1)]

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _toggle_pot(self):
        _pot = self._message_bus.get_publisher('pot')
        if _pot:
            if _pot.enabled:
                self._log.info(Fore.YELLOW + 'disabling potentiometer...')
                _pot.suppress()
                _pot.disable()
                self._log.info('potentiometer disabled.')
            else:
                self._log.info(Fore.YELLOW + 'enabling potentiometer...')
                try:
                    _pot.enable()
                    _pot.release()
                except Exception as e:
                    self._log.error('potentiometer error: {}'.format(e))
                self._log.info('potentiometer enabled.')
        else:
            self._log.info(Fore.YELLOW + 'potentiometer not found.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _toggle_clock(self):
        _clock = self._message_bus.get_publisher('clock')
        if _clock:
            if _clock.enabled:
                _clock.disable()
                self._log.info('system clock disabled.')
            else:
                _clock.enable()
                self._log.info('system clock enabled.')
        else:
            self._log.info(Fore.YELLOW + 'system clock not found.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _toggle_verbosity(self):
        self._message_bus.verbose = not self._message_bus.verbose
        if self._message_bus.verbose:
            self._log.info('setting verbosity to: ' + Fore.YELLOW + '{}'.format(self._message_bus.verbose))
        else:
            print(Fore.CYAN + Util.repeat(' ',60) + ': setting verbosity to: ' + Fore.YELLOW + '{}'.format(self._message_bus.verbose))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _toggle_gamepad(self):
        raise Exception('Todo') 
        _kros = globals.get('kros')
        _gamepad_publisher = _kros.get_gamepad_publisher()
        if _gamepad_publisher:
            _gamepad_publisher.toggle()
        else:
            self._log.info('gamepad publisher: ' + Fore.YELLOW + 'disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _toggle_ifs(self):
        '''
        Toggles the suppress/release flag of the IfsPublisher.
        '''
        _kros = globals.get('kros')
        _ifs_publisher = _kros.get_ifs_publisher()
        if _ifs_publisher:
            _ifs_publisher.toggle()
        else:
            self._log.info('ifs publisher: ' + Fore.YELLOW + 'disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _toggle_flood(self):
        '''
        Toggles the flood mode that publishes random messages.
        This is currently not used.
        '''
        if self._flood_enable:
            self._flood_enable = False
            self._log.info('flood disabled: ' + Fore.YELLOW + 'type \'w\' to enable.')
        else:
#           await asyncio.sleep(3.0) # delay before starting flood loop
            self._flood_enable = True
            self._log.info('flood enabled: ' + Fore.YELLOW + 'type \'w\' to disable.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _toggle_experiment(self, event):
        self._log.debug('😃 toggle experiment "{}"'.format(event))
        _kros = globals.get('kros')
        _experiment_mgr = _kros.get_experiment_manager()
        _experiment_mgr.toggle_experiment(event)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _print_behaviour_info(self):
        _kros = globals.get('kros')
        _behaviour_mgr = _kros.get_behaviour_manager()
        if _behaviour_mgr:
            _behaviour_mgr.print_info()
        else:
            self._log.info('behaviour manager: ' + Fore.YELLOW + 'disabled')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _toggle_behaviour_manager(self):
        _kros = globals.get('kros')
        _behaviour_mgr = _kros.get_behaviour_manager()
        if _behaviour_mgr:
            if _behaviour_mgr.suppressed:
                _behaviour_mgr.release()
            else:
                _behaviour_mgr.suppress()
        else:
            self._log.info('no behaviour manager available.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _toggle_motors(self):
        if self._motor_ctrl:
            self._log.info('toggle motors...')
            if self._motor_ctrl.loop_is_running:
                self._motor_ctrl.stop_loop()
            else:
                self._motor_ctrl.start_loop()
            self._log.debug('loop is running? ' + Fore.YELLOW + '{}'.format(self._motor_ctrl.loop_is_running))
        else:
            self._log.warning('no motors available.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher as well as shut down the message bus.
        '''
        self._message_bus.disable()
        Publisher.disable(self)
        self._log.info('disabled publisher.')

    # message handling ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _print_event(self, color, event, value):
        self._log.info('event:\t' + color + Style.BRIGHT + '{}; value: {}'.format(event.label, value))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_output(self, color, label, value):
        if ( value == 0 ):
            _style = color + Style.BRIGHT
        elif ( value == 1 ):
            _style = color + Style.NORMAL
        elif ( value == 2 ):
            _style = color + Style.DIM
        else:
            _style = Fore.BLACK + Style.DIM
        return _style + '{0:>9}'.format( label if ( value < self._message_limit ) else '' )

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_help(self):
        self._log.debug(Fore.BLUE + Style.DIM + '''
0        1         2         3         4         5         6         7         8         9         C         1         2         3         4
12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890''')
        _key_map_header_x = '''
       ┏━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓
       ┃ SHIFT-1 ┃ SHIFT-2 ┃ SHIFT-3 ┃ SHIFT-4 ┃ SHIFT-5 ┃ SHIFT-6 ┃ SHIFT-7 ┃
       ┃  EXP 1  ┃  EXP 2  ┃  EXP 3  ┃  EXP 4  ┃  EXP 5  ┃  EXP 6  ┃  EXP 7  ┃
       ┣━━━━━━━━━╋━━━━━━━━━╋━━━━━━━━━╋━━━━━━━━━╋━━━━━━━━━╋━━━━━━━━━╋━━━━━━━━━╋━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓'''

        _key_map_header = '''
       ┏━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓'''


        _key_map_body = '''
       ┃    1    ┃    2    ┃    3    ┃    4    ┃    5    ┃    6    ┃    7    ┃    8    ┃    9    ┃    0    ┃    -    ┃    =    ┃   DEL   ┃
       ┃ FUL AST ┃ HAF AST ┃ SLO AST ┃ DSL AST ┃  HALT   ┃ DSL AHD ┃ SLO AHD ┃ HAF AHD ┃ FUL AHD ┃  STOP   ┃  BRAKE  ┃  EVEN   ┃ SHUTDWN ┃
  ┏━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┛
  ┃   TAB   ┃    Q    ┃    W    ┃    E    ┃    R    ┃    T    ┃    Y    ┃    U    ┃    I    ┃    O    ┃    P    ┃    [    ┃    ]    ┃
  ┃ GAMEPAD ┃  QUIT   ┃   IFS   ┃   POT   ┃  ROAM   ┃  AVOID  ┃ BEH_MGR ┃  IDLE   ┃  INFO   ┃ SWERVE  ┃ POP_MSG ┃ IN_PORT ┃ IN_STBD ┃
  ┗━━━━━━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┓
                 ┃    A    ┃    S    ┃    D    ┃    F    ┃    G    ┃    H    ┃    J    ┃    K    ┃    L    ┃    :    ┃    "    ┃   RET   ┃
                 ┃ IR_PSID ┃ IR_PORT ┃ IR_CNTR ┃ IR_STBD ┃ IR_SSID ┃  HELP   ┃ BM_PORT ┃ BM_CNTR ┃ BM_STBD ┃ DE_PORT ┃ DE_STBD ┃  CLEAR  ┃
                 ┗━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┻━━━━┳━━━━┛
                      ┃    Z    ┃    X    ┃    C    ┃    V    ┃    B    ┃    N    ┃    M    ┃    <    ┃    >    ┃    ?    ┃    \    ┃
                      ┃ MTR_INF ┃ SP_PORT ┃ TN_PORT ┃ VERBOSE ┃ TN_STBD ┃ SP_STBD ┃  MOTH   ┃ DE_VELO ┃ IN_VELO ┃  HELP   ┃  CLOCK  ┃
                      ┗━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━┛

                               TAB:      toggle gamepad
  FUL AST:   full astern       QUIT:     quit application             IR_PSID:  port side infrared           MTR_INF:  toggle motor info
  HAF AST:   half astern       IFS:      toggle ifs                   IR_PORT:  port infrared                SP_PORT:  spin port
  SLO AST:   slow astern       POT:      toggle potentiometer         IR_CNTR:  center infrared              TN_PORT:  turn to port
  DSL AST:   dead slow astern  ROAM:     trigger roam behaviour       IR_STBD:  starboard infrared           VERBOSE:  toggle verbosity
  HALT:      halt              AVOID:    trigger avoidance behaviour  IR_SSID:  starboard side infrared      TN_STBD:  turn to starboard
  DSL AHD:   dead slow ahead   BEH_MGR:  toggle behaviour manager     HELP:     print help                   SP_STBD:  spin starboard
  SLO AHD:   slow ahead        IDLE:     send idle message            BM_PORT:  port bumper                  MOTH:     trigger moth behaviour
  HAF AHD:   half ahead        INFO:     print system information     BM_CNTR:  center bumper                DE_VELO:  decrease velocity
  FUL AHD:   full ahead        SWERVE:   toggle swerve behaviour      BM_STBD:  starboard bumper             IN_VELO:  increase velocity
  STOP:      stop              POP_MSG:  pop messages from queue      DE_PORT:  decrease port velocity       HELP:     print help
  BRAKE:     brake             IN_PORT:  increase port velocity       DE_STBD:  decrease starboard velocity  CLOCK:    toggle system clock
  EVEN:      even velocity     IN_STBD:  increase starboard velocity  RET:      clear display
  SHUTDOWN:  shut down robot
        '''

        _kros = globals.get('kros')
        _experiment_mgr = _kros.get_experiment_manager()
        self._log.info('key map:\n{}{}'.format(_key_map_header_x if _experiment_mgr and _experiment_mgr.enabled else _key_map_header, _key_map_body))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
