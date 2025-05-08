#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2025-05-07
# modified: 2025-05-08
#

from colorama import init, Fore, Style
init()

from core.component import Component
from core.logger import Logger, Level
from core.orientation import Orientation
from hardware.distance_sensor import DistanceSensor

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class DistanceSensors(Component):
    '''
    Collects the three IR distance sensors into a class. This is a raw sensing
    class with no timing or integration into the rest of the operating system.
    It does support weighted averages of the center and port, and center and
    starboard sensors.

    :param config:            the application configuration
    :param level:             the log level
    '''
    def __init__(self, config, level=Level.INFO):
        if not isinstance(level, Level):
            raise ValueError('wrong type for log level argument: {}'.format(type(level)))
        self._level = level
        self._log = Logger('dists', level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        # configuration ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        if config is None:
            raise ValueError('no configuration provided.')
        _cfg = config['kros'].get('hardware').get('distance_sensors')
        self._reverse_curve    = _cfg.get('reverse', False)
        self._min_distance     = _cfg.get('min_distance', 80)
        self._default_distance = _cfg.get('max_distance', 300)
        # sensors ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        self._port_sensor = DistanceSensor(config, Orientation.PORT)
        self._cntr_sensor = DistanceSensor(config, Orientation.CNTR)
        self._stbd_sensor = DistanceSensor(config, Orientation.STBD)
        self._sensors = {
           Orientation.PORT: self._port_sensor,
           Orientation.CNTR: self._cntr_sensor,
           Orientation.STBD: self._stbd_sensor
        }
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        '''
        Enable the three sensors as well as this class.
        '''
        for _sensor in self._sensors.values():
            _sensor.enable()
        Component.enable(self)
        self._log.info('enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def sensors(self):
        '''
        Return the Orientation-keyed dictionary of sensors as a property.
        '''
        return self._sensors

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __getattr__(self, name):
        '''
        Access individual sensors via attributes, e.g.,

            _sensors = DistanceSensors(config)
            _port_sensor = _sensors.PORT
        '''
        if name in Orientation.__members__: # check if the name is a valid orientation
            orientation = Orientation[name]
            if hasattr(self, f"_{orientation.name.lower()}_sensor"):
                return getattr(self, f"_{orientation.name.lower()}_sensor")
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __iter__(self):
        '''
        Iterate over the sensors, permitting this construction:

            for _sensor in _sensors:
                distance_mm = _sensor.distance
        '''
        return iter(self._sensors.values())

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get(self, orientation: Orientation):
        '''
        Get method to retrieve the sensor by Orientation.
        '''
        return self._sensors.get(orientation, None)  # Returns the sensor or None if not found

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
        '''
        Read current distances or substitute default. This returns
        a tuple containing the port and starboard values.
        '''
        port = self._port_sensor.distance or self._default_distance
        cntr = self._cntr_sensor.distance or self._default_distance
        stbd = self._stbd_sensor.distance or self._default_distance
        # compute pairwise averages
        port_avg = (port + cntr) / 2
        stbd_avg = (stbd + cntr) / 2
        # normalize
        port_norm = DistanceSensors.normalize_distance(port_avg,
                min_dist=self._min_distance,
                max_dist=self._default_distance,
                reverse=self._reverse_curve)
        stbd_norm = DistanceSensors.normalize_distance(stbd_avg,
                min_dist=self._min_distance,
                max_dist=self._default_distance,
                reverse=self._reverse_curve)
        return (port_norm, stbd_norm)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        Disable the three sensors as well as this class.
        '''
        Component.disable(self)
        for _sensor in self._sensors.values():
            _sensor.disable()
        self._log.info('disabled.')

#EOF
