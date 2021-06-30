#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-10
# modified: 2021-06-29
#

import asyncio
import random
from typing import final
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component
from core.fsm import FiniteStateMachine
from core.message_bus import MessageBus

# ..............................................................................
class Subscriber(Component, FiniteStateMachine):
    '''
    Extends FiniteStateMachine as a subscriber to messages from the message bus.
    '''
    LOG_INDENT = ( ' ' * 60 ) + Fore.CYAN + ': ' + Fore.CYAN

    def __init__(self, name, message_bus, color=Fore.CYAN, level=Level.INFO):
        '''
        :param name:         the subscriber name (for logging)
        :param message_bus:  the message bus
        :param color:        the optional color for log messages
        :param events:       the list of events used as a filter, None to set as cleanup task
        :param level:        the logging level
        '''
        self._log = Logger('sub:{}'.format(name), level)
        Component.__init__(self, self._log, False)
        FiniteStateMachine.__init__(self, self._log, name)
        self._name        = name
        self._color       = color
        if message_bus is None:
            raise ValueError('null message bus argument.')
        elif isinstance(message_bus, MessageBus):
            self._message_bus = message_bus
        else:
            raise ValueError('unrecognised message bus argument: {}'.format(type(message_bus)))
        self._events      = None # list of acceptable event types
        self._brief       = True # brief messages by default
        self._message_bus.register_subscriber(self)
        self._log.info(self._color + 'ready.')

    # ..........................................................................
    def set_log_level(self, level):
        self._log.level = level

    # ..........................................................................
    @property
    def name(self):
        return self._name

    # ..........................................................................
    @property
    def is_gc(self):
        return False

    # events  ..................................................................

    @property
    def events(self):
        '''
        A function to return the list of events that this subscriber accepts.
        '''
        return self._events

    def add_event(self, event):
        '''
        Adds another event to the list that this subscriber accepts.
        '''
        self._events.append(event)
        self._log.info('configured {:d} events for subscriber: {}.'.format(len(self._events), self._name))

    @events.setter
    def events(self, events):
        '''
        Sets the list of events that this subscriber accepts.
        '''
        self._events = events

    def acceptable(self, message):
        '''
        A filter that returns True if the message's event type is acceptable
        to this subcriber.
        '''
        return message.event in self._events

    def print_events(self):
        if self._events:
            _events = []
            for event in self._events:
                _description = event.description.replace(' ','-')
                _events.append('{} '.format(_description))
            return ''.join(_events)
        else:
            return '[ANY]'

    # ..........................................................................
    @final
    async def consume(self):
        '''
        Awaits a message on the message bus, first peeking at it from the queue,
        filtering on event type.

        Kick off various tasks to consume (process) the message by first creating
        an asyncio event. Tasks are then created to process the message followed
        by a cleanup task. If the latter is overridden it should also called
        by the subclass method as it flags the message as expired. Once these
        tasks have been created the asyncio event flag is set, indicating that
        the message has been consumed, and can subsequently garbage collected.

        This method is not meant to be overridden, except by the garbage
        collector. The process_message() method can be overridden.
        '''
        _peeked_message = await self._message_bus.peek_message()
        if not _peeked_message:
            raise QueueEmptyOnPeekError('peek returned none.')
        elif _peeked_message.gcd:
            raise GarbageCollectedError('{} cannot consume: message has been garbage collected. [1]'.format(self.name))

        _ackd = _peeked_message.acknowledged_by(self)
        if not _ackd and self.acceptable(_peeked_message):

            _event = asyncio.Event()
            self._log.debug(Fore.RED + 'begin event tracking for message:' + Fore.WHITE 
                    + ' {}; event: {}'.format(_peeked_message.name, _peeked_message.event.description))

            # acknowledge we've seen the message
            _peeked_message.acknowledge(self)

            # this subscriber accepts this message and hasn't seen it before so consume and handle the message
            self._log.debug(self._color + Style.DIM + 'waiting to consume acceptable message:'
                    + Fore.WHITE + ' {}; event: {}'.format(_peeked_message.name, _peeked_message.event.description))

            _message = await self._message_bus.consume_message()
            self._message_bus.consumed()
            if self._message_bus.verbose:
                self._log.debug(self._color + Style.DIM + 'consumed acceptable message:' \
                    + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))

            # handle acceptable message
            if self._message_bus.verbose:
                _elapsed_ms = (dt.now() - _message.timestamp).total_seconds() * 1000.0
                self._print_message_info('❕ process message:', _message, _elapsed_ms)
            self._log.debug(self._color + Style.DIM + 'creating task for processing message:' \
                    + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
            # create message processing task
            asyncio.create_task(self.process_message(_message), name='{}:process-message-{}'.format(self.name, _message.name))

            # create message cleanup task
            _cleanup_task = asyncio.create_task(self._cleanup_message(_message), name='{}:cleanup-message-{}'.format(self.name, _message.name))
            _cleanup_task.add_done_callback(self._done_callback)

            self._log.debug('end event tracking for message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
            _event.set()

            # we've handled message so pass along to arbitrator
            if not _message.sent:
                self._log.debug(self._color + 'sending message: {}; event: {} to arbitrator...'.format(_message.name, _message.event.description))
                await self._arbitrate_message(_message)
                self._log.debug(self._color + 'sent message:' + Fore.WHITE + ' {}; event: {} to arbitrator.'.format(_message.name, _message.event.description))
            else:
                self._log.warning(self._color + 'message: {} already sent; event: {}'.format(_message.name, _message.event.description))

            # keep track of timestamp of last message
            self._message_bus.last_message_timestamp = _message.timestamp

            # republish the message
            self._log.debug(self._color + 'awaiting republication of message:' \
                + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
            await self._message_bus.republish_message(_message)
            self._log.debug(self._color + 'message:' \
                + Fore.WHITE + ' {} with event: {}'.format(_message.name, _message.event.description) + self._color + ' has been republished.')

        elif not _ackd:
            # if not already ack'd, acknowledge we've seen the message
            self._log.debug(self._color + Style.DIM + 'acknowledging unacceptable message:' \
                    + Fore.WHITE + ' {}; event: {} (queue: {:d} elements)'.format(
                    _peeked_message.name, _peeked_message.event.description, self._message_bus.queue_size))
            _peeked_message.acknowledge(self)

    # ..........................................................................
    def _done_callback(self, task):
        '''
        Has the message bus clear any completed tasks.
        '''
        self._message_bus.clear_tasks()
        self._log.debug('callback on message consume complete; {}'.format(task.get_name()))

#   # ..........................................................................
#   def _get_timestamp(self):
#       return dt.utcfromtimestamp(dt.utcnow().timestamp()).isoformat() #.replace(':','_').replace('-','_').replace('.','_')

    # ..........................................................................
    async def process_message(self, message):
        '''
        Process the message, i.e., pass its Payload along to the Arbitrator,
        which passes the highest priority Payload to the Controller to change
        the state of the robot.

        This method is meant to be overridden by subclasses. Its only
        responsibility is to set the message's processed flag.

        :param message:  the message to process.
        '''
        self._log.debug(self._color + Style.DIM + 'processing message {}'.format(message.name))
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
        # indicate that this subscriber has processed the message
        message.process(self)
        self._log.debug(self._color + Style.DIM + 'processed message {}'.format(message.name))

    # ..........................................................................
    async def _arbitrate_message(self, message):
        '''
        Pass the message on to the Arbitrator and acknowledge that it has been
        sent (by setting a flag in the message).
        '''
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + 'arbitrating payload for event {}; value: {}'.format(message.payload.event.name, message.payload.value))
        await self._message_bus.arbitrate(message.payload)
        # increment sent acknowledgement count
        message.acknowledge_sent()
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + 'arbitrated payload for event {}; value: {}'.format(message.payload.event.name, message.payload.value))

    # ..........................................................................
    async def _cleanup_message(self, message):
        '''
        Cleanup tasks related to completing work on a message (by this subscriber). 

        This currently sets the message's 'expire' flag as True and tells the
        message bus to clear any completed tasks. It's not really async but is
        declared as such as part of the asyncio experiment.

        :param message:  consumed message that is done being processed.
        '''
        if self._message_bus.verbose:
            self._log.debug(self._color + Style.DIM + 'begin cleanup of message: {}'.format(message.name))
        if message.gcd:
            self._log.warning('cannot cleanup message: message has been garbage collected. [4]')
            return
        # set message flag as expired
        self._log.info('message {} expired by subscriber: {}.'.format(message.name, self._name))
        message.expire()
        # clear any tasks related to the message
        self._message_bus.clear_tasks()
        self._log.debug(self._color + Style.DIM + 'end cleanup of message: {}'.format(message.name))

    # ..........................................................................
    def _print_message_info(self, title, message, elapsed):
        '''
        Print an informational string followed by details about the message.

        :param title:    the title string
        :param message:  the message and its payload to display
        :param elapsed:  the optional elapsed time (in milliseconds) for an operation
        '''
        if self._brief:
            self._log.info(self._color + Style.BRIGHT + title + Style.NORMAL \
                    + ' id: ' + Style.BRIGHT + '{};'.format(message.name) + Style.NORMAL \
                    + ' event: ' + Style.BRIGHT + ( '{}; '.format(message.event.description) if message.event else 'n/a' ) + Style.NORMAL \
                    + ' value: ' + Style.BRIGHT + Subscriber.get_formatted_value(message.payload.value))
        else:
            self._log.info(self._color + Style.BRIGHT + title + Style.NORMAL + '\n' \
                    + Subscriber.LOG_INDENT + 'id: ' + Style.BRIGHT + '{};'.format(message.name) + Style.NORMAL \
                    + ' event: ' + Style.BRIGHT + ( '{}; '.format(message.event.description) if message.event else 'n/a: [gc\'d] ' ) + Style.NORMAL \
                    + ' value: ' + Style.BRIGHT + Subscriber.get_formatted_value(message.payload.value) + '\n' + Style.NORMAL \
                    + Subscriber.LOG_INDENT + '{:d} procd;'.format(message.processed) + ' sent {:d}x;'.format(message.sent) \
                            + ' expired? {}\n'.format(self._message_bus.is_expired(message)) \
                    + Subscriber.LOG_INDENT + 'procd by:\t{}\n'.format(message.print_procd()) \
                    + Subscriber.LOG_INDENT + 'acked by:\t{}\n'.format(message.print_acks()) \
                    + Subscriber.LOG_INDENT + Subscriber.get_formatted_time('msg age: ', message.age) + '; ' + Subscriber.get_formatted_time('elapsed: ', elapsed))

    # ..........................................................................
    @staticmethod
    def get_formatted_value(value):
#       print('TYPE: {}'.format(type(value)))
        if isinstance(value, float):
            return '{:5.2f}'.format(value)
        else:
            return '{}'.format(value)

    # ..........................................................................
    @staticmethod
    def get_formatted_time(label, value):
       if value is None:
           return ''
       elif value > 1000.0:
           return label + ' {:4.3f}s'.format(value/1000.0)
#          return Fore.RED + label + ' {:4.3f}s'.format(value/1000.0)
       else:
           return label + ' {:4.3f}ms'.format(value)

    # ..........................................................................
    def start(self):
        '''
        The necessary state machine call to start the publisher, which performs
        any initialisations of active sub-components, etc.
        This also enables the Subscriber, which is upon initialisation disabled.
        '''
        self._log.debug('subscriber {} started.'.format(self.name))
        super().start()
        self.enable()

    # ..........................................................................
    def disable(self):
        super().disable()
        FiniteStateMachine.disable(self)

    # ..........................................................................
    def close(self):
        super().close()
        FiniteStateMachine.close(self)

    # ..........................................................................
    def __key(self):
        return (self.name, self._color)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, obj):
        return isinstance(obj, Subscriber) and obj.name == self.name

# GarbageCollector .............................................................
class GarbageCollector(Subscriber):
    '''
    Extends subscriber as a garbage collector that eliminates messages after
    they've passed the publish cycle.

    :param name:         the subscriber name (for logging)
    :param color:        the color to use for printing
    :param message_bus:  the message bus
    :param level:        the logging level
    '''
    def __init__(self, name, message_bus, color=Fore.BLUE, level=Level.INFO):
        Subscriber.__init__(self, name, message_bus, color, level)
#       super().__init__(name, message_bus, color, level)

    # ..........................................................................
    @property
    def is_gc(self):
        return True

    # ..........................................................................
    def acceptable(self, message):
        '''
        A filter that returns True if the message is either expired and/or
        fully acknowledged.
        '''
        _elapsed_ms = (dt.now() - message.timestamp).total_seconds() * 1000.0
        if self._message_bus.is_expired(message) and message.fully_acknowledged:
            if self._message_bus.verbose:
                self._print_message_info('garbage collecting expired, fully-acknowledged message:', message, _elapsed_ms)
            return True
        elif self._message_bus.is_expired(message):
            if self._message_bus.verbose:
                self._print_message_info('garbage collecting expired message:', message, _elapsed_ms)
            return True
        elif message.fully_acknowledged:
            if self._message_bus.verbose:
                self._print_message_info('garbage collecting fully-acknowledged message:', message, _elapsed_ms)
            return True
        else:
            if self._message_bus.verbose:
                self._print_message_info('garbage collector ignoring unprocessed message:', message, _elapsed_ms)
            return False

    # ..........................................................................
    async def consume(self):
        '''
        Overrides the method on Subscriber to first peek, and then if acceptable
        (expired and/or fully acknowledged), then consume and explicitly garbage
        collect the message.
        '''
        _peeked_message = await self._message_bus.peek_message()
        if not _peeked_message:
            raise QueueEmptyOnPeekError('peek returned none.')
        elif _peeked_message.gcd:
            self._log.warning('message has already been garbage collected. [1]'.format(self.name))
        if self._message_bus.verbose:
            self._log.info(self._color + 'gc-consume() message:' + Fore.WHITE + ' {}; event: {}'.format(_peeked_message.name, _peeked_message.event.description))

        # garbage collect (consume) if filter accepts the peeked message
        if self.acceptable(_peeked_message):
            _message = await self._message_bus.consume_message()
            self._message_bus.consumed()
            _message.gc() # mark as garbage collected and don't republish
            if not _message.sent:
                self._log.warning('garbage collected undelivered message: {}; event: {}'.format(_message.name, _message.event.name))
            if self._message_bus.verbose:
                self._log.info(self._color + 'garbage collected message:' + Fore.WHITE + ' {}; gcd: {}'.format(_message.name, _message.gcd))
        else:
            # acknowledge we've seen the message
            _peeked_message.acknowledge(self)
            self._log.info(self._color + Style.DIM + 'acknowledged unacceptable message:' \
                    + Fore.WHITE + ' {}; event: {} (queue: {:d} elements)'.format(
                    _peeked_message.name, _peeked_message.event.description, self._message_bus.queue_size))

# GarbageCollectedError ........................................................
class GarbageCollectedError(Exception):
    '''
    The garbage collector refused to process the message that has already been
    garbage collected.
    '''
    pass

# QueueEmptyOnPeekError ........................................................
class QueueEmptyOnPeekError(Exception):
    '''
    An awaited peek at the queue failed to return a message.
    '''
    pass

#EOF
