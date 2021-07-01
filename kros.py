#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2020-03-12
#
# The NZPRG K-Series Robot Operating System (KROS), including its command line
# interface (CLI).
#
#        1         2         3         4         5         6         7         8         9         C
#234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890

# ..............................................................................
import os, sys, signal, time, threading, traceback
import argparse, psutil
from pathlib import Path
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.fsm import FiniteStateMachine
from core.config_loader import ConfigLoader
from core.i2c_scanner import I2CScanner
from core.controller import Controller
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.publisher import Publisher
from core.clock import Clock
from core.subscriber import Subscriber, GarbageCollector
from core.behaviour_manager import BehaviourManager
from core.event import Event

from mock.motor_configurer import MotorConfigurer
from mock.event_publisher import EventPublisher
from mock.motor_subscriber import MotorSubscriber
#from mock.gamepad_publisher import GamepadPublisher
#from mock.gamepad_controller import GamepadController
from behave.roam import Roam
from behave.moth import Moth
from behave.sniff import Sniff
from behave.idle import Idle


#from core.logger import Level, Logger
##from lib.devnull import DevNull
#from core.config_loader import ConfigLoader
#from core.rate import Rate
#from core.event import Event
#from core.message import Message
#from core.message import Message
#from core.message_bus import MessageBus
#from core.message_factory import MessageFactory
#from core.clock import Clock
#from core.arbitrator import Arbitrator
#from core.controller import Controller

# standard features:
#from lib.motors import Motors
#from lib.ifs import IntegratedFrontSensor
#from lib.temperature import Temperature

led_0_path = '/sys/class/leds/led0/brightness'
led_1_path = '/sys/class/leds/led1/brightness'

# ==============================================================================

# KROS ..........................................................................
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

    # ..........................................................................
    def __init__(self, mutex=None, level=Level.INFO):
        '''
        This initialises the KROS and calls the YAML configurer.
        '''
        _name = 'kros'
        self._level = level
        self._log = Logger(_name, self._level)
        Component.__init__(self, self._log)
        FiniteStateMachine.__init__(self, self._log, _name)
        self._mutex = mutex if mutex is not None else threading.Lock() 
        self._log.info('setting process as high priority...')
        # set KROS as high priority
        proc = psutil.Process(os.getpid())
        proc.nice(10)
        # configuration...
        self._config       = None
        self._active       = False
        self._closing      = False
        self._disable_leds = False
        self._arbitrator   = None
        self._controller   = None
        self._gamepad      = None
        self._motors       = None
        self._ifs          = None
        self._log.info('🍈 initialised.')

    # ..........................................................................
    def configure(self, arguments):
        '''
        Provided with a set of configuration arguments, configures KROS based on
        both KD01/KR01 standard hardware as well as optional features, the 
        latter based on devices showing up (by address) on the I²C bus. Optional
        devices are only enabled at startup time via registration of their feature
        availability.
        '''
        self._log.heading('configuration', 'configuring ros...', 
            '[1/2]' if arguments.start else '[1/1]')
        self._log.info('application log level: {}'.format(self._log.level.name))

        # configuration from command line arguments ............................

        # read YAML configuration
        _loader = ConfigLoader(self._level)
        filename = 'config.yaml'
        self._config = _loader.configure(filename)

        # scan I2C bus
        self._log.info('scanning I²C address bus...')
        scanner = I2CScanner(self._log.level)
        self._addresses = scanner.get_int_addresses()
        _hex_addresses = scanner.get_hex_addresses()
        self._addrDict = dict(list(map(lambda x, y:(x,y), self._addresses, _hex_addresses)))
#       for i in range(len(self._addresses)):
        for _address in self._addresses:
            _device_name = self.get_device_for_address(_address)
            self._log.info('found device at I²C address 0x{:02X}: {}'.format(_address, _device_name) + Style.RESET_ALL)
            # TODO look up address and make assumption about what the device is

        # establish basic subsumption components ...............................

        self._log.info('configure subsumption components...')
       
        self._message_bus = MessageBus(Level.INFO)
        self._message_factory = MessageFactory(self._message_bus, Level.INFO)
    
        self._controller = Controller(Level.INFO)
        self._message_bus.register_controller(self._controller)
    
    #    _gp_controller = GamepadController(Level.WARN)
    #    _message_bus.register_controller(_gp_controller)
    
        self._publisher0  = Clock(self._config, self._message_bus, self._message_factory, level=self._level)
        self._publisher1  = EventPublisher(self._config, self._message_bus, self._message_factory, level=self._level)
    #   self._publisher2  = FloodPublisher(self._message_bus, self._message_factory)
    #   self._publisher3  = GamepadPublisher(self._config, self._message_bus, self._message_factory)
    
        # add motor controller, reacts to STOP, HALT, BRAKE, INCREASE_VELOCITY and DECREASE_VELOCITY
        self._motor_configurer = MotorConfigurer(self._config, self._message_bus, enable_mock=True, level=Level.WARN)
        self._motors = self._motor_configurer.get_motors()
        self._publisher1.set_motors(self._motors)
    
        # create subscribers
        self._subscriber1 = MotorSubscriber(self._message_bus, self._motors, Fore.MAGENTA, self._level)
    
        self._subscriber2 = Subscriber('infrared', self._message_bus, Fore.GREEN, self._level)
        self._subscriber2.events = [ Event.INFRARED_PORT_SIDE, Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD, Event.INFRARED_STBD_SIDE ] # reacts to IR sensors
    
        self._subscriber3 = Subscriber('bumper', self._message_bus, Fore.YELLOW, self._level)
        self._subscriber3.events = [ Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD ] # reacts to bumpers
    
        self._garbage_collector = GarbageCollector('gc', self._message_bus, Fore.BLUE, self._level)
    
        # behaviour manager is a specialised subscriber
        self._behave_manager = BehaviourManager(self._config, self._message_bus, self._motors, Fore.BLUE, self._level)
        # create and register behaviours (these are listed in priority order)
        self._behave_manager.register_behaviour(Roam(self._config, self._message_bus, self._motors, self._level))
        self._behave_manager.register_behaviour(Moth(self._config, self._message_bus, self._motors, self._level))
        self._behave_manager.register_behaviour(Sniff(self._config, self._message_bus, self._motors, self._level))
        self._behave_manager.register_behaviour(Idle(self._config, self._message_bus, self._motors, self._level))
    
    #   _message_bus.print_publishers()
    #   _message_bus.print_subscribers()

        self._log.info('🍅 configured.')

    # ..........................................................................
    def _set_feature_available(self, name, value):
        '''
            Sets a feature's availability to the boolean value.
        '''
        self._log.debug(Fore.BLUE + Style.BRIGHT + '-- set feature available. name: \'{}\' value: \'{}\'.'.format(name, value))
        self.set_property('features', name, value)

    # ..........................................................................
    def get_device_for_address(self, address):
        if address == 0x0E:
            return 'RGB Potentiometer'
        elif address == 0x0F:
            return 'RGB Encoder' # default, moved to 0x16
        elif address == 0x15:
            return 'ThunderBorg'
        elif address == 0x16:
            return 'RGB Encoder'
        elif address == 0x18:
            return 'IO Expander'
        elif address == 0x48:
            return 'ADS1015'
        elif address == 0x4A:
            return 'Unknown'
        elif address == 0x74:
            return '5x5 RGB Matrix'
        elif address == 0x77:
            return '5x5 RGB Matrix (or 11x7 LED Matrix)'
        else:
            return 'Unknown'

    # ..........................................................................
    @property
    def configuration(self):
        return self._config

    # ..........................................................................
    def get_property(self, section, property_name):
        '''
        Return the value of the named property of the application
        configuration, provided its section and property name.
        '''
        return self._config[section].get(property_name)

    # ..........................................................................
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

    # ..........................................................................
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

    # ..........................................................................
    def _callback_shutdown(self):
        _enable_self_shutdown = self._config['ros'].get('enable_self_shutdown')
        if _enable_self_shutdown:
            self._log.critical('callback: shutting down os...')
            self.close()
            sys.exit(0)
        else:
            self._log.critical('self-shutdown disabled.')

    # ..........................................................................
    def _print_banner(self):
        '''
        Display banner on console.
        '''
        self._log.info('…')
        self._log.info('…    █▒    █▒   █▒▒▒▒▒▒▒     █▒▒▒▒▒▒     █▒▒▒▒▒▒    █▒▒ ')
        self._log.info('…    █▒   █▒    █▒▒   █▒▒   █▒▒   █▒▒   █▒▒         █▒▒ ')
        self._log.info('…    █▒▒▒▒▒     █▒▒▒▒▒▒     █▒▒   █▒▒    █▒▒▒▒▒▒    █▒▒ ')
        self._log.info('…    █▒   █▒    █▒▒  █▒▒    █▒▒   █▒▒         █▒▒       ')
        self._log.info('…    █▒    █▒   █▒▒   █▒▒    █▒▒▒▒▒▒     █▒▒▒▒▒▒    █▒▒ ')
        self._log.info('…')

    # ..........................................................................
    def start(self):
        '''
        This first disables the Pi's status LEDs, establishes the message bus,
        arbitrator, controller, enables the set of features, then starts the main
        OS loop.
        '''
        self._log.info('🍑 starting...')
        super().start()
        self._print_banner()

        self._disable_leds = self._config['pi'].get('disable_leds')
        if self._disable_leds:
            # disable Pi LEDs since they may be distracting
            self._set_pi_leds(False)

        # begin main loop ..............................

        self._log.notice('Press Ctrl-C to exit.')
        self._log.info('begin main os loop.\r')

        if self._motors:
            self._motors.enable()
        self._message_bus.enable()
    
        if self._message_bus:
            self._message_bus.close()
        self._log.info('closed.')

        # enable arbitrator tasks (normal functioning of robot)
#       self._arbitrator.start()

        self._log.info('🍑 started.')

        # end main ...................................

    # ..........................................................................
    def close(self):
        '''
        This sets the KROS back to normal following a session.
        '''
        if self._closing:
            # this also gets called by the arbitrator so we ignore that
            self._log.info('already closing.')
            return
        else:
            self._active = False
            self._closing = True
            self._log.info(Style.BRIGHT + 'closing...')
            if self._gamepad:
                self._gamepad.close() 
            if self._motors:
                self._motors.close()
            if self._ifs:
                self._ifs.close() 

            if self._disable_leds:
                # restore LEDs
                self._set_pi_leds(True)
         
            self._log.info('os closed.')
            sys.exit(0)

# ==============================================================================

# ..............................................................................
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
    parser.add_argument('--configure',      '-c', action='store_true', help='run configuration (included by -s)')
    parser.add_argument('--start',          '-s', action='store_true', help='start ros')
    parser.add_argument('--no-motors',      '-n', action='store_true', help='disable motors')
    parser.add_argument('--gamepad',        '-g', action='store_true', help='enable bluetooth gamepad control')
    parser.add_argument('--camera',         '-C', action='store_true', help='enable camera if installed')
    parser.add_argument('--mock',           '-m', action='store_true', help='permit mocked libraries (when not on a Pi)')
    parser.add_argument('--config-file',    '-f', help='use alternative configuration file')
    parser.add_argument('--level',          '-l', help='specify logging level \'DEBUG\'|\'INFO\'|\'WARN\'|\'ERROR\' (default: \'INFO\')')
    try:
        args = parser.parse_args()
        _log.debug('parsed arguments: {}\n'.format(args))
#       print_banner()
        if not args.configure and not args.start:
            print(Fore.CYAN)
#           print('' + Fore.CYAN)
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

# exception handler ............................................................

def signal_handler(signal, frame):
    global _kros
    print('\nsignal handler    :' + Fore.MAGENTA + Style.BRIGHT + ' INFO  : Ctrl-C caught: exiting...' + Style.RESET_ALL)
    if _kros:
        _kros.close()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
#   sys.stderr = DevNull()
#   sys.exit()
    sys.exit(0)

# main .........................................................................

_kros = None

def main(argv):
    global _kros

    _log = Logger("main", Level.INFO)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        _args = parse_args()
        if _args == None:
            print('')
            _log.info(Fore.CYAN + 'arguments: no action.')
        else:
            _level = Level.from_str(_args.level) if _args.level != None else Level.INFO
            _log.level = _level
            _log.info('arguments: {}'.format(_args))
            _kros = KROS(level=_level)
            if _args.configure or _args.start:
                _kros.configure(_args)
                if not _args.start:
                    _log.info('configure only: ' + Fore.YELLOW + 'specify the -s argument to start ros.')
            if _args.start:
                _kros.start()

    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
        if _kros:
            _kros.close()
    finally:
        _log.info('exit.')

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

# prevent Python script from exiting abruptly
#signal.pause()

#EOF
