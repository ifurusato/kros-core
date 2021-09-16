#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-01-18
# modified: 2020-10-28
#

from collections import deque as Deque
from colorama import init, Fore, Style
init()

import core.globals as globals
from core.config_loader import ConfigLoader
from core.logger import Logger, Level
from core.orient import Orientation
from core.component import Component
from core.event import Event
from core.message import Message
from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from hardware.io_expander import IoExpander
from hardware.analog_pot import AnalogPotentiometer # for calibration only
from hardware.digital_pot import DigitalPotentiometer # for calibration only

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class IntegratedFrontSensor(Component):
    '''
    The IntegratedFrontSensor: communicates with the integrated front bumpers
    and infrared sensors, receiving messages via the IO Expander board or I²C
    Arduino slave, sending the messages with its events onto the message bus.
    For analog sensors the values are contained within the Payload of the
    Message.

    This polls the values of the IO Expander's pins, which outputs 0-255 values
    for analog pins, and a 0 or 1 for digital pins.

    Configuration ......................

    The analog infrared values are returned as distances in centimeters, with
    the calibration done using either an analog or digital potentiometer. This
    uses both a 'conversion exponent' and a 'fudge factor' from the YAML
    configuration. Due to the non-linear response from the Sharp IR sensors
    this compromise is weighted towards closer range measurement, as accuracy
    at greater distances is less important than close to the robot.

    Note that the initial state for this class is disabled and suppressed.

    :param config:            the YAML based application configuration
    :param message_bus:       the asynchronous message bus
    :param message_factory:   the factory for creating messages
    :param level:             the logging Level
    '''
    def __init__(self, config, message_bus, message_factory, suppressed=True, enabled=False, level=Level.INFO):
        if not isinstance(level, Level):
            raise ValueError('wrong type for log level argument: {}'.format(type(level)))
        self._log = Logger("ifs", level)
        Component.__init__(self, self._log, suppressed, enabled)
        if config is None:
            raise ValueError('no configuration provided.')
        self._message_bus = message_bus
        self._message_factory = message_factory
        self._log.info('configuring integrated front sensor...')
        self._config = config['kros'].get('integrated_front_sensor')
        self._ignore_duplicates        = self._config.get('ignore_duplicates')
        _cfg = [ 0, 330, 0.0, 2.0 ]
        self._analog_pot = AnalogPotentiometer(config, in_min=_cfg[0], in_max=_cfg[1], out_min=_cfg[2], out_max=_cfg[3], level=Level.INFO) \
                if self._config.get('use_analog_potentiometer') \
                else None
        if self._analog_pot:
            self._log.info(Fore.YELLOW + 'using analog potentiometer for calibration.')
        self._digital_pot = DigitalPotentiometer(config, Level.INFO) \
                if self._config.get('use_digital_potentiometer') \
                else None
        if self._digital_pot:
            self._log.info(Fore.YELLOW + 'using digital potentiometer for calibration.')
        self._conversion_exponent      = self._config.get('conversion_exponent') # 1.27, 1.33
        self._fudge_factor             = self._config.get('fudge_factor') # can be zero
        # event thresholds:
        self._cntr_raw_min_trigger     = self._config.get('cntr_raw_min_trigger')
        self._oblq_raw_min_trigger     = self._config.get('oblq_raw_min_trigger')
        self._side_raw_min_trigger     = self._config.get('side_raw_min_trigger')
        self._cntr_trigger_distance_cm = self._config.get('cntr_trigger_distance_cm')
        self._oblq_trigger_distance_cm = self._config.get('oblq_trigger_distance_cm')
        self._side_trigger_distance_cm = self._config.get('side_trigger_distance_cm')
        self._log.info('event thresholds:    \t' \
                + Fore.RED   + ' port side={:>5.2f}; port={:>5.2f};'.format(self._side_trigger_distance_cm, self._oblq_trigger_distance_cm) \
                + Fore.BLUE  + ' center={:>5.2f};'.format(self._cntr_trigger_distance_cm) \
                + Fore.GREEN + ' stbd={:>5.2f}; stbd side={:>5.2f}'.format(self._oblq_trigger_distance_cm, self._side_trigger_distance_cm))
        # hardware pin assignments are defined in IO Expander
        # create/configure IO Expander
        self._io_expander = IoExpander(config, Level.INFO)
        # these are used to support running averages
        _queue_limit = 2 # larger number means it takes longer to change
        self._deque_cntr      = Deque([], maxlen=_queue_limit)
        self._deque_port      = Deque([], maxlen=_queue_limit)
        self._deque_stbd      = Deque([], maxlen=_queue_limit)
        self._deque_port_side = Deque([], maxlen=_queue_limit)
        self._deque_stbd_side = Deque([], maxlen=_queue_limit)
        self._cntr_count      = 0
        self._port_count      = 0
        self._stbd_count      = 0
        self._port_side_count = 0
        self._stbd_side_count = 0
        globals.put('ifs', self)
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def name(self):
        return 'ifs'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_info(self):

        return 'ifs: {}; ioe: {}; psid: {:d}; port: {:d}; cntr: {:d}; stbd: {:d}; ssid: {:d}'.format(\
                self.is_active, self._io_expander.is_active,
                self._cntr_count, self._port_count, self._stbd_count, self._port_side_count, self._stbd_side_count)
#               len(self._deque_port_side), len(self._deque_port), len(self._deque_cntr), len(self._deque_stbd), len(self._deque_stbd_side))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def poll_port_bumper(self):
        '''
        Polls the port bumper, returning True if triggered.
        '''
        return self.is_active and self._io_expander.get_raw_port_bmp_value() == 0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def poll_cntr_bumper(self):
        '''
        Polls the center bumper, returning True if triggered.
        '''
        return self.is_active and self._io_expander.get_raw_cntr_bmp_value() == 0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def poll_stbd_bumper(self):
        '''
        Polls the starboard bumper, returning True if triggered.
        '''
        return self.is_active and self._io_expander.get_raw_stbd_bmp_value() == 0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    # Group 0: the bumpers
    def poll_bumpers(self):
        '''
        Polls the port, center and starboard bumpers, returning a tuple
        containing each value or None if not triggered.

        Bumpers are not normally polled as a group as that's too slow;
        callbacks directly attached to the poll methods are more suitable.
        '''
        if not self.is_active:
            return None

        _port_bmp_message = None
        _cntr_bmp_message = None
        _stbd_bmp_message = None

        # port bumper sensor ...........................
        if self.poll_port_bumper():
            self._log.info(Fore.RED + 'adding new message for BUMPER_PORT event.')
            _port_bmp_message = self._message_factory.create_message(Event.BUMPER_PORT, True)

        # center bumper sensor .........................
        if self.poll_cntr_bumper():
            self._log.info(Fore.BLUE + 'adding new message for BUMPER_CNTR event.')
            _cntr_bmp_message = self._message_factory.create_message(Event.BUMPER_CNTR, True)

        # stbd bumper sensor ...........................
        if self.poll_stbd_bumper():
            self._log.info(Fore.GREEN + 'adding new message for BUMPER_STBD event.')
            _stbd_bmp_message = self._message_factory.create_message(Event.BUMPER_STBD, True)

        return [_port_bmp_message, _cntr_bmp_message, _stbd_bmp_message] if _port_bmp_message or _cntr_bmp_message or _stbd_bmp_message else None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    # Group 1: the center infrared sensor
    def poll_cntr_infrared(self):
        '''
        Polls the center infrared sensor, returning the value or None if nothing
        is within range.
        '''
        if self.is_active and self._io_expander.is_active:
            self._cntr_count += 1
            _cntr_ir_data = self._io_expander.get_cntr_ir_value()
            if _cntr_ir_data > self._cntr_raw_min_trigger:
#               self._log.info(Fore.BLUE + 'ANALOG IR CENTER:\t' + (Fore.RED if (_cntr_ir_data > 100.0) else Fore.YELLOW)
#                       + Style.BRIGHT + '{:d} exceeds trigger of {:d}'.format(_cntr_ir_data, self._cntr_raw_min_trigger)
#                       + Style.DIM + '\t(analog value 0-255)')
                _value = self._get_mean_distance(Orientation.CNTR, self.convert_to_distance(_cntr_ir_data))
                if _value != None and _value < self._cntr_trigger_distance_cm:
#                   self._log.info(Fore.BLUE + Style.NORMAL + 'CNTR\tmean distance:\t{:5.2f}/{:5.2f}cm'.format(\
#                           _value, self._cntr_trigger_distance_cm) + Style.DIM + '; raw: {:d}'.format(_cntr_ir_data))
                    _message = self._message_factory.create_message(Event.INFRARED_CNTR, _value)
#                   self._log.info('created message for event: {}; value: {:5.2f}'.format(_message.event, _message.value))
                    return _message
        return None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    # Group 2: the oblique infrared sensors
    def poll_oblique_infrared(self):
        '''
        Polls the port and starboard oblique infrared sensors, returning a tuple
        containing the results, where None means no value.
        '''
        if not self.is_active:
            return None
        _port_ir_message = None
        _stbd_ir_message = None
        # port analog infrared sensor ......................
        _port_ir_data      = self._io_expander.get_port_ir_value()
        if _port_ir_data > self._oblq_raw_min_trigger:
            self._port_count += 1
            self._log.info('ANALOG IR OBLIQUE:\t' + (Fore.RED if (_port_ir_data > 100.0) else Fore.YELLOW) \
                    + Style.BRIGHT + '{:d}'.format(_port_ir_data) + Style.DIM + '\t(analog value 0-255)')
            _value = self._get_mean_distance(Orientation.PORT, self.convert_to_distance(_port_ir_data))
            if _value != None and _value < self._oblq_trigger_distance_cm:
                self._log.info(Fore.RED + Style.DIM + 'PORT     \tmean distance:\t{:5.2f}/{:5.2f}cm'.format(\
                        _value, self._oblq_trigger_distance_cm) + Style.DIM + '; raw: {:d}'.format(_port_ir_data))
                _port_ir_message = self._message_factory.create_message(Event.INFRARED_PORT, _value)
        # starboard analog infrared sensor .................
        _stbd_ir_data      = self._io_expander.get_stbd_ir_value()
        if _stbd_ir_data > self._oblq_raw_min_trigger:
            self._stbd_count += 1
            self._log.info('ANALOG IR OBLIQUE:\t' + (Fore.RED if (_stbd_ir_data > 100.0) else Fore.YELLOW) \
                    + Style.BRIGHT + '{:d}'.format(_stbd_ir_data) + Style.DIM + '\t(analog value 0-255)')
            _value = self._get_mean_distance(Orientation.STBD, self.convert_to_distance(_stbd_ir_data))
            if _value != None and _value < self._oblq_trigger_distance_cm:
                self._log.info(Fore.GREEN + Style.DIM + 'STBD     \tmean distance:\t{:5.2f}/{:5.2f}cm'.format(\
                        _value, self._oblq_trigger_distance_cm) + Style.DIM + '; raw: {:d}'.format(_stbd_ir_data))
                _stbd_ir_message = self._message_factory.create_message(Event.INFRARED_STBD, _value)
        return [_port_ir_message, _stbd_ir_message]

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    # Group 3: the side infrared sensors
    def poll_side_infrared(self):
        if not self.is_active:
            return None
        # port side analog infrared sensor .................
        _port_side_ir_data = self._io_expander.get_port_side_ir_value()
        if _port_side_ir_data > self._side_raw_min_trigger:
            self._port_side_count += 1
            self._log.info(Fore.RED + 'ANALOG IR SIDE:\t' + (Fore.RED if (_port_side_ir_data > 100.0) else Fore.YELLOW) \
                    + Style.BRIGHT + '{:d}'.format(_port_side_ir_data) + Style.DIM + '\t(analog value 0-255)')
            _value = self._get_mean_distance(Orientation.PSID, self.convert_to_distance(_port_side_ir_data))
            if _value != None and _value < self._side_trigger_distance_cm:
                self._log.info(Fore.RED + Style.DIM + 'PSID\tmean distance:\t{:5.2f}/{:5.2f}cm'.format(\
                        _value, self._side_trigger_distance_cm) + Style.DIM + '; raw: {:d}'.format(_port_side_ir_data))
                _port_side_ir_message = self._message_factory.create_message(Event.INFRARED_PSID, _value)
        else:
            _port_side_ir_message = None
        # starboard side analog infrared sensor ............
        _stbd_side_ir_data = self._io_expander.get_stbd_side_ir_value()
        if _stbd_side_ir_data > self._side_raw_min_trigger:
            self._stbd_side_count += 1
            self._log.info('ANALOG IR SIDE:\t' + (Fore.RED if (_stbd_side_ir_data > 100.0) else Fore.YELLOW) \
                    + Style.BRIGHT + '{:d}'.format(_stbd_side_ir_data) + Style.DIM + '\t(analog value 0-255)')
            _value = self._get_mean_distance(Orientation.SSID, self.convert_to_distance(_stbd_side_ir_data))
            if _value != None and _value < self._side_trigger_distance_cm:
                self._log.info(Fore.GREEN + Style.DIM + 'SSID\tmean distance:\t{:5.2f}/{:5.2f}cm'.format(\
                        _value, self._side_trigger_distance_cm) + Style.DIM + '; raw: {:d}'.format(_stbd_side_ir_data))
                _stbd_side_ir_message = self._message_factory.create_message(Event.INFRARED_SSID, _value)
        else:
            _stbd_side_ir_message = None
        return [_port_side_ir_message, _stbd_side_ir_message]

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_mean_distance(self, orientation, value):
        '''
        Returns the mean of values collected in the queue for the specified IR sensor.
        '''
        if value == None or value == 0:
            return None
        if orientation is Orientation.CNTR:
            _deque = self._deque_cntr
        elif orientation is Orientation.PORT:
            _deque = self._deque_port
        elif orientation is Orientation.STBD:
            _deque = self._deque_stbd
        elif orientation is Orientation.PSID:
            _deque = self._deque_port_side
        elif orientation is Orientation.SSID:
            _deque = self._deque_stbd_side
        else:
            raise ValueError('unsupported orientation.')
        _deque.append(value)
        _n = 0
        _mean = 0.0
        for x in _deque:
            _n += 1
            _mean += ( x - _mean ) / _n
        if _n < 1:
            return float('nan');
        else:
            return _mean

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def convert_to_distance(self, value):
        '''
        Converts the value returned by the IR sensor to a distance in centimeters.

        Distance Calculation ---------------

        This is reading the distance from a 3 volt Sharp GP2Y0A60SZLF infrared
        sensor to a piece of white A4 printer paper in a low ambient light room.
        The sensor output is not linear, but its accuracy is not critical. If
        the target is too close to the sensor the values are not valid. According
        to spec 10cm is the minimum distance, but we get relative variability up
        until about 5cm. Values over 150 clearly indicate the robot is less than
        10cm from the target. Here's a sampled output:

            0cm = unreliable
            5cm = 226.5
          7.5cm = 197.0
           10cm = 151.0
           20cm =  92.0
           30cm =  69.9
           40cm =  59.2
           50cm =  52.0
           60cm =  46.0
           70cm =  41.8
           80cm =  38.2
           90cm =  35.8
          100cm =  34.0
          110cm =  32.9
          120cm =  31.7
          130cm =  30.7 *
          140cm =  30.7 *
          150cm =  29.4 *

        * Maximum range on IR is about 130cm, after which there is diminishing
          stability/variability, i.e., it's hard to determine if we're dealing
          with a level of system noise rather than data. Different runs produce
          different results, with values between 28 - 31 on a range of any more
          than 130cm.

        See: http://ediy.com.my/blog/item/92-sharp-gp2y0a21-ir-distance-sensors
        '''
        if value == None or value == 0:
            return None

        if self._analog_pot:
            _EXPONENT = self._analog_pot.get_scaled_value()
        elif self._digital_pot:
            _EXPONENT = self._digital_pot.get_scaled_value(True)
        else:
            _EXPONENT = self._conversion_exponent # 1.27, 1.33
        _NUMERATOR = 1000.0
        _distance = pow( _NUMERATOR / value, _EXPONENT ) + self._fudge_factor
        if self._analog_pot:
            self._log.debug(Fore.CYAN + 'value: {:>5.2f}; analog pot value: {:>5.2f}; '.format(value, _EXPONENT) + Fore.YELLOW + 'distance: {:>5.2f}cm'.format(_distance))
        elif self._digital_pot:
            self._log.debug(Fore.CYAN + 'value: {:>5.2f}; digital pot value: {:>5.2f}; '.format(value, _EXPONENT) + Fore.YELLOW + 'distance: {:>5.2f}cm'.format(_distance))
        return _distance

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        '''
        Enable this Component.
        '''
        Component.enable(self)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def suppress(self):
        '''
        Suppresses this Component.
        '''
        Component.suppress(self)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def release(self):
        '''
        Releases (un-suppresses) this Component.
        '''
        Component.release(self)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this Component.
        This returns a True value to force currency.
        '''
        Component.disable(self)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        '''
        Close the IoExpander and release any resources.
        '''
        if not self.closed:
            if self._digital_pot:
                self._digital_pot.close()
            Component.close(self)

# EOF
