#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-10
# modified: 2021-04-28
#

import asyncio
import random
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event

LOG_INDENT = ( ' ' * 60 ) + Fore.CYAN + ': ' + Fore.CYAN

# GarbageCollectedError ........................................................
class GarbageCollectedError(Exception):
    pass

# ..............................................................................
class Subscriber(object):
    '''
    A subscriber to messages from the message bus.

    :param name:         the subscriber name (for logging)
    :param color:        the color to use for printing
    :param message_bus:  the message bus
    :param events:       the list of events used as a filter, None to set as cleanup task
    :param level:        the logging level
    '''
    def __init__(self, name, color, message_bus, level=Level.INFO):
        self._log = Logger('sub-{}'.format(name), level)
        self._name        = name
        self._color       = color
        self._message_bus = message_bus
        self._events      = None # list of acceptable event types
        self._enabled     = True # by default
        self._log.info(self._color + 'ready.')

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
                _events.append('{} '.format(event.name))
            return ''.join(_events)
        else:
            return '(no filter)'

    # ..........................................................................
    async def consume(self):
        '''
        Awaits a message on the message bus, then peeks it, filtering
        on event type. If it is acceptable it is consumed, processing
        the message then putting it back on the bus to be further
        processed and eventually garbage collected.

        This method is not meant to be overridden, except by the garbage
        collector.
        '''
        _peeked_message = await self._message_bus.peek_message()
        if not _peeked_message:
            raise Exception('peek returned none.')
        elif _peeked_message.gcd:
            raise GarbageCollectedError('{} cannot consume: message has been garbage collected. [1]'.format(self.name))

        # 🐸 🐰 🐷 
        _ackd = _peeked_message.acknowledged_by(self)
        if not _ackd and self.acceptable(_peeked_message):

            # acknowledge we've seen the message
            self._log.info(self._color + Style.DIM + '👍 acknowledging accepted message:' \
                    + Fore.WHITE + ' {}; event: {} (queue: {:d} elements)'.format(
                    _peeked_message.name, _peeked_message.event.description, self._message_bus.queue_size))
            _peeked_message.acknowledge(self)

            # this subscriber accepts this message and hasn't seen it before so consume and handle the message
            self._log.info(self._color + Style.DIM + 'waiting to consume acceptable message:' \
                    + Fore.WHITE + ' {}; event: {}'.format(_peeked_message.name, _peeked_message.event.description))

            _message = await self._message_bus.consume_message()

            _event = asyncio.Event()
            self._log.info(Fore.RED + '🍎 begin event tracking for message:' + Fore.WHITE + ' {}; for event: {}'.format(_message.name, _message.event.description))

            # handle acceptable message
            self._message_bus.add_task(asyncio.create_task(self.handle_message(_message, _event), name='{}:handle-message-{}'.format(self.name, _message.name)))

            self._log.info(Fore.RED + '🍎 end event tracking for message:' + Fore.WHITE + ' {}; for event: {}'.format(_message.name, _message.event.description))
            _event.set()

#           self._log.info('🥝 awaiting event tracking completion flag to be set...')
#           await _event.wait()
#           self._log.info('🥝 end waiting for event tracking completion flag to be set.')

            # we've handled message, so pass along to arbitrator
            await self._arbitrate_message(_message)

            self._message_bus.consumed()
            if self._message_bus.verbose:
                self._log.info(self._color + Style.DIM + '🥚 consumed acceptable message:' \
                    + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))

            # republish the message
            self._log.info(self._color + '😈 awaiting republication of message:' \
                + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
            await self._message_bus.republish_message(_message)
            self._log.info(self._color + '😈 message:' \
                + Fore.WHITE + ' {} with event: {}'.format(_message.name, _message.event.description) + self._color + ' has been republished.')

        elif not _ackd:
            # if not already ack'd, acknowledge we've seen the message
            self._log.info(self._color + Style.DIM + '👎 acknowledging unacceptable message:' \
                    + Fore.WHITE + ' {}; event: {} (queue: {:d} elements)'.format(
                    _peeked_message.name, _peeked_message.event.description, self._message_bus.queue_size))
            _peeked_message.acknowledge(self)


    # ..........................................................................
    def _get_timestamp(self):
        return dt.utcfromtimestamp(dt.utcnow().timestamp()).isoformat() #.replace(':','_').replace('-','_').replace('.','_')

    # ..........................................................................
    async def handle_message(self, message, event):
        '''
        Kick off various tasks to consume (process) the message by first creating
        an asyncio event. Tasks are then created for process_message() followed
        by _cleanup_message(). If the latter is overridden it should also called
        by the subclass method as it flags the message as expired. Once these
        tasks have been created the asyncio event flag is set, indicating that
        the message has been consumed.

        The message is acknowledged if this subscriber has subscribed to the
        message's event type and has not acknowledged this message before, or if
        it is not subscribed to the event type (i.e., the message is ignored).
        We don't acknowledge more than once.

        :param message:  the message to consume.
        :param event:    the asyncio event tracker, created by consume()
        '''
        # 🍏 🍈 🍋 🍐 🍑 🍓 🥧 🧀
        if message.gcd:
            raise GarbageCollectedError('cannot handle_message: message has been garbage collected. [2]')
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + 'handle message:' + Fore.WHITE + ' {}; event: {}'.format(message.name, message.event.description))

        self._log.info(self._color + Style.DIM + 'creating task for processing message:' \
                + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))
        self._message_bus.add_task(asyncio.create_task(self.process_message(message), name='{}:process-message-{}'.format(self.name, message.name)))

        self._log.info(self._color + Style.DIM + 'creating task for cleanup after message:' \
                + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))
        self._message_bus.add_task(asyncio.create_task(self._cleanup_message(message), name='{}:cleanup-message-{}'.format(self.name, message.name)))

#       while not event.is_set():
#       self._log.info(Fore.RED + '🍎 end event tracking for message:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))
#       event.set()

        if self._message_bus.verbose:
            _elapsed_ms = (dt.now() - message.timestamp).total_seconds() * 1000.0
            self._print_message_info('handled message:', message, _elapsed_ms)

    # ..........................................................................
    async def process_message(self, message):
        '''
        Process the message, i.e., pass its Payload along to the Arbitrator,
        which passes the highest priority Payload to the Controller to change
        the state of the robot.

        :param message:  the message to process.
        '''
        self._log.info(self._color + Style.DIM + '🍏 processing message {}'.format(message.name))
        if message.gcd:
            raise GarbageCollectedError('cannot process message: message has been garbage collected. [3]')
        message.process(self)

#       self._arbitrate_message(message)

        self._log.info(self._color + Style.DIM + '🍏 processed message {}'.format(message.name))

    # ..........................................................................
    async def _arbitrate_message(self, message):
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + '🍏 arbitrating payload for event {}; value: {}'.format(message.payload.event.name, message.payload.value))
        await self._message_bus.arbitrate(message.payload)
        # increment sent acknowledgement count
        message.acknowledge_sent()
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + '🍏 arbitrated payload for event {}; value: {}'.format(message.payload.event.name, message.payload.value))

    # ..........................................................................
    async def _cleanup_message(self, message):
        '''
        Cleanup tasks related to completing work on a message (by this subscriber). 

        This currently just sets the message's 'expire' flag as True.

        :param message:  consumed message that is done being processed.
        '''
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + '🚽 begin cleanup of message: {}'.format(message.name))
        if message.gcd:
            self._log.warning('cannot cleanup message: message has been garbage collected. [4]')
            return
        message.expire()

#       # tasks related to this message
#       self._message_bus.clear tasks()

#       self._log.info(self._color + Style.DIM + '🚽 A. processing cleanup of message: {}...'.format(message.name))
#       if self._message_bus.is_expired(message) or message.fully_acknowledged:
#           self._log.info(self._color + Style.DIM + '🚽 A1. processing cleanup of message: {}...'.format(message.name))
#           await self._message_bus.garbage_collect(message)
#           self._log.info(self._color + Style.DIM + '🚽 A2. processing cleanup of message: {}...'.format(message.name))
#           if self._message_bus.verbose:
#               self._log.info(self._color + Style.DIM + '🚽 end cleanup of message: {} (garbage collected)'.format(message.name))
#       else:
#           self._log.info(self._color + Style.DIM + '🚽 B1. processing cleanup of message: {}...'.format(message.name))
#           if self._message_bus.verbose:
#               self._log.info(self._color + Style.DIM + '🚽 end cleanup of message: {}'.format(message.name))

        self._log.info(self._color + Style.DIM + '🚽 end cleanup of message: {}'.format(message.name))

    # ..........................................................................
    def _get_formatted_time(self, label, value):
       if value is None:
           return ''
       elif value > 1000.0:
           return Fore.RED + label + ' {:4.3f}s'.format(value/1000.0)
       else:
           return label + ' {:4.3f}ms'.format(value)

    # ..........................................................................
    def _print_message_info(self, info, message, elapsed):
        '''
        Print an informational string followed by details about the message.

        :param info:     the information string
        :param message:  the message and its payload to display
        :param elapsed:  the optional elapsed time (in milliseconds) for an operation
        '''
        self._log.info(self._color + info + '\n' \
                + LOG_INDENT + 'id: ' + Style.BRIGHT + '{};'.format(message.name) + Style.NORMAL \
                + ' event: ' + Style.BRIGHT + ( '{}\n'.format(message.event.description) if message.event else 'n/a: [gc\'d]\n' ) + Style.NORMAL \
                + LOG_INDENT + '{:d} procd;'.format(message.processed) + ' sent {:d}x;'.format(message.sent) \
                        + ' expired? {}\n'.format(self._message_bus.is_expired(message)) \
                + LOG_INDENT + 'procd by:\t{}\n'.format(message.print_procd()) \
                + LOG_INDENT + 'acked by:\t{}\n'.format(message.print_acks()) \
                + LOG_INDENT + self._get_formatted_time('msg age: ', message.age) + '; ' + self._get_formatted_time('elapsed: ', elapsed))

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if not self._closed:
            if self._enabled:
                self._log.warning('already enabled.')
            else:
                self._enabled = True
                self._log.info('enabled.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._enabled = False
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def close(self):
        '''
        Permanently close and disable the message bus.
        '''
        if not self._closed:
            self.disable()
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.debug('already closed.')


# GarbageCollector .............................................................
class GarbageCollector(Subscriber):
    '''
    Extends subscriber as a garbage collector that eliminates messages after
    they've passed the publish cycle.

    :param name:         the subscriber name (for logging)
    :param color:        the color to use for printing
    :param message_bus:  the message bus
    :param events:       the list of events used as a filter, None to set as cleanup task
    :param level:        the logging level
    '''
    def __init__(self, name, color, message_bus, level=Level.INFO):
        super().__init__(name, color, message_bus, level=Level.INFO)
        self._max_age = 3.0 # ms
        self._log.info(self._color + 'ready.')

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
#   
        _elapsed_ms = (dt.now() - message.timestamp).total_seconds() * 1000.0
        if self._message_bus.is_expired(message) and message.fully_acknowledged:
            if self._message_bus.verbose:
                self._print_message_info('🙈 garbage collecting expired, fully-acknowledged message:', message, _elapsed_ms)
            return True
        elif self._message_bus.is_expired(message):
            if self._message_bus.verbose:
                self._print_message_info('🙉 garbage collecting expired message:', message, _elapsed_ms)
            return True
        elif message.fully_acknowledged:
            if self._message_bus.verbose:
                self._print_message_info('🙊 garbage collecting fully-acknowledged message:', message, _elapsed_ms)
            return True
        else:
            if self._message_bus.verbose:
                self._print_message_info('🐸 garbage collector ignoring unprocessed message:', message, _elapsed_ms)
            return False

    # ..........................................................................
    async def x_collect(self, message):
        '''
        Explicitly collect the message by popping it from the queue for
        garbage collection.
        '''
        _peeked_message = await self._message_bus.peek_message()
        if _peeked_message == None:
            self._log.info('💩 cannot collect: queue is empty.')
        elif _peeked_message == message:
            self._log.info('💩 collecting message from queue.')
            _message = await self._message_bus.consume_message()
            self._message_bus.consumed()
        else:
            self._log.info('💩 cannot collect: message is not in queue.')

    # ..........................................................................
    async def consume(self):
        '''
        Overrides the method on Subscriber to first peek, and then if acceptable
        (expired and/or fully acknowledged), then consume and explicitly garbage
        collect the message.
        '''
        _peeked_message = await self._message_bus.peek_message()
        if not _peeked_message:
            raise Exception('peek returned none.')
        elif _peeked_message.gcd:
            self._log.warning('message has already been garbage collected. [1]'.format(self.name))
        if self._message_bus.verbose: # TEMP
            self._log.info(self._color + '💀 gc-consume() message:' + Fore.WHITE + ' {}; event: {}'.format(_peeked_message.name, _peeked_message.event.description))

        # garbage collect (consume) if filter accepts the peeked message
        if self.acceptable(_peeked_message):
            _message = await self._message_bus.consume_message()
            self._message_bus.consumed()
            _message.gc() # mark as garbage collected and don't republish
            if self._message_bus.verbose:
                self._log.info(self._color + '💀 garbage collected message:' + Fore.WHITE + ' {}; gcd: {}'.format(_message.name, _message.gcd))
        elif not _peeked_message.acknowledged_by(self):
            # acknowledge we've seen the message
            self._log.info(self._color + Style.DIM + '💀 gc: not actually acknowledging message:' + Fore.WHITE + ' {}; event: {} (queue: {:d} elements)'.format(
                    _peeked_message.name, _peeked_message.event.description, self._message_bus.queue_size))
#           _peeked_message.acknowledge(self)
        else:
            self._log.info(self._color + Style.DIM + '💀 gc: ELSE message:' + Fore.WHITE + ' {}; event: {} (queue: {:d} elements)'.format(
                    _peeked_message.name, _peeked_message.event.description, self._message_bus.queue_size))
            _peeked_message.acknowledge(self)

#EOF
