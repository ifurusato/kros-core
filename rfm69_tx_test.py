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

import sys, signal, time, threading, traceback
from RFM69 import Radio, FREQ_315MHZ, FREQ_433MHZ, FREQ_868MHZ, FREQ_915MHZ
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

    def __init__(self, level=Level.INFO):
        self._log = Logger('radio', Level.INFO)
        self._node_id      = 2
        self._network_id   = 100
        self._recipient_id = 1
        self._enabled      = False
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
    def enable(self):
        '''
        The following are for an Adafruit RFM69HCW Transceiver Radio Bonnet
            https://www.adafruit.com/product/4072
        You should adjust them to whatever matches your radio.
        '''
        _radio = None
        self._enabled = True
        try:
            self._log.info("📡 creating link to radio...")
            with Radio(FREQ_915MHZ,        \
                       self._node_id,      \
                       self._network_id,   \
                       isHighPower = True, \
                       verbose = True,     \
                       interruptPin = 15,  \
                       resetPin = 22,      \
                       promiscuousMode = True, \
                       spiDevice = 1) as _radio:
                self._log.info("📡 established link to radio.")

                self._log.info("Starting loop...")

                # Create a thread to run receiveFunction in the background and start it
                receiveThread = threading.Thread(target = self.receiveFunction, args=(_radio,))
                receiveThread.start()

                while self._enabled:
                    # after 5 seconds send a message
                    time.sleep(5)
                    self._log.info ("Sending...")
                    if _radio.send(self._recipient_id, "TEST", attempts=3, waitTime=100):
                        self._log.info("Acknowledgement received.")
                    else:
                        self._log.info("No acknowledgement.")

        except KeyboardInterrupt:
            self._log.info(Style.BRIGHT + 'caught Ctrl-C; exiting...')
        except Exception:
            self._log.error(Fore.RED + Style.BRIGHT + '🤡 error with radio: {}'.format(traceback.format_exc()))
            if _radio:
                self._log.info('🤡 executing hard reset on radio...')
                try:
                    _radio._reset_hard()
                    self._log.info('🤡 hard reset complete.')
                except Exception as e:
                    self._log.info('🤡 hard reset error: {}'.format(e))
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
