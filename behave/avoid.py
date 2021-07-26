#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2021-06-26
#

import itertools
import asyncio
from queue import SimpleQueue
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.fsm import State
from core.event import Event, Group
from core.util import Util
from behave.behaviour import Behaviour
from core.publisher import Publisher
from behave.trigger_behaviour import TriggerBehaviour
from hardware.motor_controller import MotorController

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Avoid(Behaviour, Publisher):

    _AVOID_PUBLISHER_LOOP = '__avoid_publisher_loop'

    '''
    Extends both Behaviour and Publisher to implement an
    obstable avoidance behaviour. The Behaviour subscribes to
    infrared and bumper events, and should an event appear with
    a distance less than the minimum distance threshold we
    trigger one of the avoidance behaviours depending on sensor
    and distance.

    :param config:          the application configuration
    :param message_bus:     the asynchronous message bus
    :param message_factory: the factory for messages
    :param motor_ctrl:      the motor controller
    :param level:           the optional log level
    '''
    def __init__(self, config, message_bus, message_factory, motor_ctrl, level=Level.INFO):
        Behaviour.__init__(self, 'avoid', config, message_bus, message_factory, level)
        Publisher.__init__(self, 'avoid', config, message_bus, message_factory, suppressed=True, level=level)
        if not isinstance(motor_ctrl, MotorController):
            raise ValueError('wrong type for motor_ctrl argument: {}'.format(type(motor_ctrl)))
        self._motor_ctrl = motor_ctrl
        _cfg = self._config['kros'].get('behaviour').get('avoid')
        self._min_distance = _cfg.get('min_distance')
        self._queue = SimpleQueue()
        self._avoid_loop_delay_sec = 0.05 # 50ms/20Hz, so each loop is 1/20th second or 20 loops/sec
        self._publish_loop_running = False
        self._delay_ticks = 0
        self._counter = itertools.count()
        self.add_events([ Group.INFRARED, Group.BUMPER ])
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_trigger_behaviour(self, event):
        return TriggerBehaviour.TOGGLE # or RELEASE

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def trigger_event(self):
        '''
        This returns the event used to enable/disable the behaviour manually.
        '''
        return Event.AVOID

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        '''
        if self.state is not State.STARTED:
            Publisher.start(self)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Publisher.enable(self)
        if self.enabled:
            if self._message_bus.get_task_by_name(Avoid._AVOID_PUBLISHER_LOOP) or self._publish_loop_running:
                raise Exception('already enabled.')
#               self._log.warning('already enabled.')
            else:
                self._log.info('creating task for avoid listener loop...')
                self._publish_loop_running = True
                self._message_bus.loop.create_task(self._avoid_publisher_loop(lambda: self.enabled), name=Avoid._AVOID_PUBLISHER_LOOP)
                self._log.info('enabled.')
        else:
            self._log.warning('failed to enable avoid publisher.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def callback(self):
        self._log.info('👾 avoid callback.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'avoid'

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _queue_directive(self, event, delay_ms=0):
        '''
        Queue a directive as a message bearing the event and value. If
        the delay is provided this is converted to ticks, which acts as
        a countdown timer on the loop to delay popping the next message
        from the queue.

          # with delay at 0.05/50ms/20Hz, each loop is 1/20th second or 20 loops/sec
          # one tick is one loop of 50ms, 1000ms/1sec = 20 ticks
        '''
        _ticks = int( delay_ms / ( self._avoid_loop_delay_sec * 1000 ))
        _message = self._message_factory.create_message(event, _ticks)
        self._log.info('creating publish task for message: {} for {:d} ticks (delay: {}ms)'.format(_message.event.label, _message.payload.value, delay_ms))
        self._queue.put(_message, False)
        self._log.debug('created publish task.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _avoid_publisher_loop(self, f_is_enabled):
        '''
        We get a message from the queue and publish it.

        Then we loop. The published message's value is the number
        of loop ticks to wait until getting the next message.

        We continue to loop but without getting another message
        until the delay_tick_counter reaches zero.
        '''
        self._log.info('starting avoid listener loop:\t' + Fore.YELLOW + 'min distance: {:5.2f} cm'.format(self._min_distance)
                + ( '; (suppressed, type \'m\' to release)' if self.suppressed else '.') )
        _last_event = Event.NOOP
        while f_is_enabled():
            _count = next(self._counter)
            self._log.debug('[{:03d}] begin avoid loop with {} delay ticks...'.format(_count, self._delay_ticks))
            if not self.suppressed:
                self._log.debug('[{:03d}] avoid released.'.format(_count))
                if self._delay_ticks == 0: # then we can pop the next message from the queue...
                    if not self._queue.empty():

                        if _last_event is not Event.NOOP:
                            _delta = dt.now() - _start_time
                            _elapsed_ms = int(_delta.total_seconds() * 1000)
                            self._log.debug(Fore.MAGENTA + Style.DIM + 'elapsed: {}ms'.format(_elapsed_ms) + Style.DIM)
                            self._log.info(Fore.YELLOW + '[{:03d}] {} has completed; {} ms elapsed...'.format(_count, _last_event.label, _elapsed_ms))
                        _start_time = dt.now()

                        # pop queue and publish...
                        _message = self._queue.get()
                        _last_event = _message.event
                        self._log.info('💠 avoid-publishing message:' + Fore.WHITE + ' {}; event: {} for {:d} ticks.'.format(_message.name, _message.event.label, _message.payload.value))
                        await Publisher.publish(self, _message)
                        self._log.debug('avoid-published message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.label))
                        # add loop/tick delay if provided...
                        self._delay_ticks = _message.value if ( _message.value and isinstance(_message.value, int) ) else 0
            else:
                self._log.debug('[{:03d}] avoid suppressed.'.format(_count))

            await asyncio.sleep(self._avoid_loop_delay_sec)

            # every loop we decrement if above zero
            if self._delay_ticks > 0:
                self._delay_ticks -= 1
                if _count % 1 == 0:
                    self._log.debug('[{:03d}] waiting for {} to complete, with {} delay ticks remaining...'.format(_count, _last_event.label, self._delay_ticks))
            elif _last_event is not Event.NOOP:
                _delta = dt.now() - _start_time
                _elapsed_ms = int(_delta.total_seconds() * 1000)
                self._log.info(Fore.YELLOW + '[{:03d}] {} has completed; {} ms elapsed...'.format(_count, _last_event.label, _elapsed_ms))
                # reset
                _last_event = Event.NOOP
            else:
                self._log.debug('[{:03d}] no task executing.'.format(_count))

        self._log.info('avoid loop complete.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def __publish_message(self, message):
        self._log.info('👾 __publishing message: {}'.format(message.event.label))
#       await Publisher.publish(self, message)
        await self._message_bus.publish_message(message)
        await asyncio.sleep(0.05)
        self._log.info('👾 __published message: {}'.format(message.event.label))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def execute(self, message):
        '''
        The method called upon each loop iteration. This receives a message and
        executes a ballistic behaviour for either a bumper or infrared event (if
        the latter is closer than a specified threshold distance).

        :param message:  an optional Message passed along by the message bus
        '''
        if self.suppressed:
            self._log.info(Style.DIM + '👾 avoid suppressed; message: {}'.format(message.event.label))
        else:
            self._log.info('👾 avoid released; message: {}'.format(message.event.label))
            _timestamp = self._message_bus.last_message_timestamp
            if _timestamp is None:
                self._log.info('👾 avoid loop execute; no previous messages.')
            else:
                _elapsed_ms = (dt.now() - _timestamp).total_seconds() * 1000.0
                self._log.info('👾 avoid loop execute; {}'.format(Util.get_formatted_time('message age:', _elapsed_ms)))
            if self.enabled:
                _payload = message.payload
                _event   = _payload.event
                _value   = _payload.value
                self._log.info('👾 avoid enabled, execution on message {}; '.format(message.name) + Fore.YELLOW + ' event: {}; value: {}'.format(_event.label, _value))

                # process value
                if _value < self._min_distance:
                    self._log.info(Fore.YELLOW + '👾 avoid: value below threshold; event: {}; value: {}'.format(_event.label, _value))

#                   # David Anderson's IR bumper behaviour .........................................
#                   void bumper_behavior()      /* Collision recovery as concurrent task */
#                   {
#                   extern LAYER bump;      // C structure for behavior output
#                   int bumper;             // local to hold bumper switches status
#
#                   while (1) {             // endless loop
#                       bumper = read_bumper_switches();   // read the bumper switches
#                       if (bumper) {                   // if any switches are closed
                    if Event.is_bumper_event(_event):
                        # Ballistic segment 1 ........................
                        self._queue_directive(Event.SLOW_ASTERN, 6000)
                        # bump.cmd = BACKUP_SLOW;     // request reverse low speed
                        # bump.arg = 0;               // straight back
                        # bump.flag = TRUE;           // signal arbitrator
                        # msleep(1000);               // suspend and back up for 1 second


                        # Ballistic segment 2 ........................
                        # bump.cmd = HALF_SPEED;      // then request forward � speed
                        # if (bump == LEFT)           // and turn away from the bump
                        # bump.arg = RIGHT_TURN;
                        # else bump.arg = LEFT_TURN;
                        _turn_ahead_delay = 3000
                        if _event is Event.BUMPER_PORT:
                            self._log.info('👾 avoid; event: {}; value: {}'.format(_event.label, _value))
                            self._queue_directive(Event.TURN_AHEAD_STBD, _turn_ahead_delay)

                        elif _event is Event.BUMPER_STBD:
                            self._log.info('👾 avoid; event: {}; value: {}'.format(_event.label, _value))
                            self._queue_directive(Event.TURN_AHEAD_PORT, _turn_ahead_delay)

                        elif _event is Event.BUMPER_CNTR:
                            self._log.info('👾 avoid; event: {}; value: {}'.format(_event.label, _value))
                            self._queue_directive(Event.TURN_AHEAD_PORT, _turn_ahead_delay) # same as starboard
                        # msleep(500);                // suspend and turn for 1/2 second

                        # Ballistic segment 3 ........................
                        # bump.cmd = top_speed;       // request full speed
                        self._queue_directive(Event.FULL_AHEAD, 4000)
                        # bump.arg = 0;               // straight forward
                        # bump.flag = TRUE;           // signal arbitrator
                        # msleep(250);               // suspend and back up for 1/4 second

                        # Ballistic segments complete
                        # bump.flag = FALSE;          // then reset arbitration flag and loop

                        #  } else {                         // else if no bumps,
                        #       bump.flag = FALSE;	        // reset flag and	
                        #       msleep(10);                 // loop at 100Hz, looking for bumps
                        #  }
                        # }
                        # }

                    elif _event is Event.INFRARED_PORT_SIDE:
                        self._log.info('👾 avoid; event: {}; value: {}'.format(_event.label, _value))
                    elif _event is Event.INFRARED_PORT:
                        self._log.info('👾 avoid; event: {}; value: {}'.format(_event.label, _value))
                    elif _event is Event.INFRARED_CNTR:
                        self._log.info('👾 avoid; event: {}; value: {}'.format(_event.label, _value))
                    elif _event is Event.INFRARED_STBD:
                        self._log.info('👾 avoid; event: {}; value: {}'.format(_event.label, _value))
                    elif _event is Event.INFRARED_STBD_SIDE:
                        self._log.info('👾 avoid; event: {}; value: {}'.format(_event.label, _value))
                    else:
                        raise ValueError('expected a bumper or infrared event, not {}'.format(_event.label))
                    # David Anderson's IR collision avoidance behaviour ............................
#                   int ir_task()
#                   {
#                       extern LAYER ir;                       // C structure for task output
#                       int detect = read_ir_sensors();        // read sensors
#                       if (detect == LEFT) {                  // if reflection on the left
#                               ir.cmd = HALF_SPEED;           // request slow down
#                               ir.arg = RIGHT_TURN;           // and turn right
#                               ir.flag = TRUE;                // signal arbitrator we want control
#                       } else {
#                           if (detect == RIGHT) {             // else if reflection on the right
#                               ir.cmd = HALF_SPEED;           // request slow down
#                               ir.arg = LEFT_TURN;            // and turn left
#                               ir.flag = TRUE;                // tell arbitrator we want control
#                           } else {
#                               if (detect == BOTH) {          // else if reflection left and right
#                                   ir.cmd = ZERO_SPEED;       // request slow to zero
#                                   ir.arg = keep_turning();   // keep turning same direction
#                                   ir.flag = TRUE;            // signal arbitrator we want control
#                               } else {
#                                  ir.flag = FALSE;            // else no detection, release control
#                               }
#                           }
#                       }
#                   }
                else:
                    self._log.info('👾💜 avoid (no action): value above threshold; event: {}; value: {}'.format(_event.label, _value))
            else:
                self._log.info('👾 avoid disabled, execution on message {}; '.format(message.name) + Fore.YELLOW + ' event: {}; value: {}'.format(_event.label, _value))

#EOF
