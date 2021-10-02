#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-10-02
# modified: 2021-10-02
#
# Basic RFM69 transceiver.
#
# Uses RFM69 library:  https://rpi-rfm69.readthedocs.io/en/latest/
# Installed via:
#
#    sudo pip3 install rpi-rfm69
#
# Installed at:  /usr/local/lib/python3.8/site-packages/RFM69/radio.py
#
# pylint: disable=missing-function-docstring,unused-import,redefined-outer-name
#
# ......................................
# Notes on the Pimoroni Breakout Garden:
#
# On the single SPI slot version:
#
# The SPI slot on Breakout Garden Mini uses:
# * chip select 1 (BCM 7) and
# * the GPIO pin (BCM 19) for things like LCD backlights
#
# On the double SPI slot version:
#
# The top/back slot (closest to the Breakout Garden logo) uses:
# * chip select 0 (BCM 8) and
# * the GPIO pin (BCM 18) for things like LCD backlights
#
# The bottom/front slot uses
# * chip select 1 (BCM 7) and
# * the GPIO pin (BCM 19) for things like LCD backlights
#

import sys, signal, time, threading, traceback, itertools
from RFM69 import Radio, FREQ_315MHZ, FREQ_433MHZ, FREQ_868MHZ, FREQ_915MHZ
import RPi.GPIO as GPIO
from colorama import init, Fore, Style
init()

from core.rate import Rate
from core.logger import Logger, Level

# execution handler ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def signal_handler(signal, frame):
    print('\nsignal handler    :' + Fore.MAGENTA + Style.BRIGHT + ' INFO  : Ctrl-C caught: exiting...' + Style.RESET_ALL)

    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.exit(0)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Rfm69Radio(object):
    '''
    '''
    def __init__(self, level=Level.INFO):
        self._log = Logger('radio', level)
        self._spi_device      = 0
        self._network_id      = 100
        self._log.info('SPI device {:d} on network ID {:d}'.format(self._spi_device, self._network_id))
        self._node_id         = 2
        self._recipient_id    = 1
        self._log.info('node ID {:d} sending to recipient ID {:d}'.format(self._node_id, self._recipient_id))
        self._interruptPin    = 18 # GPIO 24, was '15' in original code
        self._reset_pin       = 29 # GPIO 5
        self._promiscuousMode = True
        self._counter         = itertools.count()
        self._enabled         = False
        # reset pin for radio (LOW is enabled)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self._reset_pin, GPIO.OUT)
#       GPIO.output(self._reset_pin, GPIO.HIGH) # reset radio
        self._log.info("📡 enabling radio...")
        GPIO.output(self._reset_pin, GPIO.LOW) # enable radio
        self._log.info('ready')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def receiveFunction(self, radio):
        '''
        We'll run this function in a separate thread.
        '''
        while True:
            # This call will block until a packet is received
            _packet = radio.get_packet()
            self._log.info(Fore.YELLOW + "Got a packet: ", end="")
            # process packet
            self._log.info(Fore.WHITE + '{}'.format(_packet))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _reset_radio(self, radio):
        '''
        Perform a hard reset on the RFM69 radio.
        '''
        if radio:
            self._log.info('🤡 executing hard reset on radio...')
            try:
                radio._reset_radio()
                self._log.info('🤡 hard reset complete.')
            except Exception as e:
                self._log.info('🤡 error performing hard reset: {}'.format(e))
        else:
            self._log.info('🤡 no radio available.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        '''
        The following are for an Adafruit RFM69HCW Transceiver Radio Bonnet
            https://www.adafruit.com/product/4072
        You should adjust them to whatever matches your radio.
        '''
        if self._enabled:
            self._log.warning("already enabled.")
            return
        self._enabled = True
        _radio = None

        try:
            time.sleep(1.0)
            self._log.info("📡 creating link to radio...")
            with Radio(FREQ_915MHZ,        \
                       self._node_id,      \
                       self._network_id,   \
                       isHighPower = True, \
                       verbose = True,     \
                       interruptPin = self._interruptPin, \
                       resetPin = 22,      \
                       promiscuousMode = self._promiscuousMode, \
                       spiDevice = self._spi_device) as _radio:
                self._log.info("📡 established link to radio.")
#               self._reset_radio(_radio)

                self._log.info("Starting loop...")

                # Create a thread to run receiveFunction in the background and start it
                receiveThread = threading.Thread(target = self.receiveFunction, args=(_radio,))
                receiveThread.start()

                while self._enabled:
                    # after 5 seconds send a message
                    _count = next(self._counter)
                    time.sleep(5)
                    self._log.info('[{:04d}] sending from node ID {:d} to recipient ID {:d}'.format(_count, self._node_id, self._recipient_id))
                    if _radio.send(self._recipient_id, "TEST", attempts=3, waitTime=100):
                        self._log.info(Fore.GREEN + "Acknowledgement received.")
                    else:
                        self._log.info(Style.DIM + "No acknowledgement.")

        except KeyboardInterrupt:
            self._log.info(Style.BRIGHT + 'caught Ctrl-C; exiting...')
        except Exception:
            self._log.error(Fore.RED + Style.BRIGHT + '🤡 error with radio: {}'.format(traceback.format_exc()))
#           self._reset_radio(_radio)
        finally:
            self._enabled = False
            self._log.info('finally.')

# main ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main(argv):

    signal.signal(signal.SIGINT, signal_handler)

    _radio = Rfm69Radio()
    _radio.enable()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
if __name__== "__main__":
    main(sys.argv[1:])

# prevent Python script from exiting abruptly
#signal.pause()

#EOF
