#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2025-05-08
#

import asyncio
from colorama import init, Fore, Style
init()

import core.globals as globals
globals.init()

from core.logger import Logger, Level
from core.event import Event
from core.orientation import Orientation
from core.message_factory import MessageFactory
from core.publisher import Publisher
from hardware.distance_sensors import DistanceSensors

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class DistanceSensorsPublisher(Publisher):
    CLASS_NAME = 'distance'
    _LISTENER_LOOP_NAME = '__distance-sensors-loop'
    '''
    A publisher for events from a trio of DistanceSensors.

    :param config:            the application configuration
    :param message_bus:       the asynchronous message bus
    :param message_factory:   the factory for creating messages
    :param distance_sensors:  the optional DistanceSensors object (will create if not provided)
    :param level:             the log level
    '''
    def __init__(self, config, message_bus, message_factory, distance_sensors=None, level=Level.INFO):
        if not isinstance(level, Level):
            raise ValueError('wrong type for log level argument: {}'.format(type(level)))
        self._level = level
        Publisher.__init__(self, DistanceSensorsPublisher.CLASS_NAME, config, message_bus, message_factory, level=self._level)
        # configuration ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        if config is None:
            raise ValueError('no configuration provided.')
        _cfg = config['kros'].get('publisher').get('distance_sensors')
        _loop_freq_hz          = _cfg.get('loop_freq_hz')
        self._publish_delay_sec = 1.0 / _loop_freq_hz
        self._sense_threshold  = _cfg.get('sense_threshold')
        self._bump_threshold   = _cfg.get('bump_threshold')
        self._exit_on_cancel   = True # FIXME
        # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._reverse_curve    = False # reverse normalisation curve
        self._default_distance = 300   # max sensor range in mm
        self._min_distance     = 80    # minimum distance for scaling
        # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        if distance_sensors:
            self._sensors = distance_sensors
        else:
            self._sensors = DistanceSensors(config)
        self._port_sensor = self._sensors.get(Orientation.PORT)
        self._cntr_sensor = self._sensors.get(Orientation.CNTR)
        self._stbd_sensor = self._sensors.get(Orientation.STBD)
        self._verbose = False
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if self.message_bus.get_task_by_name(DistanceSensorsPublisher._LISTENER_LOOP_NAME):
                self._log.warning('already enabled.')
            else:
                self._log.info('creating task for distance sensor listener loop…')
                self.message_bus.loop.create_task(self._dist_listener_loop(lambda: self.enabled), name=DistanceSensorsPublisher._LISTENER_LOOP_NAME)
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable publisher.')

    # weighted averages support ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @staticmethod
    def normalize_distance(dist, min_dist=80, max_dist=300, reverse=False):
        '''
        Normalize distance to a value between 0.0 and 1.0 (or reversed),
        using quadratic easing.
        
        - reverse=False: 1.0 at max_dist, 0.0 at min_dist (default behavior)
        - reverse=True:  0.0 at max_dist, 1.0 at min_dist (flipped)
        '''
        dist = max(min(dist, max_dist), min_dist)
        normalized = (dist - min_dist) / (max_dist - min_dist)
        value = normalized ** 2  # Quadratic easing
        return 1.0 - value if reverse else value

    def get_weighted_averages(self):
        # read current distances or substitute default
        port = self._port_sensor.distance or self._default_distance
        cntr = self._cntr_sensor.distance or self._default_distance
        stbd = self._stbd_sensor.distance or self._default_distance
        # compute pairwise averages
        port_avg = (port + cntr) / 2
        stbd_avg = (stbd + cntr) / 2
        # normalize
        port_norm = normalize_distance(port_avg,
                min_dist=self._min_distance,
                max_dist=self._default_distance,
                reverse=self._reverse_curve)
        stbd_norm = normalize_distance(stbd_avg,
                min_dist=self._min_distance,
                max_dist=self._default_distance,
                reverse=self._reverse_curve)
        return (port_norm, stbd_norm)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_bumper_event(self, orientation):
        match orientation:
            case Orientation.PORT:
                return Event.BUMPER_PORT 
            case Orientation.CNTR:
                return Event.BUMPER_CNTR 
            case Orientation.STBD:
                return Event.BUMPER_STBD 

    def _get_infrared_event(self, orientation):
        match orientation:
            case Orientation.PORT:
                return Event.INFRARED_PORT
            case Orientation.CNTR:
                return Event.INFRARED_CNTR 
            case Orientation.STBD:
                return Event.INFRARED_STBD  

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _dist_listener_loop(self, f_is_enabled):
        self._log.info('starting distance sensor listener loop.')
        _exit_flag = False
        try:
            # enable all sensors
            for _sensor in self._sensors:
                _sensor.enable()
            while f_is_enabled():
                for _sensor in self._sensors:
                    _distance_mm = _sensor.distance
                    if _distance_mm is not None:
                        if _distance_mm < self._bump_threshold:
                            if self._verbose:
                                self._log.info(Fore.WHITE + Style.BRIGHT + "bumper:   {:<10} {:>10.1f}mm".format(_sensor.orientation.name, _distance_mm))
                            _message = self.message_factory.create_message(self._get_bumper_event(_sensor.orientation), (_distance_mm))
                            await Publisher.publish(self, _message)
                        elif _distance_mm < self._sense_threshold:
                            if self._verbose:
                                self._log.info(Fore.WHITE + "infrared: {:<10} {:>10.1f}mm".format(_sensor.orientation.name, _distance_mm))
                            _message = self.message_factory.create_message(self._get_infrared_event(_sensor.orientation), (_distance_mm))
                            await Publisher.publish(self, _message)
                await asyncio.sleep(self._publish_delay_sec)
        except asyncio.CancelledError:
            self._log.info('closing kros from Ctrl-C…')
            if self._exit_on_cancel:
                _exit_flag = True
        finally:
            for _sensor in self._sensors:
                _sensor.stop()
            if _exit_flag:
                _component_registry = globals.get('component-registry')
                _kros = _component_registry.get('kros')
                _kros.shutdown()

        self._log.info('distance sensors publish loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable this publisher.
        '''
        Publisher.disable(self)

#EOF
