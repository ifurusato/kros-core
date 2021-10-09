#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import pytest
import sys, time, traceback
from datetime import datetime as dt
from colorama import init, Fore, Style
init(autoreset=True)

from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from core.rate import Rate
from core.ranger import Ranger
from behave.swerve import Swerve
from core.message_factory import MessageFactory
from mock.message_bus import MockMessageBus as MessageBus
from mock.external_clock import MockExternalClock as ExternalClock

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_swerve():

    _log = Logger('test', Level.INFO)
    _start_time = dt.now()

    _swerve = None
    _message_bus = None

    try:

        _ranger = Ranger(0.0, 255.0, 0.0, 1.0)
        _minimum_output = 0.0
        _maximum_output = 255
        _clip = lambda n: _minimum_output if n <= _minimum_output else _maximum_output if n >= _maximum_output else n
        _percent_tolerance = 25.0
        _abs_tol = ( _percent_tolerance / 100.0 ) * 255.0
        _multiplier = 1.0
        
        # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

        _level = Level.INFO
        
        # read YAML configuration
        _config = ConfigLoader(Level.INFO).configure()
        _log.info('creating message bus...')
#       _message_bus = MockMessageBus()
        _message_bus = MessageBus(_config, _level)
        _log.info('creating message factory...')
        _message_factory = MessageFactory(_message_bus, _level)
        _motor_ctrl = None
        _external_clock = ExternalClock(_config)
        
        print('creating Swerve...')
        _swerve = Swerve(_config, _message_bus, _message_factory, _motor_ctrl, _external_clock, suppressed=True, enabled=True, level=Level.INFO)
        _swerve._reverse = False # ignore config
        print('created Swerve.')
        
        _limit = 256
        _port  = 256
        _stbd  = 0
        _step  = 8
        while _stbd < _limit:
            if _port < ( _limit / 2 ):
                _stbd = _stbd + _step
            if _port > 0:
                _port = _port - _step
            _result_port, _result_stbd = _swerve._compare(_port, _stbd)
            if _result_port == 0.0 and _result_stbd == 0:
                print(Fore.CYAN + 'compare:\t' + Fore.RED + 'PORT: {:5.2f}\t'.format(_port) 
                        + Fore.CYAN + 'with ' + Fore.GREEN + 'STBD: {:5.2f}  \t'.format(_stbd)
                        + Fore.BLUE + 'result:\t' + Fore.RED + Style.DIM + 'PORT: {:5.2f}\t'.format(_result_port)
                        + Fore.BLUE + Style.NORMAL + 'with ' + Fore.GREEN + Style.DIM + 'STBD: {:5.2f}  \t'.format(_result_stbd) )
            elif _result_port == 0.0:
                print(Fore.CYAN + 'compare:\t' + Fore.RED + 'PORT: {:5.2f}\t'.format(_port) 
                        + Fore.CYAN + 'with ' + Fore.GREEN + 'STBD: {:5.2f}  \t'.format(_stbd)
                        + Fore.CYAN + 'result:\t' + Fore.RED + Style.DIM + 'PORT: {:5.2f}\t'.format(_result_port) 
                        + Fore.CYAN + Style.NORMAL + 'with ' + Fore.GREEN + 'STBD: {:5.2f}  \t'.format(_result_stbd) )
            else:
                print(Fore.CYAN + 'compare:\t' + Fore.RED + 'PORT: {:5.2f}\t'.format(_port) 
                        + Fore.CYAN + 'with ' + Fore.GREEN + 'STBD: {:5.2f}  \t'.format(_stbd)
                        + Fore.CYAN + 'result:\t' + Fore.RED + 'PORT: {:5.2f}\t'.format(_result_port) 
                        + Fore.CYAN + 'with ' + Fore.GREEN + Style.DIM + 'STBD: {:5.2f}  \t'.format(_result_stbd) )

        _external_clock.enable()
        _swerve.enable()

        while True:
            print(Fore.CYAN + 'tick:')
            time.sleep(2.0)

        _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
        _log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
    except Exception as e:
        _log.error('{} encountered, exiting: {}'.format(type(e), e))
        traceback.print_exc(file=sys.stdout)
    finally:
        if _swerve:
            _log.info('closing swerve...')
            _swerve.close()
        if _message_bus:
            _log.info('closing message bus...')
            _message_bus.close()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():
    test_swerve()

if __name__== "__main__":
    main()

#EOF
