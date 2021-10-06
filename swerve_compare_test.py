#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import sys, math
from colorama import init, Fore, Style
init(autoreset=True)

from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from core.ranger import Ranger
from behave.swerve import Swerve
from core.message_factory import MessageFactory
from mock.message_bus import MockMessageBus

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

_ranger = Ranger(0.0, 255.0, 0.0, 1.0)
_minimum_output = 0.0
_maximum_output = 255
_clip = lambda n: _minimum_output if n <= _minimum_output else _maximum_output if n >= _maximum_output else n
_percent_tolerance = 25.0
_abs_tol = ( _percent_tolerance / 100.0 ) * 255.0
_multiplier = 1.0

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def x_compare(port, stbd):

    _port = _clip(port)
    _stbd = _clip(stbd)
#   print(Fore.CYAN + 'compare ' + Fore.RED + 'PORT: {:5.2f}\t'.format(_port) + Fore.CYAN + 'with ' + Fore.GREEN + 'STBD: {:5.2f}  \t'.format(_stbd) )

    if math.isclose(_port, _stbd, abs_tol=_abs_tol):
        _port = 0.0
        _stbd = 0.0
#       print(Fore.CYAN + 'equal: ' + Fore.RED + 'PORT: {:5.2f} '.format(_port) + Fore.CYAN + 'with ' + Fore.GREEN + 'STBD: {:5.2f}  \t'.format(_stbd))
    else:
        _comp = -1 if ( (stbd - port) < 0 ) else 1
        if _comp < 0: # then bias to PORT
            _port = abs(_ranger.convert(_stbd - _port))
            _stbd = 0.0
        elif _comp > 0: # then bias to STBD
            _port = 0.0
            _stbd = abs(_ranger.convert(_port - _stbd))
#       print(Fore.CYAN + 'compare ' + Fore.RED + 'PORT: {:5.2f}\t'.format(_port) + Fore.CYAN + 'with ' + Fore.GREEN + 'STBD: {:5.2f}  \t'.format(_stbd)
#               + Fore.WHITE + 'compared: {}'.format(_comp))
    _port *= _multiplier
    _stbd *= _multiplier
    return ( _port, _stbd )

# ...................

_config = ConfigLoader(Level.INFO).configure()
_message_bus = MockMessageBus()
_message_factory = None
_message_factory = MessageFactory(_message_bus, Level.INFO)
_motor_ctrl = None
_external_clock = None

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

# EOF
