# UART Data Transmitter for Sensor Data (UDT4SD)
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-26
# modified: 2021-09-13
#

from machine import UART
from machine import Timer
from machine import Pin
import time

import itertools
from queue import Queue
from switch import Switch

# flash the unicorns
import tp_utils as tpu

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                  CONSTANTS
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# pin definitions ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

IN_D0_PIN = 27 # port bumper switch
IN_D1_PIN = 26 # center bumper switch
IN_D2_PIN = 25 # starboard bumper switch
IN_D3_PIN = 15 # port aft infrared
IN_D4_PIN = 14 # mast infrared
IN_D5_PIN =  4 # starboard aft infrared

TX_PIN    = 23 # connect to Rx on Pi
RX_PIN    = 19 # connect to Tx on Pi
BAUD_RATE = 19200

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                   FUNCTIONS
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def irq_callback(pin):
    '''
    The IRQ callback that puts the data corresponding to the
    pin into the queue.

    If we're transmitting then further data is likely noise.
    '''
    global g_transmitting, g_queue, g_pins
    if not g_transmitting: 
        # only enqueue the record if not already present in queue.
#       g_queue.put_as_set(g_pins.get(id(pin)))
        # or just shove it in there anyway...
        g_queue.put(g_pins.get(id(pin)))

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def define_pin(pin_num, message, color, is_switch):
    '''
    If is_switch is true, we use the Switch class, otherwise a Pin and an IRQ.
    '''
    global g_pins
    if is_switch:
        _pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        _switch = Switch(pin_num, pin=_pin, callback=irq_callback)
    else:
        _pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        # define interrupt
        #   Pin.IRQ_FALLING     interrupt on falling edge.
        #   Pin.IRQ_RISING      interrupt on rising edge.
        #   Pin.IRQ_LOW_LEVEL   interrupt on low level.
        #   Pin.IRQ_HIGH_LEVEL  interrupt on high level.
        # These values can be OR’ed together to trigger on multiple events.
        _pin.irq(handler=irq_callback, trigger=Pin.IRQ_FALLING or Pin.IRQ_LOW_LEVEL)
    g_pins[id(_pin)] = ( message, color )

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def poll():
    '''
    Pop all elements of the queue, transmitting them to the
    UART recipient.
    '''
    global g_uart, g_queue, g_transmitting, g_counter
    if not g_transmitting and not g_queue.empty():
        g_transmitting = True
        try:
            while not g_queue.empty():
                _data, _color = g_queue.get()
                tpu.led(_color)
#               print("🌞 WRITE: {}".format(_data))
                g_uart.write(_data)
                time.sleep_ms(50)
#           time.sleep_ms(4)
        except Exception as e:
#           print(e)
            tpu.led(tpu.COLOR_RED)
            time.sleep(2.0)
        finally:
            g_queue.clear()
            g_transmitting = False
    else:
        if next(g_counter) % 20 == 0.0:
            tpu.led(tpu.COLOR_TURQUOISE)
            time.sleep_ms(4)
    tpu.led(tpu.COLOR_BLACK)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                            INITIALISE & EXECUTE
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# configure SPI for controlling the DotStar
# uses software SPI as the pins used are not hardware SPI pins
#spi = SPI(sck=Pin(TinyPICO.DOTSTAR_CLK), mosi=Pin(TinyPICO.DOTSTAR_DATA), miso=Pin(TinyPICO.SPI_MISO)) # create a DotStar instance
#dotstar = DotStar(spi, 1, brightness = 0.5)    # just one DotStar, half brightness
#TinyPICO.set_dotstar_power(True)               # turn on the power to the DotStar

g_counter = itertools.count()
g_queue   = Queue()

g_transmitting = False

g_uart = UART(1, baudrate=BAUD_RATE, parity=None, tx=TX_PIN, rx=RX_PIN, stop=1)

# pin configuration
g_pins = {}
_pin_0 = define_pin(IN_D0_PIN, 'port\n', tpu.COLOR_RED, True)
_pin_1 = define_pin(IN_D1_PIN, 'cntr\n', tpu.COLOR_BLUE, True)
_pin_2 = define_pin(IN_D2_PIN, 'stbd\n', tpu.COLOR_GREEN, True)
_pin_3 = define_pin(IN_D3_PIN, 'paft\n', tpu.COLOR_CYAN, False)
_pin_4 = define_pin(IN_D4_PIN, 'mast\n', tpu.COLOR_YELLOW, False)
_pin_5 = define_pin(IN_D5_PIN, 'saft\n', tpu.COLOR_MAGENTA, False)

# start polling loop with frequency of 20Hz (50ms)
_timer = Timer(1)
_timer.init(period=50, mode=Timer.PERIODIC, callback=lambda n: poll())

tpu.ready()

#EOF
