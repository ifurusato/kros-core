#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import sys, math
from colorama import init, Fore, Style
init(autoreset=True)

from core.ranger import Ranger


# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

_ranger = Ranger(0.0, 255.0, 0.0, 1.0)
_minimum_output = 0.0
_maximum_output = 255
_clip = lambda n: _minimum_output if n <= _minimum_output else _maximum_output if n >= _maximum_output else n
_percent_tolerance = 15.0
_abs_tol = ( _percent_tolerance / 100.0 ) * 255.0


# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def _compare(port, stbd):
    '''
    Returns -1 if port > stbd or; 0 if the two values are within a tolerance of each other, or; 1 if port < stbd
    '''
    if math.isclose(port, stbd, abs_tol=_abs_tol):
        return 0
    else:
        return -1 if ( (stbd - port) < 0 ) else 1

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def _ratio(port, stbd):
    ''' With:
          PORT     STBD      PORT_ratio    STBD_ratio
           255        0         1.0           0.0
             0        0         0.0           0.0
             0      255         0.0           1.0
           255      255         0.0           0.0
           127      127         0.0           0.0

    So, get ratio between them first.
    '''
    _port = _clip(port)
    _stbd = _clip(stbd)
    print(Fore.CYAN + 'compare ' + Fore.RED + 'PORT: {:5.2f}\t'.format(_port) + Fore.CYAN + 'with ' + Fore.GREEN + 'STBD: {:5.2f}  \t'.format(_stbd) )
    return
    _comp = _compare(_port, _stbd)
    if _comp == 0:
        _port = 0.0
        _stbd = 0.0
    elif _comp < 0: # then bias to PORT
        _port = abs(_ranger.convert(_stbd - _port))
        _stbd = 0.0
    elif _comp > 0: # then bias to STBD
        _port = 0.0
        _stbd = abs(_ranger.convert(_port - _stbd))
    print(Fore.CYAN + 'compare ' + Fore.RED + 'PORT: {:5.2f} '.format(_port) + Fore.CYAN + 'with ' 
            + Fore.GREEN + 'STBD: {:5.2f}  \t'.format(_stbd) + Fore.WHITE + 'compared: {}'.format(_comp))
    return ( _port, _stbd )


_limit = 256
_port  = 256
_stbd  = 0
_step  = 8
while _stbd < _limit:
    if _port < ( _limit / 2 ):
        _stbd = _stbd + _step
    if _port > 0:
        _port = _port - _step
    _ratio(_port, _stbd)

# EOF
