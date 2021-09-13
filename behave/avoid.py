#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-09-06
#
# TODO:
#  * Copy guts of Avoid to copy of Roam
#  * move Travel from MotorController to Avoid to replace as much ballistic behaviour as possible. Perhaps only backup.
#  * There needs to be a decision-making event where the robot chooses where to go to avoid obstacles, perhaps a LIDAR or ultrasonic scan.
#  * Integrate Travel into Avoid, and also re-use specific event types, with either timer or prescribed distance.
#

from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.event import Event, Group
from core.speed import Speed
from core.util import Util
from core.orient import Orientation
from behave.behaviour import Behaviour
from behave.trigger_behaviour import TriggerBehaviour
from hardware.motor_controller import MotorController

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Avoid(Behaviour):

    _LAMBDA_NAME = 'avoid'

    '''
    Implements an avoidance behaviour.

    The Behaviour subscribes to infrared and bumper events, and should
    an infrared event appear with a distance less than the minimum distance
    threshold we trigger one of the avoidance behaviours.

    The Avoid behaviour is by default suppressed.

    :param config:           the application configuration
    :param message_bus:      the asynchronous message bus
    :param message_factory:  the factory for messages
    :param motor_ctrl:       the motor controller
    :param exernal_clock:    the external clock
    :param suppressed:       suppressed state, default True
    :param enabled:          enabled state, default True
    :param level:            the optional log level
    '''
    def __init__(self, config, message_bus, message_factory, motor_ctrl, external_clock, suppressed=True, enabled=True, level=Level.INFO):
        Behaviour.__init__(self, 'avoid', config, message_bus, message_factory, suppressed=suppressed, enabled=enabled, level=level)
        if not isinstance(motor_ctrl, MotorController):
            raise ValueError('wrong type for motor_ctrl argument: {}'.format(type(motor_ctrl)))
        self._port_motor   = motor_ctrl.get_motor(Orientation.PORT)
        self._stbd_motor   = motor_ctrl.get_motor(Orientation.STBD)
        self._ext_clock    = external_clock
        if self._ext_clock:
            self._ext_clock.add_slow_callback(self._tick)
            pass
        else:
            raise Exception('unable to enable avoid behaviour: no external clock available.')
        _cfg = config['kros'].get('behaviour').get('avoid')
        self._min_distance  = _cfg.get('min_distance')
        self._log.info(Style.BRIGHT + 'minimum distance:\t{:4.2f}cm'.format(self._min_distance))
        self.add_events([ Group.BUMPER, Event.INFRARED_PORT, Event.INFRARED_STBD ])
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def execute(self, message):
        '''
        The method called by process_message(), upon receipt of a message.
        :param message:  an Message passed along by the message bus
        '''
        if self.suppressed:
            self._log.info(Style.DIM + 'avoid suppressed; message: {}'.format(message.event.label))
        elif self.enabled:
            self._log.info('🌓 avoid; message: {}'.format(message.event.label))
            pass # TODO

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _tick(self):
        '''
        This uses a leaky integrator to set a target forward velocity after
        waiting at least 3 seconds (configurable). The trigger occurs on the
        transition of the wait count from 1 to 0, so that at zero it won't
        continually auto-trigger.
        '''
        if not self.suppressed:
            self._log.info(Style.BRIGHT + '🌓 tick; suppressed: {};\t'.format(self.suppressed))
            pass

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_trigger_behaviour(self, event):
        return TriggerBehaviour.TOGGLE

    @property
    def trigger_event(self):
        '''
        This returns the event used to enable/disable the behaviour manually.
        '''
        return Event.AVOID

    def release(self):
        '''
        Releases (un-suppresses) this Component.
        '''
        Component.release(self)
        self._log.info(Fore.GREEN + '💚 avoid released.')

    def suppress(self):
        '''
        Suppresses this Component.
        '''
        Component.suppress(self)
        self._log.info(Fore.BLUE + '💙 avoid suppressed.')

    def disable(self):
        '''
        Disables this Component.
        '''
        Component.disable(self)
        self._log.info(Fore.BLUE + '💙 avoid disabled.')

#EOF
