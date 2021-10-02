#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-10-02
# modified: 2021-10-03
#
# An asynchronous RFM69 transceiver.
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
import asyncio
from RFM69 import Radio, FREQ_868MHZ, FREQ_915MHZ
import RPi.GPIO as GPIO
from colorama import init, Fore, Style
init(autoreset=True)

from core.config_loader import ConfigLoader
from core.logger import Logger, Level

# execution handler ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def signal_handler(signal, frame):
    print('\nsignal handler    :' + Fore.MAGENTA + Style.BRIGHT + ' INFO  : Ctrl-C caught: exiting...')
    print(Fore.MAGENTA + 'exit.')
    sys.exit(0)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Rfm69Radio(object):
    '''
    '''
    def __init__(self, config, loop, level=Level.INFO):
        self._log = Logger('radio', level)
        if config is None:
            raise ValueError('no configuration provided.')
        _cfg = config['kros'].get('hardware').get('rfm69_radio')
        self._loop = loop
        # configuration ..............
        self._frequency_name  = _cfg.get('frequency') # either 'FREQ_868MHZ' or default to FREQ_915MHZ
        if self._frequency_name == 'FREQ_868MHZ':
            self._log.info('frequency:\t868MHz')
            self._frequency = FREQ_868MHZ
        else:
            self._log.info('frequency:\t915MHz')
            self._frequency = FREQ_915MHZ
        self._spi_bus         = _cfg.get('spi_bus') # 0
        self._log.info('SPI bus:       \t{:d}'.format(self._spi_bus))
        self._spi_device      = _cfg.get('spi_device') # 0
        self._log.info('SPI device:    \t{:d}'.format(self._spi_device))
        self._network_id      = _cfg.get('network_id') # 100
        self._log.info('network ID:    \t{:d}'.format(self._network_id))
        self._node_id         = _cfg.get('node_id')       # the node ID of this device
        self._log.info('node ID:       \t{:d}'.format(self._node_id))
        self._recipient_id    = _cfg.get('recipient_id')  # identifier for target of messages
        self._log.info('recipient ID:  \t{:d}'.format(self._recipient_id))
        self._int_pin         = _cfg.get('interrupt_pin') # BOARD 18/GPIO 24
        self._log.info('interrupt pin:  \t{:d}'.format(self._int_pin))
        self._reset_pin       = _cfg.get('reset_pin') # BOARD 29/GPIO 5
        self._log.info('reset pin:      \t{:d}'.format(self._reset_pin))
        self._prom_mode       = _cfg.get('promiscuous_mode') # bool
        self._log.info('listen mode:    \t{}'.format('promiscuous' if self._prom_mode else 'normal'))
        self._tx_enabled      = _cfg.get('transmit_enabled')
        self._log.info('operation mode: \t{}'.format('transmit/receive' if self._tx_enabled else 'receive only'))
        self._attempts        = 5   # 3 default
        self._wait_time_ms    = 100 # 100 default
        self._counter         = itertools.count()
        self._enabled         = False
#       sys.exit(0) # TEMP
        # reset pin for radio (LOW is enabled)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self._reset_pin, GPIO.OUT)
#       GPIO.output(self._reset_pin, GPIO.HIGH) # reset radio
        self._log.info("📡 enabling radio...")
#       GPIO.output(self._reset_pin, GPIO.LOW) # enable radio
        self._log.info('ready')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _receive_function(self, radio, f_is_enabled):
        '''
        We'll run this function in a separate thread.
        '''
        self._log.info(Fore.BLUE + "🌎 _receive_function() begin.")
        while f_is_enabled():
            self._log.info(Fore.BLUE + "🌎 _receive_function() listening in loop...")
            # This call will block until a packet is received
            _packet = radio.get_packet()
            self._log.info(Fore.YELLOW + "Got a packet: ", end="")
            # process packet
            self._log.info(Fore.WHITE + '{}'.format(_packet))
#           self._log.info(Fore.BLUE + 'sending ack')
#           radio.send_ack(self._recipient_id)
            self._log.info(Fore.BLUE + "🌎 _receive_function() end of loop.")
        self._log.info("exit Rx loop.")

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
    async def receiver(self, radio, f_is_enabled):
        self._log.info(Fore.GREEN + 'receiver begin.')
        while f_is_enabled():
            self._log.info(Fore.GREEN + 'receiver loop.')
            for packet in radio.get_packets():
                self._log.info(Fore.GREEN + '🌎 packet received: {}'.format(packet.to_dict()))
#               await call_API("http://httpbin.org/post", packet)
            await asyncio.sleep(1.0)
        self._log.info(Fore.GREEN + 'receiver end.')
    
    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def transmit(self, radio, f_is_enabled):
        self._log.info(Fore.BLUE + 'transmit begin.')
        self._ping_counter = itertools.count()
        while f_is_enabled():
            _count = next(self._ping_counter)
            self._log.info(Fore.BLUE + 'transmit loop...')
            await self.send(radio, "ping-{:04d}".format(_count))
            await asyncio.sleep(5)
        self._log.info(Fore.BLUE + 'transmit end.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def send(self, radio, message):
        self._log.info(Fore.MAGENTA + 'sending message: \'{}\' to address {}'.format(message, self._recipient_id))
        if radio.send(self._recipient_id, message, attempts=self._attempts, waitTime=self._wait_time_ms):
            self._log.info(Fore.MAGENTA + Style.BRIGHT + 'acknowledgement received.')
        else:
            self._log.info(Fore.MAGENTA + 'no acknowledgement.')
    
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

        if not self._loop:
            self._loop = asyncio.get_event_loop()

        try:

            time.sleep(1.0)
            self._log.info("📡 creating link to radio...")
            with Radio(self._frequency,              \
                       spiBus = self._spi_bus,       \
                       spiDevice = self._spi_device, \
                       interruptPin = self._int_pin, \
                       resetPin = self._reset_pin,   \
                       nodeID = self._node_id,       \
                       networkID = self._network_id, \
                       auto_acknowledge = True,      \
                       isHighPower = True,           \
                       verbose = True,               \
                       promiscuousMode = self._prom_mode ) as _radio:
                self._log.info("📡 established link to radio.")
#               self._reset_radio(_radio)
#               _radio.begin_receive()

                self._log.info('starting loop:\t' + Fore.YELLOW + 'type Ctrl-C to exit.')
#               # create a thread to run _receive_function in the background and start it
#               receiveThread = threading.Thread(target = self._receive_function, args=(_radio, lambda: self._enabled))
#               receiveThread.start()
                
                self._log.info('creating receiver task...')
                self._loop.create_task(self.receiver(_radio, lambda: self._enabled))
                self._log.info('creating transmit task...')
                self._loop.create_task(self.transmit(_radio, lambda: self._enabled))

                self._log.info('run forever...')
                self._loop.run_forever()
                self._log.info('after forever.')

#               while self._enabled:
#                   # after 5 seconds send a message
#                   _count = next(self._counter)
#                   time.sleep(5)
#                   if self._tx_enabled:
#                       self._log.info('[{:04d}] sending from node ID {:d} to recipient ID {:d}'.format(
#                               _count, self._node_id, self._recipient_id))
#                       if _radio.send(self._recipient_id, "TEST", attempts=3, waitTime=100):
#                           self._log.info(Fore.GREEN + "Acknowledgement received.")
#                       else:
#                           self._log.info(Style.DIM + "No acknowledgement.")
#                   else:
#                       self._log.info(Style.DIM + '[{:04d}] Rx only.'.format(_count))

        except KeyboardInterrupt:
#           self._enabled = False
            self._log.info(Style.BRIGHT + 'caught Ctrl-C; exiting...')
        except Exception:
#           self._enabled = False
            self._log.error(Fore.RED + Style.BRIGHT + '🤡 error with radio: {}'.format(traceback.format_exc()))
#           self._reset_radio(_radio)
        finally:
            self._log.info('closing...')
            self._enabled = False
            self._log.info('finally; enabled: {}'.format(self._enabled))
            self._loop.close()
            time.sleep(2.0)
            self._log.info('closed.')

# main ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main(argv):

    signal.signal(signal.SIGINT, signal_handler)

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _radio = Rfm69Radio(_config, None)
    _radio.enable()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
if __name__== "__main__":
    main(sys.argv[1:])

# prevent Python script from exiting abruptly
#signal.pause()

#EOF
