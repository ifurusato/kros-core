#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-16
# modified: 2021-04-22
#

import asyncio
import random
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

import core.globals as globals
from core.logger import Logger, Level
from core.orient import Orientation
from core.event import Event, Group
from core.subscriber import Subscriber
from hardware.motor_controller import MotorController

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class BumperSubscriber(Subscriber):

    CLASS_NAME = 'bumper'

    '''
    A subscriber to bumper events.

    :param config:       the application configuration
    :param message_bus:  the message bus
    :param motor_ctrl:   the motor controller
    :param level:        the logging level
    '''
    def __init__(self, config, message_bus, motor_ctrl, level=Level.INFO):
        Subscriber.__init__(self, BumperSubscriber.CLASS_NAME, config, message_bus=message_bus, suppressed=False, enabled=False, level=level)
        if not isinstance(motor_ctrl, MotorController):
            raise ValueError('wrong type for motor_ctrl argument: {}'.format(type(motor_ctrl)))
        self._motor_ctrl = motor_ctrl
        _cfg = config['kros'].get('subscriber').get('bumper')
        self._shutdown_on_mast_event = _cfg.get('shutdown_on_mast_event')
        self.add_events(Event.by_group(Group.BUMPER))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _arbitrate_message(self, message):
        '''
        Pass the message on to the Arbitrator and acknowledge that it has been
        sent (by setting a flag in the message).
        '''
        await self._message_bus.arbitrate(message.payload)
        # increment sent acknowledgement count
        message.acknowledge_sent()
        self._log.info('arbitrated payload for event {}; value: {}'.format(message.payload.event.name, message.payload.value))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def process_message(self, message):
        '''
        Process the message.

        :param message:  the message to process.
        '''
        if self.enabled:
            if message.gcd:
                raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
            _event = message.event
            self._log.info('pre-processing message {}; '.format(message.name) + Fore.YELLOW + ' event: {}'.format(_event.label))

            if Event.is_bumper_event(_event):
                if _event is Event.BUMPER_MAST:
                    self._log.info(Fore.YELLOW + '😝 mast bumper triggered: backing up....')
                    self._motor_ctrl.astern_cm(5, 5)
                    if self._shutdown_on_mast_event:
                        self._log.info(Fore.YELLOW + '😝 mast bumper triggered: shutdown.')
                        _kros = globals.get('kros')
                        _kros.shutdown()

                elif _event is Event.BUMPER_PORT:
                    self._log.info(Fore.RED + 'BUMPER PORT.')
                    self._motor_ctrl.emergency_stop()
                    self._motor_ctrl.astern_cm(1, 10)

                elif _event is Event.BUMPER_CNTR:
                    self._log.info(Fore.BLUE + 'BUMPER CNTR.')
                    self._motor_ctrl.emergency_stop()
                    self._motor_ctrl.astern_cm(10, 10)

                elif _event is Event.BUMPER_STBD:
                    self._log.info(Fore.GREEN + 'BUMPER STBD.')
                    self._motor_ctrl.emergency_stop()
                    self._motor_ctrl.astern_cm(10, 1)

                elif _event is Event.BUMPER_PAFT:
                    self._log.info(Fore.RED + 'BUMPER PORT AFT.')
                    self._motor_ctrl.emergency_stop()

                elif _event is Event.BUMPER_SAFT:
                    self._log.info(Fore.GREEN + 'BUMPER STBD AFT.')
                    self._motor_ctrl.emergency_stop()

                else:
                    self._motor_ctrl.dispatch_bumper_event(message.payload)

            else:
                raise Exception('unrecognised bumper event on message {}'.format(message.name) + ''.format(message.event.label))

        else:
            self._log.warning('disabled: ignoring bumper dispatch.')

        await Subscriber.process_message(self, message)
        self._log.debug('post-processing message {}'.format(message.name))

#EOF
