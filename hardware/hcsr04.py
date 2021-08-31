#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021 by Murray Altheim. 
# Released without license, this code is in the public domain.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2021-08-20
#
# This version modified from the original for use as a Python 3 class,
# with a friendlier try-except on importing RPi.GPIO.
#
#======================================================================
#
# Python Module to handle an HC-SR04 Ultrasonic Module on a single Pin
# Aimed at use on Picon Zero
#
# Created by Gareth Davies, Mar 2016
# Copyright 4tronix
#
# This code is in the public domain and may be freely copied and used
# No warranty is provided or implied
#
#======================================================================

import sys, threading, time, os, subprocess
try:
    import RPi.GPIO as GPIO
except Exception:
    print('This script requires the RPi.GPIO module.\nInstall with: sudo pip3 install RPi.GPIO')
    sys.exit(1)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class HCSR04(object):

    SPEED_OF_SOUND_CM_S = 34326 # at sea level

    def __init__(self, sonar=38):
        super().__init__()
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        # define Sonar Pin (uses same pin for both Ping and Echo)
        self._sonar = sonar
        # ready

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def getDistance(self):
        '''
        Returns the distance in cm to the nearest reflecting object. 0 == no object
        '''
        GPIO.setup(self._sonar, GPIO.OUT)
        # send 10us pulse to trigger
        GPIO.output(self._sonar, True)
        time.sleep(0.00001)
        GPIO.output(self._sonar, False)
        _start = time.time()
        _count = time.time()
        GPIO.setup(self._sonar,GPIO.IN)
        while GPIO.input(self._sonar) == 0 and time.time() - _count < 0.1:
            _start = time.time()
        _count=time.time()
        _stop = _count
        while GPIO.input(self._sonar) == 1 and time.time() - _count < 0.1:
            _stop = time.time()
        # calculate pulse length
        _elapsed = _stop - _start
        # distance pulse travelled in that time is time
        # multiplied by the speed of sound (cm/s)
        _distance = _elapsed * HCSR04.SPEED_OF_SOUND_CM_S
        # That was the distance there and back so halve the value
        _distance = _distance / 2
        return _distance
    
    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def cleanup(self):
        GPIO.cleanup()

#EOF
