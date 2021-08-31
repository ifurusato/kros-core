#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Picon Zero Servo Test, based on the 4Tronix original.
# Demo for Pan and Tilt and Gripper arm.
#

import time
import sys, tty, termios
from colorama import init, Fore, Style
init()

from hardware.picon_zero import PiconZero

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
# reading single character by forcing stdin to raw mode

def readchar():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    if ch == '0x03':
        raise KeyboardInterrupt
    return ch

def readkey(getchar_fn=None):
    getchar = getchar_fn or readchar
    c1 = getchar()
    if ord(c1) != 0x1b:
        return c1
    c2 = getchar()
    if ord(c2) != 0x5b:
        return c1
    c3 = getchar()
    return chr(0x10 + ord(c3) - 65)  # 16=Up, 17=Down, 18=Right, 19=Left arrows

# End of single character reading
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def print_intro():
    print(Fore.CYAN + '''

  Tests pan-tilt of servos 0 and 1 by using the arrow keys to control.
  Press <space> key to center.
  Press <?> key for help.
  Press Ctrl-C to end.

''' + Style.RESET_ALL)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def print_help():
    print(Fore.CYAN + '''
  ┈┈┈┈┈┈┈ Servo Test Help  ┈┈┈┈┈┈┈┈┈
  <w> or UP        :  tilt up
  <z> or DOWN      :  tilt down
  <s> or RIGHT     :  pan right
  <a> or LEFT      :  pan left
  <g>              :  open
  <h>              :  close
  <space>          :  center
  <q> or Ctrl-C    :  quit
  ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
''' + Style.RESET_ALL)

# main loop ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

print_intro()

try:

    # define pins associated with servos
    _pan_servo_pin  = 0
    _tilt_servo_pin = 1
    _grip_servo_pin = 2

    pz = PiconZero()
    pz.init()

    # set output mode to Servo
    pz.setOutputConfig(_pan_servo_pin,  2)
    pz.setOutputConfig(_tilt_servo_pin, 2)
    pz.setOutputConfig(_grip_servo_pin, 2)

    # center all servos
    _pan_value  = 90
    _tilt_value = 90
    _grip_value = 90
    pz.setOutput(_pan_servo_pin, _pan_value)
    pz.setOutput(_tilt_servo_pin, _tilt_value)
    pz.setOutput(_grip_servo_pin, _grip_value)

    while True:

        keyp = readkey()
        if keyp == 'w' or ord(keyp) == 16:
            _pan_value = max (0, _pan_value - 5)
            print(Fore.CYAN + '↑ Up:   \t' + Fore.YELLOW + '{0:>3}'.format(_pan_value) + Style.RESET_ALL)
        elif keyp == 'z' or ord(keyp) == 17:
            _pan_value = min (180, _pan_value + 5)
            print(Fore.CYAN + '↓ Down: \t' + Fore.YELLOW + '{0:>3}'.format(_pan_value) + Style.RESET_ALL)
        elif keyp == 's' or ord(keyp) == 18:
            _tilt_value = max (0, _tilt_value - 5)
            print(Fore.CYAN + '→ Right:\t' + Fore.YELLOW + '{0:>3}'.format(_tilt_value) + Style.RESET_ALL)
        elif keyp == 'a' or ord(keyp) == 19:
            _tilt_value = min (180, _tilt_value + 5)
            print(Fore.CYAN + '← Left: \t' + Fore.YELLOW + '{0:>3}'.format(_tilt_value) + Style.RESET_ALL)
        elif keyp == 'g':
            _grip_value = max (0, _grip_value - 5)
            print(Fore.CYAN + '- Open: \t' + Fore.YELLOW + '{0:>3}'.format(_grip_value) + Style.RESET_ALL)
        elif keyp == 'h':
            _grip_value = min (180, _grip_value + 5)
            print(Fore.CYAN + '- Close:\t' + Fore.YELLOW + '{0:>3}'.format(_grip_value) + Style.RESET_ALL)
        elif keyp == ' ':
            _pan_value = _tilt_value = _grip_value = 90
            print(Fore.CYAN + '- Center')
        elif keyp == '/' or keyp == '?':
            print_help()
        elif keyp == 'q':
            raise KeyboardInterrupt()
        elif ord(keyp) == 3:
            break

        pz.setOutput (_pan_servo_pin, _pan_value)
        pz.setOutput (_tilt_servo_pin, _tilt_value)
        pz.setOutput (_grip_servo_pin, _grip_value)

except KeyboardInterrupt:
    print('Ctrl-C caught.')
finally:
    pz.cleanup()

print('complete.')

#EOF
