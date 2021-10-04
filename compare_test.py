#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import sys, math
from colorama import init, Fore, Style
init(autoreset=True)

from core.ranger import Ranger

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Comparator(object):

    def __init__(self):
        self._percent_tolerance = 15.0
        self._ranger = Ranger(0.0, 255.0, 0.0, 1.0)
        _minimum_output = 0.0
        _maximum_output = 255
        self._clip = lambda n: _minimum_output if n <= _minimum_output else _maximum_output if n >= _maximum_output else n
        self._abs_tol = ( self._percent_tolerance / 100.0 ) * 255.0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _compare(self, port, stbd):
        '''
        Calculate:  ( STBD - PORT ) will be less than zero if PORT is larger
        Returns
          * -1    if port > stbd or
          *  0    if the two values are within a tolerance of each other, or
          *  1    if port < stbd
        '''
#       print(Fore.RED + 'port: {}; '.format(port) + Fore.GREEN + 'stbd: {}'.format(stbd))
        if math.isclose(port, stbd, abs_tol=self._abs_tol): # 8% on a 0-255 scale
            print(Fore.CYAN + Style.DIM + 'is close: {} with {}'.format(port, stbd))
            return 0
        else:
            print(Fore.CYAN + Style.DIM + '> compare ' + Fore.RED + 'PORT: {} '.format(port) + Fore.CYAN + 'with ' 
                    + Fore.GREEN + 'STBD: {}  \t'.format(stbd) + Fore.WHITE + 'stbd - port < 0? {}'.format((port - stbd) < 0.0))
            return -1 if ( (stbd - port) < 0 ) else 1

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _ratio(self, port, stbd):
        ''' With:
              PORT     STBD      PORT_ratio    STBD_ratio
               255        0         1.0           0.0
                 0        0         0.0           0.0
                 0      255         0.0           1.0
               255      255         0.0           0.0
               127      127         0.0           0.0
    
        So, get ratio between them first.
        '''
#       if (port - stbd) < 0.0: # 
        _port = self._clip(port)
        _stbd = self._clip(stbd)
        _comp = self._compare(_port, _stbd)
        if _comp == 0:
            return ( 0.0, 0.0 )
        elif _comp < 0: # then bias to PORT
            _port = abs(self._ranger.convert(_stbd - _port))
            _stbd = 0.0
        elif _comp > 0: # then bias to STBD
            _port = 0.0
            _stbd = abs(self._ranger.convert(_port - _stbd))
        return ( _port, _stbd )

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def process(self, port, stbd):
        _comparison = self._compare(port,stbd)
        if _comparison < 0:
            _value = Fore.RED + 'PORT'
        elif _comparison > 0:
            _value = Fore.GREEN + 'STBD'
        else:
            _value = Fore.YELLOW + 'SAME'
    
        _ratio      = self._ratio(port,stbd)
        return ( _value, *_ratio )

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main(argv):

    _c = Comparator()
    #                  port   stbd
    print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(  260,    50 )))
    print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(  255,    50 )))
    print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(  240,   230 )))
#   print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(  240,   230 )))
    print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(    5,    50 )))
#   print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(    5,     5 )))
    print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(    0,     0 )))
#   print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(   50,    50 )))
    print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(    0,     5 )))
    print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(    0,   105 )))
    print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(    0,   255 )))
    print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(    0,   260 )))

    for _port in range(0, 256, 5):
        print(Fore.CYAN + 'compare: {};\tratio: {:5.2f} | {:5.2f}'.format(*_c.process(_port, 0)))


# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
if __name__== "__main__":
    main(sys.argv[1:])

