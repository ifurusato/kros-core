#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Basic test of HC-SR04 ultrasonic sensor on Picon Zero.
#

import sys, time, traceback
from colorama import init, Fore, Style
init(autoreset=True)

from hardware.hcsr04 import HCSR04

# main ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main(argv):

    _hcsr04 = HCSR04()

    try:

        while True:
            distance = int(_hcsr04.getDistance())
            print(Fore.CYAN + 'Distance:\t' + Fore.YELLOW + '{0:>3}cm'.format(distance))
            time.sleep(0.5)

    except KeyboardInterrupt:
        print(Style.BRIGHT + 'caught Ctrl-C; exiting...')
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting kros: {}'.format(traceback.format_exc()))
        sys.exit(1)
    finally:
        _hcsr04.cleanup()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
