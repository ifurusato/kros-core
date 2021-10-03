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
# ......................................
# Notes on the Raspberry Pi Wiring:
#
#  RFM69 ___ BOARD pin ___
#  EN:       (default high, not connected)
#  G0:       28 (ID_SC)
#  SCK:      23 (SCLK, GPIO 11)
#  MISO:     21 (MISO, GPIO 9)
#  MOSI:     19 (MOSI, GPIO 10)
#  CS:       24 (CE0, GPIO 8)
#  RST:      29 (GPIO 5)
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

import sys, signal, time, traceback, itertools
import asyncio
from RFM69 import Radio, FREQ_868MHZ, FREQ_915MHZ
import RPi.GPIO as GPIO
from colorama import init, Fore, Style
init(autoreset=True)

from core.config_loader import ConfigLoader
from core.message_factory import MessageFactory
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
    def __init__(self, config, message_bus, message_factory, level=Level.INFO):
        self._log = Logger('radio', level)
        if config is None:
            raise ValueError('no configuration provided.')
        _cfg = config['kros'].get('hardware').get('rfm69_radio')
        self._message_bus     = message_bus
        self._message_factory = message_factory
        self._loop = self._message_bus.loop
        # configuration ..............
        self._frequency_name  = _cfg.get('frequency') # either 'FREQ_868MHZ' or default to FREQ_915MHZ
        if self._frequency_name == 'FREQ_868MHZ':
            self._log.info('frequency:\t868MHz')
            self._frequency = FREQ_868MHZ
        else:
            self._log.info('frequency:\t915MHz')
            self._frequency = FREQ_915MHZ
        self._spi_bus    = _cfg.get('spi_bus') # 0
        self._log.info('SPI bus:       \t{:d}'.format(self._spi_bus))
        self._spi_device = _cfg.get('spi_device') # 0
        self._log.info('SPI device:    \t{:d}'.format(self._spi_device))
        self._network_id = _cfg.get('network_id') # 100
        self._log.info('network ID:    \t{:d}'.format(self._network_id))
        self._node_id    = _cfg.get('node_id')       # the node ID of this device
        self._log.info('node ID:       \t{:d}'.format(self._node_id))
        self._rx_id      = _cfg.get('recipient_id')  # identifier for target of messages
        self._log.info('recipient ID:  \t{:d}'.format(self._rx_id))
        self._int_pin    = _cfg.get('interrupt_pin') # BOARD 18/GPIO 24
        self._log.info('interrupt pin:  \t{:d}'.format(self._int_pin))
        self._reset_pin  = _cfg.get('reset_pin') # BOARD 29/GPIO 5
        self._log.info('reset pin:      \t{:d}'.format(self._reset_pin))
        self._attempts   = _cfg.get('attempts') # 3 attempts default
        self._log.info('attempts:       \t{:d}'.format(self._attempts))
        self._timeout_ms = _cfg.get('timeout_ms') # 100ms default
        self._log.info('wait time:      \t{:d}ms'.format(self._timeout_ms))
        self._prom_mode  = _cfg.get('promiscuous_mode') # bool
        self._log.info('listen mode:    \t{}'.format('promiscuous' if self._prom_mode else 'normal'))
        self._tx_enabled = _cfg.get('transmit_enabled')
        self._log.info('operation mode: \t{}'.format('transmit/receive' if self._tx_enabled else 'receive only'))
        self._auto_acknowledge = False
        self._high_power = False
        self._sent_counter   = itertools.count()
        self._ack_counter    = itertools.count()
        self._no_ack_counter = itertools.count()
        self._tx_counter     = itertools.count()
        self._rx_counter     = itertools.count()
        self._enabled    = False
        # configure reset pin for radio (LOW is enabled)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self._reset_pin, GPIO.OUT)
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
#           radio.send_ack(self._rx_id)
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
    async def _receive(self, radio, f_is_enabled):
        self._log.info(Fore.GREEN + 'receive begin.')
        while f_is_enabled():
            self._log.info(Fore.GREEN + 'receive loop.')
            for _packet in radio.get_packets():
                _rx_count = next(self._rx_counter)
                self._log.info(Fore.GREEN + '[{:04d}] 🌎 packet received: {}'.format(_rx_count, _packet.to_dict()))
                _message = self.message_factory.create_message(Event.RADIO_PACKET, _packet)
                await self._message_bus.publish_message(self, _message)
#               await call_API("http://httpbin.org/post", packet)
            await asyncio.sleep(1.0)
        self._log.info(Fore.GREEN + 'receive end.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _transmit(self, radio, f_is_enabled):
        self._log.info(Fore.BLUE + 'transmit begin.')
        while f_is_enabled():
            _tx_count = next(self._tx_counter)
            self._log.info(Fore.BLUE + '[{:04d}] transmitting message...'.format(_tx_count))
            await self._send(radio, "ping-{:04d}".format(_tx_count))
            await asyncio.sleep(5)
        self._log.info(Fore.BLUE + 'transmit end.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _send(self, radio, message):
        _sent_count = next(self._sent_counter)
        self._log.info(Fore.MAGENTA + '[{:04d}] sending message: \'{}\' to address {}'.format(
                _sent_count, message, self._rx_id))
        if radio.send(self._rx_id, message, attempts=self._attempts, waitTime=self._timeout_ms):
            _ack_count = next(self._ack_counter)
            self._log.info(Fore.MAGENTA + Style.BRIGHT + 'acknowledgement received.'.format(_ack_count))
        else:
            _no_ack_count = next(self._no_ack_counter)
            self._log.info(Fore.MAGENTA + '[{:04d}] no acknowledgement.'.format(_no_ack_count))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        if self._enabled:
            self._log.warning("already enabled.")
            return
        self._enabled = True
        self._log.info("📡 enabling RFM69 radio...")
        GPIO.output(self._reset_pin, GPIO.LOW)
        time.sleep(1.0)
        _radio = None

        try:

            self._log.info("📡 establishing link to radio...")
            with Radio(self._frequency,
                       spiBus = self._spi_bus,
                       spiDevice = self._spi_device,
                       interruptPin = self._int_pin,
                       resetPin = self._reset_pin,
                       nodeID = self._node_id,
                       networkID = self._network_id,
                       auto_acknowledge = self._auto_acknowledge,
                       isHighPower = self._high_power,
                       verbose = True,
                       promiscuousMode = self._prom_mode ) as _radio:
                self._log.info("📡 established link to radio.")

                self._log.info('creating receive task...')
                self._loop.create_task(self._receive(_radio, lambda: self._enabled))
                self._log.info('creating transmit task...')
                self._loop.create_task(self._transmit(_radio, lambda: self._enabled))

                self._log.info('starting forever loop:\t' + Fore.YELLOW + 'type Ctrl-C to exit.')
                self._loop.run_forever()
                self._log.info('after forever.')

        except KeyboardInterrupt:
            self._log.info(Style.BRIGHT + 'caught Ctrl-C; exiting...')
        except Exception:
            self._log.error(Fore.RED + Style.BRIGHT + '🤡 error with radio: {}'.format(traceback.format_exc()))
#           self._reset_radio(_radio)
        finally:
            self._log.info('closing...')
            self._enabled = False
            self._log.info('finally; enabled: {}'.format(self._enabled))
            self._loop.close()
            time.sleep(2.0)
            self._log.info('closed.')

    # end class ........................

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class FakeMessageBus():
    '''
    Mocks the Message Bus.
    '''
    def __init__(self, level=Level.INFO):
        self._log = Logger('fake-bus', level)
        self._loop = asyncio.get_event_loop()
        self._publish_delay_sec = 0.1
        self._subscribers = []
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def loop(self):
        return self._loop

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def subscribers(self):
        return self._subscribers

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def publish_message(self, message):
        self._log.info('🍉 published message: {}'.format(message))
        await asyncio.sleep(self._publish_delay_sec)

    # end FakeMessageBus ..............................


# main ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main(argv):

    signal.signal(signal.SIGINT, signal_handler)

    # read YAML configuration
    _level = Level.INFO
    _loader = ConfigLoader(_level)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _message_bus = FakeMessageBus()
    _message_factory = MessageFactory(_message_bus, _level)
    _radio = Rfm69Radio(_config, _message_bus, _level)
    _radio.enable()

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
if __name__== "__main__":
    main(sys.argv[1:])

# prevent Python script from exiting abruptly
#signal.pause()

#EOF
