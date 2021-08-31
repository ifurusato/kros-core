#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Python library for 4tronix Picon Zero
# Note that all I2C accesses are wrapped in try clauses with repeats
# see: https://4tronix.co.uk/blog/?p=1224
#

import sys, time
try:
    import smbus
except Exception:
    print('This script requires the smbus module.\nInstall with: sudo apt-get install python-smbus python3-smbus python-dev python3-dev')
    sys.exit(1)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class PiconZero(object):

    # Definitions of Commands to Picon Zero
    MOTORA    = 0
    OUTCFG0   = 2
    OUTPUT0   = 8
    INCFG0    = 14
    SETBRIGHT = 18
    UPDATENOW = 19
    RESET     = 20

    '''
    Constructor for a PiconZero.

    :param pz_address:  the I2C address of the Picon Zero (default 0x22)
    '''
    def __init__(self, pz_address = 0x22):
        super().__init__()
        self._pz_address = pz_address # I2C address of Picon Zero
        _bus_number      = 1 # for revision 1 Raspberry Pi, change to bus = smbus.SMBus(0)
        self._bus        = smbus.SMBus(_bus_number) 
        self._debug      = False
        self._retries    = 10 # max number of retries for I2C calls
        # ready.

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def getRevision(self):
        '''
        get Version and Revision info.
        '''
        for i in range(self._retries):
            try:
                rval = self._bus.read_word_data (self._pz_address, 0)
                return [rval/256, rval%256]
            except:
                if (self._debug):
                    print('Error in getRevision(), retrying')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def setMotor(self, motor, value):
        '''
        motor must be in range 0..1
        value must be in range -128 - +127
        values of -127, -128, +127 are treated as always ON,, no PWM
        '''
        if (motor>=0 and motor<=1 and value>=-128 and value<128):
            for i in range(self._retries):
                try:
                    self._bus.write_byte_data (self._pz_address, motor, value)
                    break
                except:
                    if (self._debug):
                        print('Error in setMotor(), retrying')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def forward(self, speed):
        setMotor (0, speed)
        setMotor (1, speed)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def reverse(self, speed):
        setMotor (0, -speed)
        setMotor (1, -speed)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def spinLeft(self, speed):
        setMotor (0, -speed)
        setMotor (1, speed)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def spinRight(self, speed):
        setMotor (0, speed)
        setMotor (1, -speed)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def stop(self):
        setMotor (0, 0)
        setMotor (1, 0)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def readInput(self, channel):
        '''
        Read data for selected input channel (analog or digital)
        Channel is in range 0 to 3
        '''
        if (channel>=0 and channel <=3):
            for i in range(self._retries):
                try:
                    return self._bus.read_word_data (self._pz_address, channel + 1)
                except:
                    if (self._debug):
                        print('Error in readChannel(), retrying')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def setOutputConfig(self, output, value):
        '''
        Set configuration of selected output
        0: On/Off, 1: PWM, 2: Servo, 3: WS2812B
        '''
        if (output>=0 and output<=5 and value>=0 and value<=3):
            for i in range(self._retries):
                try:
                    self._bus.write_byte_data (self._pz_address, PiconZero.OUTCFG0 + output, value)
                    break
                except:
                    if (self._debug):
                        print('Error in setOutputConfig(), retrying')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def setInputConfig(self, channel, value, pullup = False):
        '''
        Set configuration of selected input channel
        0: Digital, 1: Analog
        '''
        if (channel>=0 and channel <=3 and value>=0 and value<=3):
            if (value==0 and pullup==True):
                value = 128
            for i in range(self._retries):
                try:
                    self._bus.write_byte_data (self._pz_address, PiconZero.INCFG0 + channel, value)
                    break
                except:
                    if (self._debug):
                        print('Error in setInputConfig(), retrying')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def setOutput(self, channel, value):
        '''
        Set output data for selected output channel
        Mode  Name    Type    Values
        0     On/Off  Byte    0 is OFF, 1 is ON
        1     PWM     Byte    0 to 100 percentage of ON time
        2     Servo   Byte    -100 to + 100 Position in degrees
        3     WS2812B 4 Bytes 0:Pixel ID, 1:Red, 2:Green, 3:Blue
        '''
        if (channel>=0 and channel<=5):
            for i in range(self._retries):
                try:
                    self._bus.write_byte_data (self._pz_address, PiconZero.OUTPUT0 + channel, value)
                    break
                except:
                    if (self._debug):
                        print('Error in setOutput(), retrying')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def setPixel(self, Pixel, Red, Green, Blue, Update=True):
        '''
        Set the colour of an individual pixel (always output 5)
        '''
        pixelData = [Pixel, Red, Green, Blue]
        for i in range(self._retries):
            try:
                self._bus.write_i2c_block_data (self._pz_address, Update, pixelData)
                break
            except:
                if (self._debug):
                    print('Error in setPixel(), retrying')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def setAllPixels(self, Red, Green, Blue, Update=True):
        '''
        Set the colour of all pixels.
        '''
        pixelData = [100, Red, Green, Blue]
        for i in range(self._retries):
            try:
                self._bus.write_i2c_block_data (self._pz_address, Update, pixelData)
                break
            except:
                if (self._debug):
                    print('Error in setAllPixels(), retrying')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def updatePixels(self):
        '''
        '''
        for i in range(self._retries):
            try:
                self._bus.write_byte_data (self._pz_address, PiconZero.UPDATENOW, 0)
                break
            except:
                if (self._debug):
                    print('Error in updatePixels(), retrying')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def setBrightness(self, brightness):
        '''
        Set the overall brightness of pixel array
        '''
        for i in range(self._retries):
            try:
                self._bus.write_byte_data (self._pz_address, PiconZero.SETBRIGHT, brightness)
                break
            except:
                if (self._debug):
                    print('Error in setBrightness(), retrying')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def init(self, debug=False):
        '''
        Initialise the Board (same as cleanup)
        '''
        self._debug = debug
        for i in range(self._retries):
            try:
                self._bus.write_byte_data (self._pz_address, PiconZero.RESET, 0)
                break
            except:
                if (self._debug):
                    print('Error in init(), retrying')
        time.sleep(0.01)  #1ms delay to allow time to complete
        if (self._debug):
            print('Debug is {}'.format(self._debug))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def cleanup(self):
        '''
        Cleanup the Board (same as init)
        '''
        for i in range(self._retries):
            try:
                self._bus.write_byte_data (self._pz_address, PiconZero.RESET, 0)
                break
            except:
                if (self._debug):
                    print('Error in cleanup(), retrying')
        time.sleep(0.001) # 1ms delay to allow time to complete

#EOF
