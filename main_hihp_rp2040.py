# MicroPython External Clock for Itsy Bitsy RP2040
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-08-26
# modified: 2021-09-08
#
# Uses the Neopixel library downloadable from:
#
#    https://github.com/blaz-r/pi_pico_neopixel
#

from machine import UART
from machine import Timer
from machine import Pin
import time

import itertools
from queue import Queue
from switch import Switch

# flash the unicorns
import upy_utils as ut

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                                  CONSTANTS
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# pin definitions ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# GPIO   BAT   G   USB  11   10    9    8    7    6   16    3    2    0    1
#  PIN   BAT   G   USB  13   12   11!  10    9    7    5!  SCL  SDA  TX   RX
#         ◆    ◆    ◆    ◆    ◆    ◆    ◆    ◆    ◆    ◆    ◆    ◆    ◆    ◆
#                        A    B    x    C    D    E    x    F
# NOTE: specify GPIO (back of board) not Pin number (front of board)
# NOTE: You can't use GPIO 16 as that's the NeoPixel's power pin!
#       You also can't use GPIO 11 as that's the red LED.

IN_D3_PIN = 11  # A. port aft infrared
IN_D4_PIN = 10  # B, mast infrared
IN_D5_PIN =  8  # C. starboard aft infrared

IN_D0_PIN =  7  # port bumper switch
IN_D1_PIN =  6  # center bumper switch
IN_D2_PIN =  3  # starboard bumper switch

UART_ID    =  0  # UART 0 or 1?
#TX_PIN    =  0  # TX/GP00 - The main UART0 TX pin, connect to Rx on Pi.
#RX_PIN    =  1  # RX/GP01 - The main UART0 RX pin, connect to Tx on Pi.
BAUD_RATE = 9600

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
    UART recipient. This gets called every 50ms.
    '''
    global g_uart, g_queue, g_transmitting, g_counter
    if not g_transmitting and not g_queue.empty():
        g_transmitting = True
        try:
            while not g_queue.empty():
                _data, _color = g_queue.get()
#               print("writing data: {}; color: {}".format(_data, _color))
                ut.rgb_led(_color)
                g_uart.write(_data)
                time.sleep_ms(50)
            time.sleep_ms(10)
        except Exception as e:
            print("ERROR: {}".format(e))
            ut.error()
            time.sleep(2.0)
        finally:
            g_queue.clear()
            g_transmitting = False
    else:
        if next(g_counter) % 20 == 0.0:
            ut.rgb_led(ut.COLOR_TURQUOISE)
            time.sleep_ms(10)
    time.sleep_ms(10)
    ut.rgb_led(ut.COLOR_BLACK)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                            INITIALISE & EXECUTE
# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

# configure SPI for controlling the DotStar
# uses software SPI as the pins used are not hardware SPI pins
#spi = SPI(sck=Pin(TinyPICO.DOTSTAR_CLK), mosi=Pin(TinyPICO.DOTSTAR_DATA), miso=Pin(TinyPICO.SPI_MISO)) # create a DotStar instance
#dotstar = DotStar(spi, 1, brightness = 0.5)    # just one DotStar, half brightness
#TinyPICO.set_dotstar_power(True)               # turn on the power to the DotStar

try:

    g_counter = itertools.count()
    g_queue   = Queue()

    g_transmitting = False

    #tx_pin = Pin(TX_PIN)
    #rx_pin = Pin(RX_PIN)
    #g_uart = UART(UART_ID, baudrate=BAUD_RATE, parity=None, tx=_tx_pin, rx=_rx_pin, stop=1)
    g_uart = UART(UART_ID, baudrate=BAUD_RATE, parity=None) #tx=_tx_pin, rx=_rx_pin, stop=1)

    # pin configuration
    g_pins = {}
    _pin_0 = define_pin(IN_D0_PIN, 'port\n', ut.COLOR_RED,     False)
    _pin_1 = define_pin(IN_D1_PIN, 'cntr\n', ut.COLOR_BLUE,    False)
    _pin_2 = define_pin(IN_D2_PIN, 'stbd\n', ut.COLOR_GREEN,   False)
    _pin_3 = define_pin(IN_D3_PIN, 'paft\n', ut.COLOR_CYAN,    False)
    _pin_4 = define_pin(IN_D4_PIN, 'mast\n', ut.COLOR_YELLOW,  False)
    _pin_5 = define_pin(IN_D5_PIN, 'saft\n', ut.COLOR_MAGENTA, False)

    # start polling loop with frequency of 20Hz (50ms)
    _timer = Timer(period=50, mode=Timer.PERIODIC, callback=lambda n: poll())

    ut.ready()

except Exception as e:
    print("error: {}".format(e))
    ut.error()
finally:
    ut.red_led(0)

#EOF
