#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2024-11-16
# modified: 2025-04-08
#

import time
import asyncio
from threading import Thread
from collections import deque
import pigpio
from colorama import init, Fore, Style
init()

import core.globals as globals
globals.init()

from core.logger import Logger, Level
from core.component import Component
from core.orientation import Orientation
from hardware.pigpiod_util import PigpiodUtility

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class DistanceSensor(Component):
    CLASS_NAME = 'dist'
    '''
    Provides distance information in millimeters from a Pololu PWM-based
    infrared proximity sensor.

    This can run either in a Thread or using the MessageBus (asyncio).

    :param config:       the application configuration
    :param orientation:  the orientation of the sensor, PORT, CNTR or STBD
    :param message_bus:  the optional message bus
    :param level:        the log level
    '''
    def __init__(self, config, orientation, message_bus=None, level=Level.INFO):
        '''
        Initializes the DistanceSensor.

        :param config:        the application configuration
        :param orientation:   the Orientation of the sensor
        :param level:         the logging Level
        '''
        self._log = Logger('dist:{}'.format(orientation.label), level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        if config is None:
            raise ValueError('no configuration provided.')
        _cfg = config['kros'].get('hardware').get('distance_sensor')
        match orientation:
            case Orientation.PORT:
                self._pin = _cfg.get('pin_port') # pin connected to the port sensor
            case Orientation.CNTR:
                self._pin = _cfg.get('pin_cntr') # pin connected to the center sensor
            case Orientation.STBD:
                self._pin = _cfg.get('pin_stbd') # pin connected to the starboard sensor
            case _:
                raise Exception('unexpected orientation: {}'.format(orientation.name))
        self._orientation = orientation
        self._task            = None
        self._task_name = '__{}-distance-sensor-loop'.format(self.orientation.name)
        self._timeout         = _cfg.get('timeout')     # time in seconds to consider sensor as timed out
        self._smoothing       = _cfg.get('smoothing') # enable smoothing of distance readings
        _smoothing_window     = _cfg.get('smoothing_window')
        self._window = deque(maxlen=_smoothing_window) if self._smoothing else None
        self._loop_interval   = _cfg.get('loop_interval') # interval between distance polling, in seconds
        self._pulse_start     = None
        self._pulse_width_us  = None
        self._distance        = -1
        self._running         = False
        self._pi              = None
        self._callback        = None
        self._use_message_bus = False
        if orientation is Orientation.PORT:
            self._log.info(Fore.RED + '{} distance sensor ready on pin {}.'.format(orientation.label, self._pin))
        elif orientation is Orientation.CNTR:
            self._log.info(Fore.BLUE + '{} distance sensor ready on pin {}.'.format(orientation.label, self._pin))
        elif orientation is Orientation.STBD:
            self._log.info(Fore.GREEN + '{} distance sensor ready on pin {}.'.format(orientation.label, self._pin))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _ensure_pigpio(self):
        '''
        Make sure that pigpio is running.
        '''
        PigpiodUtility.ensure_pigpiod_is_running()
        self._pi = pigpio.pi()
        if not self._pi.connected:
            raise Exception("Failed to connect to pigpio daemon")
        self._pi.set_mode(self._pin, pigpio.INPUT)
        self._callback = self._pi.callback(self._pin, pigpio.EITHER_EDGE, self._pulse_callback)
        self._last_read_time = time.time()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return self._orientation.name

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def orientation(self):
        return self._orientation

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _pulse_callback(self, gpio, level, tick):
        '''
        Callback function to measure PWM pulse width.
        '''
        if level == 1:   # rising edge
            self._pulse_start = tick
        elif level == 0: # falling edge
            if self._pulse_start is not None:
                self._pulse_width_us = pigpio.tickDiff(self._pulse_start, tick)
            else:
                self._pulse_width_us = None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _compute_distance(self):
        '''
        Compute and update the distance based on the current pulse width,
        returning the distance or None if out of range.
        '''
        _pulse_width_us = self._pulse_width_us # capture current value
        _distance = None
        if _pulse_width_us is not None:
            if 1000 <= _pulse_width_us <= 1850:
                distance_mm = (_pulse_width_us - 1000) * 3 / 4
                self._last_read_time = time.time()
                if self._smoothing:
                    self._window.append(distance_mm)
                    _distance = int(sum(self._window) / len(self._window))
                else:
                    _distance = int(distance_mm)
            self._pulse_width_us = None # reset after processing
        return _distance

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def distance(self):
        '''
        Get the latest computed distance as a property.
        '''
        return self._distance

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def check_timeout(self):
        '''
        Check if the sensor has timed out (no pulse received recently).
        '''
        return time.time() - self._last_read_time > self._timeout

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _async_sensor_loop(self):
        '''
        Asynchronous loop to continuously compute distances.
        '''
        while self._running:
            self._distance = self._compute_distance()
            await asyncio.sleep(self._loop_interval)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _sensor_loop(self):
        '''
        Loop to continuously compute distances. This is used when the
        asyncio message bus is active.
        '''
        while self._running:
            self._distance = self._compute_distance()
            time.sleep(self._loop_interval)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def stop(self):
        '''
        Stop the sensor's asynchronous loop and clean up resources.
        '''
        self._running = False
        if self._task is not None:
            self._task.cancel()
        if self._callback:
            self._callback.cancel()
        if self._pi:
            self._pi.stop()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Component.enable(self)
        if self.enabled:
            self._ensure_pigpio()
            if self._use_message_bus:
                _component_registry = globals.get('component-registry')
                _message_bus = _component_registry.get('bus')
                if _message_bus is None:
                    raise Exception('no message bus available.')
                elif _message_bus.get_task_by_name(self._task_name):
                    self._log.warning('already enabled.')
                self._running = True
                self._task = asyncio.create_task(self._async_sensor_loop(), name=self._task_name)
            else:
                self._running = True
                self._thread = Thread(name='sensor-loop', target=self._sensor_loop)
                self._thread.start()
        else:
            self._log.warning('failed to enable distance sensor.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        self.stop()
        Component.disable(self)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        '''
        Stop the loop if running, then close the sensor.
        '''
        Component.close(self) # calls disable

#EOF
