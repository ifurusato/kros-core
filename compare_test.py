#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import sys, math
from colorama import init, Fore, Style
init(autoreset=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Comparator(object):

    def __init__(self):
        self._percent_tolerance = 15.0
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
        print(Fore.RED + 'port: {}; '.format(port) + Fore.GREEN + 'stbd: {}'.format(stbd))
        if math.isclose(port, stbd, abs_tol=self._abs_tol): # 8% on a 0-255 scale
            print(Fore.CYAN + Style.DIM + 'is close: {} with {}'.format(port, stbd))
            return 0
        else:
            print(Fore.CYAN + Style.BRIGHT + '> compare {} with {}; stbd - port < 0? {}'.format(port, stbd, ((port - stbd) < 0.0)))
            return -1 if ( (stbd - port) < 0 ) else 1

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _ratio(self, port, stbd):
        return ( ( stbd - port ), ( port - stbd ) )

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def process(self, port, stbd):
        _comparison = self._compare(port,stbd)
        _ratio      = self._ratio(port,stbd)
        return ( _comparison, *_ratio )

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main(argv):

    _c = Comparator()
    #                  port   stbd
    print(Fore.CYAN + 'compare: {:d};\tratio: {} | {}'.format(*_c.process(  260,    50 )))
    print(Fore.CYAN + 'compare: {:d};\tratio: {} | {}'.format(*_c.process(  255,    50 )))
    print(Fore.CYAN + 'compare: {:d};\tratio: {} | {}'.format(*_c.process(  240,   200 )))
    print(Fore.CYAN + 'compare: {:d};\tratio: {} | {}'.format(*_c.process(  240,   230 )))
    print(Fore.CYAN + 'compare: {:d};\tratio: {} | {}'.format(*_c.process(    5,    50 )))
    print(Fore.CYAN + 'compare: {:d};\tratio: {} | {}'.format(*_c.process(    5,     5 )))
    print(Fore.CYAN + 'compare: {:d};\tratio: {} | {}'.format(*_c.process(    0,     0 )))
    print(Fore.CYAN + 'compare: {:d};\tratio: {} | {}'.format(*_c.process(   50,    50 )))
    print(Fore.CYAN + 'compare: {:d};\tratio: {} | {}'.format(*_c.process(    0,     5 )))
    print(Fore.CYAN + 'compare: {:d};\tratio: {} | {}'.format(*_c.process(    0,   105 )))
    print(Fore.CYAN + 'compare: {:d};\tratio: {} | {}'.format(*_c.process(    0,   255 )))
    print(Fore.CYAN + 'compare: {:d};\tratio: {} | {}'.format(*_c.process(    0,   260 )))


# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
if __name__== "__main__":
    main(sys.argv[1:])

