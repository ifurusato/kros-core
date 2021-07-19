#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2021-07-19
#
# The NZPRG K-Series Robot Operating System (KROS), including its command line
# interface (CLI).
#
#        1         2         3         4         5         6         7         8         9         C
#234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890

import os, sys, signal, time, threading, traceback
import argparse, psutil
from pathlib import Path
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event
from core.system import System
from core.component import Component
from core.fsm import FiniteStateMachine
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.config_loader import ConfigLoader
from core.i2c_scanner import I2CScanner

from core.controller import Controller
from core.publisher import Publisher
from core.subscriber import Subscriber, GarbageCollector

from mock.event_publisher import EventPublisher
from mock.bumper_subscriber import BumperSubscriber
from mock.infrared_subscriber import InfraredSubscriber
from mock.motor_subscriber import MotorSubscriber
#from mock.gamepad_publisher import GamepadPublisher
#from mock.gamepad_controller import GamepadController
from behave.behaviour_manager import BehaviourManager
from behave.avoid import Avoid
from behave.roam import Roam
from behave.moth import Moth
from behave.sniff import Sniff
from behave.idle import Idle

from hardware.motor_configurer import MotorConfigurer
from hardware.pid_motor_ctrl import PIDMotorController

led_0_path = '/sys/class/leds/led0/brightness'
led_1_path = '/sys/class/leds/led1/brightness'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class KROS(Component, FiniteStateMachine):
    '''
    Extends Component and Finite State Machine (FSM) as a basis of a K-Series
    Robot Operating System (KROS) or behaviour-based system (BBS), including 
    spawning the various tasks and starting up the Subsumption Architecture, 
    used for communication between Components over a common message bus.

    The MessageBus receives Event-containing messages from sensors and other
    message sources, which are passed on to the Arbitrator, whose job it is
    to determine the highest priority action to execute for that task cycle,
    by passing it on to the Controller.

    There is also a krosd linux daemon, which can be used to start, enable
    and disable kros. 

    :param mutex:   the optional logging mutex, passed on from krosd
    '''
    def __init__(self, mutex=None, level=Level.INFO):
        '''
        This initialises KROS and calls the YAML configurer.
        '''
        _name = 'kros'
        self._mutex = mutex if mutex is not None else threading.Lock() 
        self._level = level
        self._log = Logger(_name, self._level, mutex=self._mutex)
        self._print_banner()
        self._log.info('…')
        Component.__init__(self, self._log, suppressed=False, enabled=False)
        FiniteStateMachine.__init__(self, self._log, _name)
        self._system        = System(level)
        self._system.set_nice()
        # configuration...
        self._config        = None
        self._behaviour_mgr = None
        self._arbitrator    = None
        self._controller    = None
        self._gamepad       = None
        self._motors        = None
        self._ifs           = None
        self._disable_leds  = False
        self._closing       = False
        self._log.info('initialised.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def configure(self, arguments):
        '''
        Provided with a set of configuration arguments, configures KROS based on
        both KD01/KR01 standard hardware as well as optional features, the 
        latter based on devices showing up (by address) on the I²C bus. Optional
        devices are only enabled at startup time via registration of their feature
        availability.
        '''
        self._log.heading('configuration', 'configuring kros...', 
            '[1/2]' if arguments.start else '[1/1]')
        self._log.info('application log level: {}'.format(self._log.level.name))

        # read YAML configuration ..............................................
        _loader = ConfigLoader(self._level)
        _config_filename = arguments.config_file
        _filename = _config_filename if _config_filename is not None else 'config.yaml' 
        self._config = _loader.configure(_filename)

        # configuration from command line arguments ............................

        _args = self._config['kros'].get('arguments')
        # copy argument-based configuration over to _config

#       self._log.info('argument gamepad:     {}'.format(arguments.gamepad))
        _args['gamepad_enabled'] = arguments.gamepad
        self._log.info('gamepad enabled:      {}'.format(_args['gamepad_enabled']))
#       self._log.info('argument video:       {}'.format(arguments.video))
        _args['video_enabled']   = arguments.video
        self._log.info('video enabled:        {}'.format(_args['video_enabled']))
#       self._log.info('argument no-motors:   {}'.format(arguments.no_motors))
        _args['motors_enabled']  = not arguments.no_motors
        self._log.info('motors enabled:       {}'.format(_args['motors_enabled']))
#       self._log.info('argument mock:        {}'.format(arguments.mock))
        _args['mock_enabled']    = arguments.mock
        self._log.info('mock enabled:         {}'.format(_args['mock_enabled']))

        # print remaining arguments
        self._log.info('argument config-file: {}'.format(arguments.config_file))
        self._log.info('argument level:       {}'.format(arguments.level))

        # scan I2C bus .........................................................
        _i2c_scanner = I2CScanner(self._config, self._log.level)
        _i2c_scanner.print_device_list()
        self._addresses = _i2c_scanner.get_int_addresses()

        # establish basic subsumption components ...............................

        self._log.info('configure subsumption components...')
       
        self._message_bus = MessageBus(self._config, self._level)
        self._message_factory = MessageFactory(self._message_bus, self._level)

        self._controller = Controller(self._message_bus, self._level)
    
    #    _gp_controller = GamepadController(self._level)
    #    _message_bus.register_controller(_gp_controller)

        # add motor controller
        self._motor_configurer = MotorConfigurer(self._config, self._message_bus, _i2c_scanner, level=self._level)
        self._motors = self._motor_configurer.get_motors()
#       self._publisher1.set_motors(self._motors)

        self._log.info('configure pid motor controller...')
        self._pid_motor_ctrl = PIDMotorController(self._config, self._message_bus, self._motors, self._level)
    
        # create publishers ....................................................

#       self._clock  = Clock(self._config, self._message_bus, self._message_factory, level=self._level)
        self._publisher1  = EventPublisher(self._config, self._message_bus, self._message_factory, self._motors, self._system, level=self._level)
#       self._publisher2  = FloodPublisher(self._message_bus, self._message_factory)
#       self._publisher3  = GamepadPublisher(self._config, self._message_bus, self._message_factory)
    
        # create subscribers ...................................................
        self._motor_subscriber    = MotorSubscriber(self._config, self._message_bus, self._motors, level=self._level)
        self._bumper_subscriber   = BumperSubscriber(self._config, self._message_bus, self._motors, level=self._level)
#       self._infrared_subscriber = InfraredSubscriber(self._config, self._message_bus, self._motors, level=self._level) # reacts to IR sensors
        self._garbage_collector   = GarbageCollector(self._config, self._message_bus, level=self._level)
    
#       _subscriberX = Subscriber('x', self._config, self._message_bus, color=Fore.MAGENTA, suppressed=False, enabled=True, level=self._level)
#       _subscriberX.add_events([ Event.ROAM, Event.FULL_AHEAD ]) 

        # create behaviours ....................................................
        self._behaviour_mgr = BehaviourManager(self._config, self._message_bus, self._level) # a specialised subscriber
#       self._behaviour_mgr = None
        # create and register behaviours (listed in priority order)
        self._avoid = Avoid(self._config, self._message_bus, self._message_factory, self._motors, self._level)
        self._roam  = Roam(self._config, self._message_bus, self._message_factory, self._motors, self._level)
        self._moth  = Moth(self._config, self._message_bus, self._message_factory, self._motors, self._level)
        self._sniff = Sniff(self._config, self._message_bus, self._message_factory, self._motors, self._level)
        self._idle  = Idle(self._config, self._message_bus, self._message_factory, self._level)
    
    #   _message_bus.print_publishers()
    #   _message_bus.print_subscribers()

        self._log.info('configured.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_feature_available(self, name, value):
        '''
            Sets a feature's availability to the boolean value.
        '''
        self._log.debug(Fore.BLUE + Style.BRIGHT + '-- set feature available. name: \'{}\' value: \'{}\'.'.format(name, value))
        self.set_property('features', name, value)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def configuration(self):
        return self._config
    
    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_property(self, section, property_name):
        '''
        Return the value of the named property of the application
        configuration, provided its section and property name.
        '''
        return self._config[section].get(property_name)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_property(self, section, property_name, property_value):
        '''
        Set the value of the named property of the application
        configuration, provided its section, property name and value.
        '''
        self._log.debug(Fore.GREEN + 'set config on section \'{}\' for property key: \'{}\' to value: {}.'.format(\
                section, property_name, property_value))
        if section == 'ros':
            self._config[section].update(property_name = property_value)
        else:
            _kros = self._config['ros']
            _kros[section].update(property_name = property_value)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_pi_leds(self, enable):
        '''
        Enables or disables the Raspberry Pi's board LEDs.
        '''
        sudo_name = self.get_property('pi', 'sudo_name')
        # led_0_path:   '/sys/class/leds/led0/brightness'
        _led_0_path = self._config['pi'].get('led_0_path')
        _led_0 = Path(_led_0_path)
        # led_1_path:   '/sys/class/leds/led1/brightness'
        _led_1_path = self._config['pi'].get('led_1_path')
        _led_1 = Path(_led_1_path)
        if _led_0.is_file() and _led_0.is_file():
            if enable:
                self._log.info('re-enabling LEDs...')
                os.system('echo 1 | {} tee {}'.format(sudo_name,_led_0_path))
                os.system('echo 1 | {} tee {}'.format(sudo_name,_led_1_path))
            else:
                self._log.debug('disabling LEDs...')
                os.system('echo 0 | {} tee {}'.format(sudo_name,_led_0_path))
                os.system('echo 0 | {} tee {}'.format(sudo_name,_led_1_path))
        else:
            self._log.warning('could not change state of LEDs: does not appear to be a Raspberry Pi.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _callback_shutdown(self):
        _enable_self_shutdown = self._config['ros'].get('enable_self_shutdown')
        if _enable_self_shutdown:
            self._log.critical('callback: shutting down os...')
            self.close()
            sys.exit(0)
        else:
            self._log.critical('self-shutdown disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _print_banner(self):
        '''
        Display banner on console.
        '''
        self._log.info(' ')
        self._log.info(' ')
        self._log.info('      ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ')
        self._log.info('      ┃                                                       ┃ ')
        self._log.info('      ┃    █▒▒   █▒▒  █▒▒▒▒▒▒▒    █▒▒▒▒▒▒    █▒▒▒▒▒▒   █▒▒    ┃ ')
        self._log.info('      ┃    █▒▒  █▒▒   █▒▒   █▒▒  █▒▒   █▒▒  █▒▒        █▒▒    ┃ ')
        self._log.info('      ┃    █▒▒▒▒▒▒    █▒▒▒▒▒▒    █▒▒   █▒▒   █▒▒▒▒▒▒   █▒▒    ┃ ')
        self._log.info('      ┃    █▒▒  █▒▒   █▒▒  █▒▒   █▒▒   █▒▒        █▒▒         ┃ ')
        self._log.info('      ┃    █▒▒   █▒▒  █▒▒   █▒▒   █▒▒▒▒▒▒    █▒▒▒▒▒▒   █▒▒    ┃ ')
        self._log.info('      ┃                                                       ┃ ')
        self._log.info('      ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ')
        self._log.info(' ')
        self._log.info(' ')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def start(self):
        '''
        This first disables the Pi's status LEDs, establishes the message bus,
        arbitrator, controller, enables the set of features, then starts the main
        OS loop.
        '''
        self._log.heading('starting', 'starting k-series robot operating system (kros)...', '[2/2]' )
        super().start()
        self._disable_leds = self._config['pi'].get('disable_leds')
        if self._disable_leds:
            # disable Pi LEDs since they may be distracting
            self._set_pi_leds(False)

        # begin main loop ..............................

        self._log.notice('Press Ctrl-C to exit.')
        self._log.info('begin main os loop.\r')

        if self._motors:
            self._motors.enable()

        # now in main application loop until quit or Ctrl-C...
        self._log.info(Fore.YELLOW + 'enabling message bus...')
        self._message_bus.enable()

        if self._message_bus and self._message_bus.enabled:
            self._message_bus.close()
        self._log.info('closed.')

        # enable arbitrator tasks (normal functioning of robot)
#       self._arbitrator.start()

        self._log.info('started.')

        # end main ...................................

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        '''
        This sets the KROS back to normal following a session.
        '''
        if self._closing:
            self._log.info('already closing.')
            return
        else:
            self._closing = True
            self._log.info(Style.BRIGHT + 'closing...')
            Component.disable(self)
            if self._behaviour_mgr:
                self._behaviour_mgr.close()
            if self._gamepad:
                self._gamepad.close() 
            if self._motors:
                self._motors.close()
            if self._ifs:
                self._ifs.close() 
            if self._disable_leds:
                # restore normal function of LEDs
                self._set_pi_leds(True)
            Component.close(self)
            self._closing = False
            self._log.info('closed.')
            sys.exit(0)

# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def parse_args():
    '''
    Parses the command line arguments and return the resulting args object.
    Help is available via '--help', '-h', or calling the script with no arguments.
    '''
    _log = Logger('parse-args', Level.INFO)
    _log.debug('parsing...')
    formatter = lambda prog: argparse.HelpFormatter(prog,max_help_position=60)
    parser = argparse.ArgumentParser(formatter_class=formatter,
            description='Provides command line control of the KROS application.', \
            epilog='This script may be executed by krosd (kros daemon) or run directly from the command line.')
    parser.add_argument('--configure',   '-c', action='store_true', help='run configuration (included by -s)')
    parser.add_argument('--start',       '-s', action='store_true', help='start kros')
    parser.add_argument('--no-motors',   '-n', action='store_true', help='disable motors (uses mock)')
    parser.add_argument('--gamepad',     '-g', action='store_true', help='enable bluetooth gamepad control')
    parser.add_argument('--video',       '-v', action='store_true', help='enable video if installed')
    parser.add_argument('--mock',        '-m', action='store_true', help='permit mocked libraries (when not on a Pi)')
    parser.add_argument('--config-file', '-f', help='use alternative configuration file')
    parser.add_argument('--level',       '-l', help='specify logging level \'DEBUG\'|\'INFO\'|\'WARN\'|\'ERROR\' (default: \'INFO\')')
    try:
        args = parser.parse_args()
        _log.debug('parsed arguments: {}\n'.format(args))
        if not args.configure and not args.start:
            print(Fore.CYAN)
            parser.print_help()
            print(Style.RESET_ALL)
            return None
        else:
            return args
    except NotImplementedError as nie:
        _log.error('unrecognised log level \'{}\': {}'.format(args.level, nie))
        _log.error('exit on error.')
        sys.exit(1)
    except Exception as e:
        _log.error('error parsing command line arguments: {}\n{}'.format(e, traceback.format_exc()))
        _log.error('exit on error.')
        sys.exit(1)

# execution handler ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def signal_handler(signal, frame):
    global _kros
    print('\nsignal handler    :' + Fore.MAGENTA + Style.BRIGHT + ' INFO  : Ctrl-C caught: exiting...' + Style.RESET_ALL)
    if _kros:
        _kros.close()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
#   sys.stderr = DevNull()
    sys.exit(0)

# main ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_kros = None

def main(argv):
    global _kros

    _log = Logger("main", Level.INFO)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        _args = parse_args()
        if _args == None:
            print('')
            _log.info('arguments: no action.')
        else:
            _level = Level.from_string(_args.level) if _args.level != None else Level.INFO
            _log.level = _level
            _log.debug('arguments: {}'.format(_args))
            _kros = KROS(level=_level)
            if _args.configure or _args.start:
                _kros.configure(_args)
                if not _args.start:
                    _log.info('configure only: ' + Fore.YELLOW + 'specify the -s argument to start kros.')
            if _args.start:
                _kros.start()
            # kros is now running...
    except KeyboardInterrupt:
        print(Style.BRIGHT + 'caught Ctrl-C; exiting...')
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting kros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
    finally:
        _log.info('exit.')
        if _kros:
            _log.info(Style.DIM + 'finally closing kros...')
            _kros.close()

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

# prevent Python script from exiting abruptly
#signal.pause()

#EOF
