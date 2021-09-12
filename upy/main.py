# UART Data Transmitter for Sensor Data (UDT4SD)
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-26
# modified: 2021-09-12
#

from machine import UART
from machine import Timer
from machine import Pin
from machine import SPI
import tinypico as TinyPICO
from dotstar import DotStar
import time, gc

from queue import Queue

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                  CONSTANTS
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# pin definitions ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# input pins .....................................
IN_D0_PIN   = 27 # port bumper switch
IN_D1_PIN   = 26 # center bumper switch
IN_D2_PIN   = 25 # starboard bumper switch
IN_D3_PIN   = 15 # port aft infrared
IN_D4_PIN   = 14 # mast infrared
IN_D5_PIN   =  4 # starboard aft infrared

UART_TX_PIN = 23 # connect to Rx on Pi
UART_RX_PIN = 19 # connect to Tx on Pi
BAUD_RATE   = 19200

# An enumeration of the different packets of data to send
# for each corresponding pin, using an int index.
ENTRY_0 = [ 0, 'port' ] # port
ENTRY_1 = [ 1, 'cntr' ] # center
ENTRY_2 = [ 2, 'stbd' ] # starboard
ENTRY_3 = [ 3, 'paft' ] # port-aft
ENTRY_4 = [ 4, 'mast' ] # mast
ENTRY_5 = [ 5, 'saft' ] # starboard-aft
ENTRIES = [ ENTRY_0, ENTRY_1, ENTRY_2, ENTRY_3, ENTRY_4, ENTRY_5 ]

# Colors ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# define constant colours on the Dotstar .........
COLOR_BLACK        = (  0,  0,  0, 10 ) # 0
COLOR_RED          = ( 64,  0,  0,  1 ) # 1
COLOR_BLUE         = (  0,  0, 64,  1 ) # 2
COLOR_GREEN        = (  0, 64,  0,  1 ) # 3
COLOR_CYAN         = (  0, 64, 64,  1 ) # 4
COLOR_YELLOW       = ( 64, 64,  0,  1 ) # 5
COLOR_MAGENTA      = ( 64,  0, 64,  1 ) # 6
# colors associated with each sensor
COLORS = [ COLOR_RED, COLOR_BLUE, COLOR_GREEN, COLOR_CYAN, COLOR_YELLOW, COLOR_MAGENTA ]

# other colors .............................
COLOR_TURQUOISE    = (  0, 10,  7,  1 )
COLOR_ORANGE       = ( 32, 16,  0,  1 )
COLOR_PURPLE       = (  9,  0,  7,  1 )
COLOR_DARK_MAGENTA = ( 32,  0, 32,  1 )
COLOR_PINK         = ( 64, 32, 32,  1 )
COLOR_YELLOW_GREEN = ( 32, 64,  0,  1 )
COLOR_SKY_BLUE     = (  8, 12, 64,  1 )
COLOR_GREY         = ( 16, 16, 16,  1 )
COLOR_WHITE        = ( 64, 64, 64,  1 )

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
        return (0, 0, 0)
    elif pos < 85:
        return (int(pos * 3), int(255 - pos * 3), 0)
    elif pos < 170:
        pos -= 85
        return (int(255 - pos * 3), 0, int(pos * 3))
    else:
        pos -= 170
        return (0, int(pos * 3), int(255 - pos * 3))

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def spin_wheel(count):
    '''
    Unicorn on the DotStar.
    '''
    for i in range(count):
        for i in range(255):
            r,g,b = wheel(i)
            dotstar[0] = (r, g, b, 0.5)
            time.sleep(0.005)
    time.sleep(0.1)
    dotstar[0] = COLOR_BLACK

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def ready():
    '''
    Signal readiness.
    '''
    for j in range(50, 0, -1):
        dotstar[0] = COLOR_GREEN
        time.sleep_ms(j)
        dotstar[0] = COLOR_BLACK
        time.sleep_ms(j)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def transmit_queue():
    '''
    Pop all elements of the queue, transmitting them to the
    UART recipient.
    '''
    global g_uart, g_queue, g_transmitting
    if not g_transmitting:
        g_transmitting = True
        try:
            while not g_queue.empty():
                _data, _color = g_queue.pop()
                dotstar[0] = _color
                g_uart.write(_data)
                time.sleep_ms(100)
        except Exception as e:
            dotstar[0] = COLOR_ORANGE
        finally:
            time.sleep_ms(10) # debounce
            dotstar[0] = COLOR_BLACK
            g_transmitting = False

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def enqueue(record):
    '''
    Only enqueue the record if not already present in queue.
    '''
    global g_queue
    g_queue.push_as_set(record)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def irq0_handler(pin):
    enqueue(('PORT\n', COLOR_RED))

def irq1_handler(pin):
    enqueue(('CNTR\n', COLOR_BLUE))

def irq2_handler(pin):
    enqueue(('STBD\n', COLOR_GREEN))

def irq3_handler(pin):
    enqueue(('PAFT\n', COLOR_CYAN))

def irq4_handler(pin):
    enqueue(('MAST\n', COLOR_YELLOW))

def irq5_handler(pin):
    enqueue(('SAFT\n', COLOR_MAGENTA))

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def define_pin(pin_num, handler):
    _pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
    # define interrupt
    _pin.irq(handler=handler, trigger=Pin.IRQ_FALLING)
    return _pin

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def poll():
    global g_queue, g_transmitting
    if not g_transmitting:
        dotstar[0] = COLOR_TURQUOISE
        time.sleep_ms(4)
        if not g_queue.empty():
            transmit_queue()
        dotstar[0] = COLOR_BLACK
        time.sleep_ms(76)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                 INITIALISE
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# configure SPI for controlling the DotStar
# uses software SPI as the pins used are not hardware SPI pins
spi = SPI(sck=Pin(TinyPICO.DOTSTAR_CLK), mosi=Pin(TinyPICO.DOTSTAR_DATA), miso=Pin(TinyPICO.SPI_MISO)) # create a DotStar instance
dotstar = DotStar(spi, 1, brightness = 0.5)    # just one DotStar, half brightness
TinyPICO.set_dotstar_power(True)               # turn on the power to the DotStar

g_queue = Queue()

g_transmitting = False

g_uart = UART(1, baudrate=BAUD_RATE, parity=None, tx=UART_TX_PIN, rx=UART_RX_PIN, stop=1)

# pin configuration
_in_d0_pin = define_pin(IN_D0_PIN, irq0_handler) # PORT
_in_d1_pin = define_pin(IN_D1_PIN, irq1_handler) # CNTR
_in_d2_pin = define_pin(IN_D2_PIN, irq2_handler) # STBD
_in_d3_pin = define_pin(IN_D3_PIN, irq3_handler) # PAFT
_in_d4_pin = define_pin(IN_D4_PIN, irq4_handler) # MAST
_in_d5_pin = define_pin(IN_D5_PIN, irq5_handler) # SAFT

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                   EXECUTE
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

check_ram()
spin_wheel(1)

# start loop with frequency of 20Hz (50ms)
_timer = Timer(1)
_timer.init(period=50, mode=Timer.PERIODIC, callback=lambda n: poll())

ready()

#EOF
