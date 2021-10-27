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
globals.init()

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

    This is currently acting as a Behaviour, publishing AVOID events back to
    the MessageBus via the QueuePublisher.

    :param config:           the application configuration
    :param message_bus:      the message bus
    :param message_factory:  the message factory
    :param motor_ctrl:       the motor controller
    :param level:            the logging level
    '''
    def __init__(self, config, message_bus, message_factory, motor_ctrl, level=Level.INFO):
        Subscriber.__init__(self, BumperSubscriber.CLASS_NAME, config, message_bus=message_bus, suppressed=False, enabled=False, level=level)
        if not isinstance(motor_ctrl, MotorController):
            raise ValueError('wrong type for motor_ctrl argument: {}'.format(type(motor_ctrl)))
        self._message_factory = message_factory
        self._motor_ctrl      = motor_ctrl
        self._behaviour_mgr   = None

        _cfg = config['kros'].get('subscriber').get('bumper')
        self._shutdown_on_mast_event = _cfg.get('shutdown_on_mast_event')

        self._queue_publisher = globals.get('queue-publisher')
        if self._queue_publisher:
            self._log.info('using queue publisher.')
        else:
            raise Exception('cannot continue: no queue publisher available.')
        self.add_events(Event.by_group(Group.BUMPER))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Subscriber.enable(self)
        if self.enabled:
            self._log.warning('already enabled.')
        else:
            if not self._behaviour_mgr: # attach behaviour manager if available
                _kros = globals.get('kros')
                self._behaviour_mgr = _kros.get_behaviour_manager() if _kros != None else None
            self._log.info('enabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _suppress_behaviours(self):
        if self._behaviour_mgr:
            self._behaviour_mgr.suppress_all_behaviours()
            self._log.info('all behaviours suppressed.')
        else:
            self._log.warning('no behaviour manager available: cannot suppress behaviours.')

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
    def get_current_target_velocities(self):
        '''
        Return a tuple containing the current target velocities of the port
        and starboard motors.
        '''
        _port_target_velocity = self._motor_ctrl.get_motor(Orientation.PORT).target_velocity
        _stbd_target_velocity = self._motor_ctrl.get_motor(Orientation.STBD).target_velocity
        return ( _port_target_velocity, _stbd_target_velocity )

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def process_message(self, message):
        '''
        Process the message. This gets a bit programmatic, as we here define
        which behaviours will get triggered upon certain events. This relies
        upon checking which direction the motors are currently moving.

        :param message:  the message to process.
        '''
        if self.enabled:
            if message.gcd:
                raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
            _event = message.event
            if not self._motor_ctrl.is_in_motion:
                self._log.info(Fore.YELLOW + '😝 {} triggered but robot does not appear to be moving.'.format(_event.label))
            elif Event.is_bumper_event(_event):
                _velocities = self.get_current_target_velocities()
                if _event is Event.BUMPER_MAST:
                    self.respond_to_mast_bumper_event()
                elif _event is Event.BUMPER_PORT:
                    self.respond_to_port_bumper_event(_velocities)
                elif _event is Event.BUMPER_CNTR:
                    self.respond_to_cntr_bumper_event(_velocities)
                elif _event is Event.BUMPER_STBD:
                    self.respond_to_stbd_bumper_event(_velocities)
                elif _event is Event.BUMPER_PAFT:
                    self.respond_to_paft_bumper_event()
                elif _event is Event.BUMPER_SAFT:
                    self.respond_to_saft_bumper_event()
                else:
                    raise Exception('unrecognised bumper event on message {}; '.format(message.name) + '{}'.format(message.event.label))
            else:
                # we shouldn't be seeing non-bumper events here
                self._log.warning('unexpected event on message {}; '.format(message.name) + '{}'.format(message.event.label))
        else:
            self._log.warning('disabled: ignoring bumper dispatch.')

        await Subscriber.process_message(self, message)
#       self._log.info('post-processing message {}'.format(message.name))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def respond_to_port_bumper_event(self, velocities):
        '''
        Respond to a port bumper event by first an emergency stop, and then
        if the robot is actually moving forward, publishing an AVOID message.
        '''
        if self._motor_ctrl.is_moving_ahead:
            self._log.info(Fore.RED + '😝 responding to port bumper: emergency stop...')
#           self._motor_ctrl.stop()
#           self._queue_publisher.put(self._message_factory.create_message(Event.AVOID, Orientation.PORT))
            self._queue_publisher.put(self._message_factory.create_message(Event.AVOID, ( Orientation.PORT, velocities )))
        else:
            self._log.warning('😝 PORT bumper triggered but robot does not appear to be moving forward.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def respond_to_cntr_bumper_event(self, velocities):
        '''
        Respond to a center bumper event by first an emergency stop, and then
        if the robot is actually moving forward, publishing an AVOID message.
        '''
        if self._motor_ctrl.is_moving_ahead:
            self._log.info(Fore.BLUE + '😝 responding to CNTR bumper: emergency stop...')
            # capture current target velocities and include in message payload
#           self._motor_ctrl.stop()
#           self._queue_publisher.put(self._message_factory.create_message(Event.AVOID, velocities))
            self._queue_publisher.put(self._message_factory.create_message(Event.AVOID, ( Orientation.CNTR, velocities )))
        else:
            self._log.warning('😝 CNTR bumper triggered but robot does not appear to be moving forward.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def respond_to_stbd_bumper_event(self, velocities):
        '''
        Respond to a starboard bumper event by first an emergency stop, and then
        if the robot is actually moving forward, publishing an AVOID message.
        '''
        if self._motor_ctrl.is_moving_ahead:
            self._log.info(Fore.GREEN + '😝 responding to STBD bumper: emergency stop...')
#           self._motor_ctrl.stop()
#           self._queue_publisher.put(self._message_factory.create_message(Event.AVOID, Orientation.STBD))
            self._queue_publisher.put(self._message_factory.create_message(Event.AVOID, ( Orientation.STBD, velocities )))
        else:
            self._log.warning('😝 CNTR bumper triggered but robot does not appear to be moving forward.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def respond_to_mast_bumper_event(self):
        '''
        Respond to a mast bumper event by first an emergency stop, then if the
        robot is moving forward and thusly configured, an emergency robot
        shutdown, otherwise publishing an AVOID message.
        '''
        if self._motor_ctrl.is_moving_ahead:
            self._log.info(Fore.YELLOW + '😝 responding to mast bumper: emergency stop...')
            self._motor_ctrl.emergency_stop()
            if self._shutdown_on_mast_event:
                self._log.info(Fore.YELLOW + '😝 responding to mast bumper: shutdown.')
                self._suppress_behaviours()
                _kros = globals.get('kros')
                _kros.shutdown()
            else:
                self._log.info(Fore.YELLOW + '😝 responding to mast bumper: avoid behaviour...')
                self._queue_publisher.put(self._message_factory.create_message(Event.AVOID, Orientation.MAST))
        elif self._motor_ctrl.is_in_motion:
            self._log.warning(Fore.YELLOW + '😝 responding to mast bumper, but robot does not appear to be moving ahead.')
            self._motor_ctrl.emergency_stop()
        else:
            self._log.info(Fore.YELLOW + '😝 mast bumper triggered but robot does not appear to be moving.')
            self._motor_ctrl.emergency_stop() # why???

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def respond_to_paft_bumper_event(self):
        '''
        Respond to a port aft (PAFT) bumper event by first an emergency stop,
        then if the robot is moving aft, doing something currently unspecified
        but highly intelligent.
        '''
        if self._motor_ctrl.is_moving_astern:
            self._log.info(Fore.RED + '😝 responding to port aft bumper: emergency stop...')
            self._motor_ctrl.stop()
        else:
            self._log.info(Fore.YELLOW + '😝 port aft bumper triggered but robot does not appear to be moving astern.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def respond_to_saft_bumper_event(self):
        '''
        Respond to a starboard aft (SAFT) bumper event by first an emergency
        stop, then if the robot is moving aft, doing something currently
        unspecified but highly intelligent.
        '''
        if self._motor_ctrl.is_moving_astern:
            self._log.info(Fore.GREEN + '😝 responding to starboard aft bumper: emergency stop...')
            self._motor_ctrl.stop()
        else:
            self._log.info(Fore.YELLOW + '😝 starboard aft bumper triggered but robot does not appear to be moving astern.')

#EOF
