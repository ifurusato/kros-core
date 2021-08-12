#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-03-16
# modified: 2020-06-12
#

import sys, itertools, traceback
import asyncio
from enum import Enum
from colorama import init, Fore, Style
init()

import hardware.ThunderBorg3 as ThunderBorg

from core.logger import Level, Logger
from core.event import Event
from core.publisher import Publisher

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class BatteryCheck(Publisher):

    _LISTENER_LOOP_NAME = '__battery_listener_loop'

    '''
    This uses both the ThunderBorg battery level method and the three channels of
    an ADS1015 to measure both the raw voltage of the battery and that of two 5
    volt regulators, labeled A and B. If any fall below a specified threshold a
    low battery message is sent to the message bus.

    If unable to establish communication with the ADS1015 this will raise a
    RuntimeError.

    This uses the ThunderBorg RGB LED to indicate the battery level of a Makita 18V
    Lithium-Ion power tool battery, whose actual top voltage is around 20 volts.
    When disabled this reverts the RGB LED back to is original indicator as the
    input battery voltage of the ThunderBorg. This is generally the same value but
    this class enumerates the value so that its state is more obvious.

    Configuration:
    battery_channel:       the ADS1015 channel: 0, 1 or 2 used to measure the raw battery voltage
    five_volt_a_channel:   the ADS1015 channel: 0, 1 or 2 used to measure the 5v regulator battery voltage
    five_volt_b_channel:   the ADS1015 channel: 0, 1 or 2 used to measure the 5v regulator battery voltage

    Parameters:
    :param message_bus:    the message bus
    :param level:          the logging level

    How many times should we sample before accepting a first value?
    '''
    def __init__(self, config, message_bus, message_factory, level):
        Publisher.__init__(self, 'battery', config, message_bus, message_factory, level=level)
#       self._log = Logger("battery", level)
        if config is None:
            raise ValueError('no configuration provided.')
        _cfg = config['kros'].get('hardware').get('battery')
        self._counter                    = itertools.count()
        # configuration ....................................
        self._enable_battery_messaging   = _cfg.get('enable_battery_messaging')
        self._enable_channel_a_messaging = _cfg.get('enable_channel_a_messaging')
        self._enable_channel_b_messaging = _cfg.get('enable_channel_b_messaging')
        _CHANNELS = ['in0/ref', 'in1/ref', 'in2/ref']
        self._battery_channel            = _CHANNELS[_cfg.get('battery_channel')]
        self._five_volt_a_channel        = _CHANNELS[_cfg.get('five_volt_a_channel')]
        self._five_volt_b_channel        = _CHANNELS[_cfg.get('five_volt_b_channel')]
        self._raw_battery_threshold      = _cfg.get('raw_battery_threshold')
        self._five_volt_threshold        = _cfg.get('low_5v_threshold')
        self._loop_delay_sec             = _cfg.get('loop_delay_sec')
        self._loop_delay_sec_div_10      = self._loop_delay_sec / 10
        self._log.info('battery check loop delay: {:>5.2f} sec'.format(self._loop_delay_sec))
        self._log.info('setting 5v regulator threshold to {:>5.2f}v'.format(self._five_volt_threshold))
        self._log.info("channel A from '{}'; channel B from '{}'; raw battery threshold to {:>5.2f}v from '{}'".format(\
                self._five_volt_a_channel, self._five_volt_b_channel, self._raw_battery_threshold, self._battery_channel))
        # configure ThunderBorg
#       try:
#           TB = ThunderBorg.ThunderBorg(Level.INFO)
#           TB.Init()
#           if not TB.foundChip:
#               boards = ThunderBorg.ScanForThunderBorg()
#               if len(boards) == 0:
#                   raise Exception('no thunderborg found, check you are attached.')
#               else:
#                   raise Exception('no ThunderBorg at address {:02x}, but we did find boards:'.format(TB.i2cAddress))
#           self._tb = TB
#       except Exception as e:
#           self._tb = None
#           self._log.error('unable to configure ThunderBorg: {}\n{}'.format(e, traceback.format_exc()))

        self._tb = None
        self._ads1015 = None
        self._message_bus = message_bus
        self._message_factory = message_factory
        self._battery_voltage       = 0.0
        self._regulator_a_voltage   = 0.0
        self._regulator_b_voltage   = 0.0
        try:
            from ads1015 import ADS1015
            self._ads1015 = ADS1015()
            self._ads1015.set_mode('single')
            self._ads1015.set_programmable_gain(2.048)
            self._ads1015.set_sample_rate(1600)
            self._reference = self._ads1015.get_reference_voltage()
            self._log.info('reference voltage: {:6.3f}v'.format(self._reference))
        except ImportError:
            self._log.error("This script requires the ads1015 module\nInstall with: pip3 install --user ads1015")
#           from lib.mock_ads1015 import ADS1015
#           sys.exit(1)
#           raise ModuleNotFoundError('This script requires the ads1015 module\nInstall with: pip3 install --user ads1015')
        except Exception as e:
            raise RuntimeError('error configuring AD converter: {}'.format(traceback.format_exc()))
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'BatteryCheck'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_enable_messaging(self, enable):
        '''
        If true we enable all battery and regulator messages to be sent.
        This overrides the configured values.
        '''
        if enable:
            self._log.info('enable battery check messaging.')
        else:
            self._log.info('disable battery check messaging.')
        self._enable_battery_messaging   = enable
        self._enable_channel_a_messaging = enable
        self._enable_channel_b_messaging = enable

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_raw_battery_threshold(self, threshold):
        self._log.info('set raw battery threshold to {:>5.2f}v'.format(threshold))
        self._raw_battery_threshold = threshold

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_five_volt_threshold(self, threshold):
        self._log.info('set five volt threshold to {:>5.2f}v'.format(threshold))
        self._five_volt_threshold = threshold

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_raw_battery_voltage(self):
        return self._battery_voltage

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_regulator_a_voltage(self):
        return self._regulator_a_voltage

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_regulator_b_voltage(self):
        return self._regulator_b_voltage

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _read_tb_voltage(self):
        '''
        Reads the ThunderBorg motor voltage, then displays a log message as
        well as setting the ThunderBorg RGB LED to indicate the value.

        Returns the read value.
        '''
        if self._tb:
            _tb_voltage = self._tb.GetBatteryReading()
            if _tb_voltage is None:
                _color = Color.MAGENTA # error color
            else:
                _color = BatteryCheck._get_color_for_voltage(_tb_voltage)
                if _color is Color.RED or _color is Color.ORANGE:
                    self._log.info(Fore.RED    + 'main battery: {:>5.2f}V'.format(_tb_voltage))
                elif _color is Color.AMBER or _color is Color.YELLOW:
                    self._log.info(Fore.YELLOW + 'main battery: {:>5.2f}V'.format(_tb_voltage))
                elif _color is Color.GREEN or _color is Color.TURQUOISE:
                    self._log.info(Fore.GREEN  + 'main battery: {:>5.2f}V'.format(_tb_voltage))
                elif _color is Color.CYAN:
                    self._log.info(Fore.CYAN   + 'main battery: {:>5.2f}V'.format(_tb_voltage))
            self._tb.SetLed1( _color.red, _color.green, _color.blue )
            return _tb_voltage
        else:
            return None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def _get_color_for_voltage(voltage):
        if ( voltage > 20.0 ):
            return Color.CYAN
        elif ( voltage > 19.0 ):
            return Color.TURQUOISE
        elif ( voltage > 18.8 ):
            return Color.GREEN
        elif ( voltage > 18.0 ):
            return Color.YELLOW
        elif ( voltage > 17.0 ):
            return Color.AMBER
        elif ( voltage > 16.0 ):
            return Color.ORANGE
        else:
            return Color.RED

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   @property
#   def count(self):
#       '''
#       Returns the count value of the last received message.
#       '''
#       return self._count

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if not self._ads1015:
                self._log.warning('cannot enable battery check: no ADC available.')
            elif self._message_bus.get_task_by_name(BatteryCheck._LISTENER_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                self._log.info('creating task for battery listener loop...')
                self._message_bus.loop.create_task(self._battery_listener_loop(lambda: self.enabled), name=BatteryCheck._LISTENER_LOOP_NAME)
                self._log.info('enabled.')
            # disable ThunderBorg RGB LED mode so we can set it
            if self._tb:
                self._tb.SetLedShowBattery(False)
            self._log.info('enabled.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _check_battery_voltage(self):
       '''
       Checks the battery voltage (default on channel 0), returning a message
       if the battery is low, otherwise None.
       '''
       self._log.info('❄️  checking battery voltage {:5.2f} against threshold {:5.2f}...'.format(self._battery_voltage, self._raw_battery_threshold))
       if self._battery_voltage < self._raw_battery_threshold:
           self._log.warning('battery low: {:>5.2f}v'.format(self._battery_voltage))
           if self._enable_battery_messaging:
               _message = self._message_factory.create_message(Event.BATTERY_LOW, 'battery low: {:5.2f}V'.format(self._battery_voltage))
               return _message
       else:
           return None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _check_channel_a(self):
       '''
       Checks the voltage on channel a (1), returning a message if below the
       configured threshold, otherwise None.
       '''
       self._log.info('❄️  checking channel a voltage {:5.2f} against threshold {:5.2f}...'.format(self._regulator_a_voltage, self._five_volt_threshold))
       if self._regulator_a_voltage < self._five_volt_threshold:
           self._log.warning('5V regulator A low:  {:>5.2f}v'.format(self._regulator_a_voltage))
           if self._enable_channel_a_messaging:
               _message = self._message_factory.create_message(Event.BATTERY_LOW, 'regulator A low: {:5.2f}V'.format(self._regulator_a_voltage))
               return _message
       else:
           return None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _check_channel_b(self):
       '''
       Checks the voltage on channel b (2), returning a message if below the
       configured threshold, otherwise None.
       '''
       self._log.info('❄️  checking channel b voltage {:5.2f} against threshold {:5.2f}...'.format(self._regulator_b_voltage, self._five_volt_threshold))
       if self._regulator_b_voltage < self._five_volt_threshold:
           self._log.warning('5V regulator B low:  {:>5.2f}v'.format(self._regulator_b_voltage))
           if self._enable_channel_b_messaging:
               _message = self._message_factory.create_message(Event.BATTERY_LOW, 'regulator B low: {:5.2f}V'.format(self._regulator_b_voltage))
               return _message
       else:
           return None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _battery_listener_loop(self, f_is_enabled):
        '''
        The function that checks the raw battery and 5v regulator voltages in
        a very slow loop. Note that this doesn't immediately send BATTERY_LOW
        messages until after the loop has run a few times, as it seems the
        first check after starting tends to measure a bit low.
        '''
        self._log.info('starting key listener loop:\t' + Fore.YELLOW + 'type \'?\' for help, \'q\' or Ctrl-C to exit.')
        try:
            while f_is_enabled():
                _count = next(self._counter)
#               if _count % 100 != 0: # process only every 100th loop
#                   return
                self._log.info('[{:03d}] battery check started...'.format(_count))

                self._battery_voltage = self._ads1015.get_compensated_voltage(channel=self._battery_channel, reference_voltage=self._reference)
                self._log.info(Fore.GREEN + 'battery channel: {}; reference: {:<5.2f}v; voltage: {:5.2f}v'.format(
                        self._battery_channel, self._reference, self._battery_voltage))

#               _motor_voltage = self._read_tb_voltage()
#               if self._battery_voltage is None or ( self._tb and _motor_voltage is None ):
#                   _motor_voltage = 0.0
#                   self._battery_voltage = 0.0
#                   self._log.warning('raw battery or thunderborg motor voltage is NA')
#               else:
#                   self._log.info(Fore.GREEN + 'raw battery voltage: {:<5.2f}v; thunderborg motor voltage: {:>5.2f}v'.format(
#                           self._battery_voltage, _motor_voltage))

                self._regulator_a_voltage = self._ads1015.get_compensated_voltage(channel=self._five_volt_a_channel, reference_voltage=self._reference)
                self._log.info(Fore.GREEN + 'five volt A channel {}: {:5.2f}V.'.format(self._five_volt_a_channel, self._regulator_a_voltage))

                self._regulator_b_voltage = self._ads1015.get_compensated_voltage(channel=self._five_volt_b_channel, reference_voltage=self._reference)
                self._log.info(Fore.GREEN + 'five volt B channel {}: {:5.2f}V.'.format(self._five_volt_b_channel, self._regulator_b_voltage))

                # publish message if exceeds threshold...
                _message = None
                if self._enable_battery_messaging:
                    _message = self._check_battery_voltage()
                if not _message and self._enable_channel_a_messaging:
                    _message = self._check_channel_a()
                if not _message and self._enable_channel_b_messaging:
                    _message = self._check_channel_b()
                if not _message:
                    self._log.info(Style.DIM + 'battery: {:>5.2f}v; regulator A: {:>5.2f}v; regulator B: {:>5.2f}v'.format(\
                            self._battery_voltage, self._regulator_a_voltage, self._regulator_b_voltage))

                if _message:
#                   _message = self._message_factory.create_message(_event, True)
                    self._log.info('battery-publishing message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.label))
                    await Publisher.publish(self, _message)
                    self._log.info('battery-published message:' + Fore.WHITE + ' {}.'.format(_message.name))
                else:
                    # nothing happening...
                    self._log.info('[{:03d}] waiting for battery event...'.format(_count))
                await asyncio.sleep(self._loop_delay_sec)

                self._log.info(Style.DIM + '[{:03d}] battery check ended.'.format(_count))

            self._log.info('publish loop complete.')
        finally:
            pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        if self.enabled:
            if self._tb:
                self._tb.SetLed1( Color.BLACK.red, Color.BLACK.green, Color.BLACK.blue )
                self._tb.SetLedShowBattery(True)
            Publisher.disable(self)
            self._log.info('disabled publisher.')

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   def close(self):
#       self.disable()
#       self._log.info('closed.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def clamp(n, minn, maxn):
        return max(min(maxn, n), minn)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def remap(x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Color(Enum):
    RED       = ( 0, 'red',       1.0, 0.0, 0.0 )
    ORANGE    = ( 1, 'amber',     0.6, 0.1, 0.0 )
    AMBER     = ( 2, 'orange',    0.8, 0.2, 0.0 )
    YELLOW    = ( 3, 'yellow',    0.9, 0.8, 0.0 )
    GREEN     = ( 4, 'green',     0.0, 1.0, 0.0 )
    TURQUOISE = ( 5, 'turquoise', 0.0, 1.0, 0.3 )
    CYAN      = ( 6, 'cyan',      0.0, 1.0, 1.0 )
    MAGENTA   = ( 7, 'magenta',   0.9, 0.0, 0.9 )
    BLACK     = ( 8, 'black',     0.0, 0.0, 0.0 )

    # ignore the first param since it's already set by __new__
    def __init__(self, num, name, red, green, blue):
        self._name = name
        self._red = red
        self._green = green
        self._blue = blue

    @property
    def name(self):
        return self._name

    @property
    def red(self):
        return self._red

    @property
    def green(self):
        return self._green

    @property
    def blue(self):
        return self._blue

#EOF
