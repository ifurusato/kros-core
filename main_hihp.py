# Handshaking Interrupt-Driven Hexadecimal Protocol (HIHP) for the TinyPICO
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-26
# modified: 2021-09-11
#
# Server for the Handshaking Interrupt-Driven Hexadecimal Protocol (HIHP).
#

from machine import Timer
from machine import Pin
from machine import SPI
#import itertools
import tinypico as TinyPICO
from dotstar import DotStar
import time, gc

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                  CONSTANTS
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# sensor orientation ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
ORIENTATION_NONE  = [ 0, 0, 0, 0 ] # none             none
ORIENTATION_PORT  = [ 0, 0, 1, 1 ] # port             port
ORIENTATION_CNTR  = [ 0, 1, 0, 2 ] # center           cntr
ORIENTATION_STBD  = [ 0, 1, 1, 3 ] # starboard        stbd
ORIENTATION_PAFT  = [ 1, 0, 0, 4 ] # port-aft         paft
ORIENTATION_MAST  = [ 1, 0, 1, 5 ] # mast             mast
ORIENTATION_SAFT  = [ 1, 1, 0, 6 ] # starboard-aft    saft
ORIENTATION_ALL   = [ 1, 1, 1, 7 ] # unused (all bits high)

# pin definitions ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
PIN_PAFT = 15 # port aft infrared
PIN_MAST = 14 # mast infrared
PIN_SAFT =  4 # starboard aft infrared
PIN_PORT = 27 # port bumper switch
PIN_CNTR = 26 # center bumper switch
PIN_STBD = 25 # starboard bumper switch

PIN_ACK  = 23 # acknowledge pin (in)
PIN_INT  = 18 # interrupt pin (out)
PIN_D0   =  5 # data 0 pin (out) was 19 or 32
PIN_D1   = 22 # data 1 pin (out)
PIN_D2   = 21 # data 2 pin (out)
PIN_D3   = 32 # data 3 pin (out)

# define constant colours on the Dotstar ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
COLOR_BLACK        = (  0,  0,  0, 10 )
COLOR_RED          = ( 64,  0,  0,  1 )
COLOR_BLUE         = (  0,  0, 64,  1 )
COLOR_GREEN        = (  0, 64,  0,  1 )
COLOR_CYAN         = (  0, 64, 64,  1 )
COLOR_YELLOW       = ( 64, 64,  0,  1 )
COLOR_MAGENTA      = ( 64,  0, 64,  1 )
COLOR_PURPLE       = (  9,  0,  7,  1 ) # not used
# colors associated with each sensor
COLORS = [ COLOR_BLACK, COLOR_RED, COLOR_BLUE, COLOR_GREEN, COLOR_CYAN, COLOR_YELLOW, COLOR_MAGENTA, COLOR_PURPLE ]
# other colors
COLOR_ACK          = (  0, 10,  7,  1 ) # acknowledged: turquoise
COLOR_NOT_ACK      = ( 24, 10,  0,  1 ) # not acknowledged: orange
COLOR_DARK_MAGENTA = ( 32,  0, 32,  1 )
COLOR_WAIT         = (  0,  5,  0,  1 )

# ACK transitions longer than this signal enable/disable
ACK_ENABLE_THRESHOLD_MS = 500

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                  VARIABLES
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

g_acknowledged = False
g_enabled      = False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                PIN CONFIGURATION
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# mast infrared
_paft_pin = Pin(PIN_PAFT, Pin.IN)
_mast_pin = Pin(PIN_MAST, Pin.IN)
_saft_pin = Pin(PIN_SAFT, Pin.IN)
# IFS bumpers
_stbd_pin = Pin(PIN_STBD, Pin.IN)
_cntr_pin = Pin(PIN_CNTR, Pin.IN)
_port_pin = Pin(PIN_PORT, Pin.IN)

# coms pins ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#               pin                 wire    use
_ack_pin  = Pin(PIN_ACK, Pin.IN)  # white   ACK
_int_pin  = Pin(PIN_INT, Pin.OUT) # grey    INT
_d0_pin   = Pin(PIN_D0, Pin.OUT)  # red     D0
_d1_pin   = Pin(PIN_D1, Pin.OUT)  # green   D1
_d2_pin   = Pin(PIN_D2, Pin.OUT)  # blue    D2
_d3_pin   = Pin(PIN_D3, Pin.OUT)  # blue    D3

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                  INITIALISE
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# configure SPI for controlling the DotStar
# uses software SPI as the pins used are not hardware SPI pins
spi = SPI(sck=Pin(TinyPICO.DOTSTAR_CLK), mosi=Pin(TinyPICO.DOTSTAR_DATA), miso=Pin(TinyPICO.SPI_MISO)) # create a DotStar instance
dotstar = DotStar(spi, 1, brightness = 0.5)    # just one DotStar, half brightness
TinyPICO.set_dotstar_power(True)               # turn on the power to the DotStar

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                   FUNCTIONS
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def check_ram():
    '''
    Tests RAM, flash green 3x if okay, flash red 3x otherwise.
    '''
    gc.collect()
    ram = gc.mem_free()
    col = COLOR_GREEN if ram > 4000000 else COLOR_RED
    for i in range (3):
        dotstar[0] = col
        time.sleep_ms(50)
        dotstar[0] = COLOR_BLACK
        time.sleep_ms(50)
    time.sleep_ms(150)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def wheel(pos):
    '''
    Input a value 0 to 255 to get a color value.
    The colours are a transition r - g - b - back to r.
    '''
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def reset_led():
    dotstar[0] = COLOR_BLACK

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def rotate(count):
    '''
    Unicorn on the DotStar.
    '''
    for i in range(count):
        for i in range(255):
            r,g,b = wheel(i)
            dotstar[0] = (r, g, b, 0.5)
            time.sleep(0.005)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def ready():
    '''
    Signal readiness.
    '''
    for j in range(50, 0, -1):
        dotstar[0] = COLOR_GREEN
        time.sleep_ms(j)
        reset_led()
        time.sleep_ms(j)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def clear_data():
    global _d0_pin, _d1_pin, _d2_pin, _d3_pin
    _d0_pin.value(0)
    _d1_pin.value(0)
    _d2_pin.value(0)
    _d3_pin.value(0)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def interrupt(state):
    '''
    INT: Interrupt pin is active low. This is an output pin
    connected to the Pi and listened to via pigpio.
    '''
    global _int_pin
    if state:
        _int_pin.value(0) # trigger interrupt
    else:
        _int_pin.value(1) # clear interrupt

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def triggered(orientation):
    global g_acknowledged, g_enabled, _d0_pin, _d1_pin, _d2_pin, _d3_pin
    '''
    If an orientation > 0 arrives we set the LED accordingly,
    and set the INT pin low.

    If the app is not enabled we only set the LED.

    We read the ACK pin in the loop and set the flag True
    once the Pi has acknowledged the message.

    We only alter the pins and set the LED if the flag is unacknowledged.
    Once acknowledged we clear the pins and set the color BLACK.
    '''
    # set LED color
    dotstar[0] = COLORS[orientation[3]]
    if orientation == ORIENTATION_NONE:
        clear_data()
        interrupt(False)
        g_acknowledged = False #                    changed!
    else:
        # FIXME should we do this based on g_acknowledged?
        # orientation = ORIENTATION_ALL # testing: all bits high
        _d3 = orientation[0]
        _d2 = orientation[1]
        _d1 = orientation[2]
        _d0 = orientation[3]
        print("♒ TRANSMIT:\t  {};\t{:d}{:d}{:d}{:d}".format(orientation[3], _d3, _d2, _d1, _d0))
        _d0_pin.value(_d0)
        _d1_pin.value(_d1)
        _d2_pin.value(_d2)
        _d3_pin.value(_d3)
        # trigger interrupt until ACK
        interrupt(True)
    time.sleep_ms(5)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def poll_ack():
    '''
    ACK:  A high-low transition longer than ACK_ENABLE_THRESHOLD_MS
    on the ACK pin is necessary to enable the script. Subsequent
    short pulses on the ACK pin are treated as acknowledgement by
    the host of successful data transfer.

    There is no facility to disable the script once enabled.
    '''
    global g_acknowledged, g_start_ticks, g_enabled
    if _ack_pin.value(): # if 1/True
        if not g_acknowledged: # then state transition has occurred
            # how long since the start ticks?
            if g_start_ticks and ( time.ticks_diff(time.ticks_ms(), g_start_ticks) > ACK_ENABLE_THRESHOLD_MS ):
                dotstar[0] = COLOR_RED # FIXME what state?
                print('🍅 RED   (long threshold)  ')
            else:
                dotstar[0] = COLOR_ACK # FIXME what state?
                print('🌎 TURQUOISE  changing from unacknowledged to acknowledged.  ')
                time.sleep_ms(100)
            g_acknowledged = True
            g_start_ticks = time.ticks_ms()
    else:
        if g_acknowledged: # then state transition has occurred
            # how long since the start ticks?
            if g_start_ticks and time.ticks_diff(time.ticks_ms(), g_start_ticks) > ACK_ENABLE_THRESHOLD_MS:
                dotstar[0] = COLOR_DARK_MAGENTA # FIXME LONG PULSE
                print('🍇 MAGENTA enabling... ')
                g_enabled = True
            else:
                print('🍊 ORANGE   ACK (short threshold)   ')
                dotstar[0] = COLOR_NOT_ACK # orange # FIXME SHORT PULSE
            time.sleep_ms(100)
            g_start_ticks = time.ticks_ms()
            g_acknowledged = False

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def poll():
    poll_ack()
    poll_data()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def poll_data():
    '''
    The loop callback, polling the sensor pins, calling triggered if low.
    '''
    global g_acknowledged, g_enabled
    if g_enabled:
        # NOTE: low is triggered
        if not _mast_pin.value():
            triggered(ORIENTATION_MAST) # COLOR_YELLOW
        elif not _stbd_pin.value():
            triggered(ORIENTATION_STBD) # COLOR_GREEN
        elif not _cntr_pin.value():
            triggered(ORIENTATION_CNTR) # COLOR_BLUE
        elif not _port_pin.value():
            triggered(ORIENTATION_PORT) # COLOR_RED
        elif not _paft_pin.value():
            triggered(ORIENTATION_PAFT) # COLOR_CYAN
        elif not _saft_pin.value():
            triggered(ORIENTATION_SAFT) # COLOR_MAGENTA
        else:
            if g_acknowledged:
                dotstar[0] = COLOR_ACK
                time.sleep_ms(100) # TEMP
            time.sleep_ms(5)
            triggered(ORIENTATION_NONE) # will blacken LED

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                   EXECUTE
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

check_ram()

# init (active low)
interrupt(False)

clear_data()

#ready()
rotate(1)
reset_led()

g_start_ticks = None # initial value

# start loop with frequency of 20Hz (50ms)
_timer = Timer(1)
_timer.init(period=50, mode=Timer.PERIODIC, callback=lambda n: poll())

#EOF
