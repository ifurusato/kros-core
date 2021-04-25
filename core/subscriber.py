#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-10
# modified: 2021-03-13
#

import asyncio
import random
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event

LOG_INDENT = ( ' ' * 60 ) + Fore.CYAN + ': ' + Fore.CYAN

# SaveFailed exception .........................................................
class SaveFailed(Exception):
    pass

# RestartFailed exception ......................................................
class RestartFailed(Exception):
    pass

# Subscriber ...................................................................
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

    # ..........................................................................
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

    def print_events(self):
        if self._events:
            _events = []
            for event in self._events:
                _events.append('{} '.format(event.name))
            return ''.join(_events)
        else:
            return '(no filter)'

    # ................................................................
    async def consume(self):
        '''
        Awaits a message on the message bus, then peeks it, filtering
        on event type. If it is acceptable it is consumed, processing
        the message then putting it back on the bus to be further
        processed and eventually garbage collected.
        '''
<<<<<<< HEAD
        _peeked_message = await self._message_bus.peek_message()
        if not _peeked_message:
            raise Exception('peek returned none.')
        elif _peeked_message.gcd:
            raise Exception('{} cannot consume: message has been garbage collected. [1]'.format(self.name))

        # if acceptable, consume/handle the message
        if self.acceptable(_peeked_message):

            # acknowledge we've seen the message
            self._log.info(self._color + Style.NORMAL + 'acknowledging message:' + Fore.WHITE + ' {}; event: {} (queue: {:d} elements)'.format(
                    _peeked_message.name, _peeked_message.event.description, self._message_bus.queue_size))
            _peeked_message.acknowledge(self)
    #       self._message_bus.task_done()

            # this subscriber accepts this message and hasn't seen it before so consume and handle the message
            self._log.info(self._color + Style.NORMAL + 'waiting to consume acceptable message:' + Fore.WHITE + ' {}; event: {}'.format(_peeked_message.name, _peeked_message.event.description))
            _message = await self._message_bus.consume_message()
            self._message_bus.task_done()
            if self._message_bus.verbose:
                self._log.info(self._color + Style.NORMAL + 'consuming acceptable message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
            # handle acceptable message
            asyncio.create_task(self.handle_message(_message))
            # If not gc'd, republish the message. If fully-ackd it will be ignored
#           if not _message.gcd and not _message.fully_acknowledged:
=======
        _message = await self._message_bus.consume_message()
        self._message_bus.task_done()
        # if garbage collected, raise exception
        if _message.gcd:
            self._log.warning('{} cannot consume: message has been garbage collected. [1]'.format(self.name))
#           raise Exception('{} cannot consume: message has been garbage collected. [1]'.format(self.name))
        elif self.acceptable(_message):
            # if acceptable, consume/handle the message
                # this subscriber is interested and hasn't seen it before so handle the message
                if self._message_bus.verbose:
                    self._log.info(self._color + Style.NORMAL + 'consuming acceptable message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
                # handle acceptable message
                asyncio.create_task(self.handle_message(_message))
        # if not gc'd, republish the message. If fully-ackd it will be ignored
        if not _message.gcd:
>>>>>>> 0f3dccb5a49acc936dbaea785f14988052a5385a
            await self._message_bus.republish_message(_message)

    # ..........................................................................
    def acceptable(self, message):
        '''
        A filter that returns True if the message has not yet been seen by
        this subscriber and its event type is acceptable.
        '''
        _acceptable_msg = message.event in self._events
        _ackd_by_self   = message.acknowledged_by(self)
        if _acceptable_msg:
            if _ackd_by_self:
                self._log.info(self._color + 'NOT ACCEPTABLE: {} (already ackd); event: {};'.format(message.name, message.event.description) \
                        + Fore.WHITE + Style.BRIGHT + '\t not acked? {}; acceptable event? {}'.format(not _ackd_by_self, _acceptable_msg))
                return False
            else:
                self._log.info(self._color + 'ACCEPTABLE: {}; event: {};'.format(message.name, message.event.description) \
                        + Fore.WHITE + Style.BRIGHT + '\t acked? {}; acceptable event? {}'.format(message.acknowledged_by(self), _acceptable_msg))
                return True
        else:
            self._log.info(self._color + 'NOT ACCEPTABLE: {} (ignored event: {});'.format(message.name, message.event.description) \
                    + Fore.WHITE + Style.BRIGHT + '\t not acked? {}; acceptable event? {}'.format(not _ackd_by_self, _acceptable_msg))
            return False

    # ................................................................
    async def handle_message(self, message):
        '''
        Kick off various tasks to consume (process) the message by first creating
        an asyncio event. Tasks are then created for process_message() followed
        by cleanup_message(). If the latter is overridden it should also called
        by the subclass method as it flags the message as expired. Once these
        tasks have been created the asyncio event flag is set, indicating that
        the message has been consumed.

        The message is acknowledged if this subscriber has subscribed to the
        message's event type and has not seen this message before, or if it
        is not subscribed to the event type (i.e., the message is ignored).
        We don't acknowledge more than once.

        :param message:  the message to consume.
        '''
<<<<<<< HEAD
        if message.gcd:
            self._log.warning('cannot _consume: message has been garbage collected. [2]')
            return
        if self._message_bus.verbose:
            self._log.info(self._color + 'HANDLE_MESSAGE:' + Fore.WHITE + ' {}; event: {}'.format(message.name, message.event.description))

#       # acknowledge we've seen the message
#       self._log.info(self._color + Style.NORMAL + 'ack accepted message:' + Fore.WHITE + ' {}; event: {}'.format(message.name, message.event.description))
#       message.acknowledge(self)
=======
        if self._message_bus.verbose:
            self._log.info(self._color + 'HANDLE_MESSAGE:' + Fore.WHITE + ' {}; event: {}'.format(message.name, message.event.description))

        if message.gcd:
            raise Exception('cannot _consume: message has been garbage collected. [2]')

        # acknowledge we've seen the message
        self._log.info(self._color + Style.NORMAL + 'ack accepted message:' + Fore.WHITE + ' {}; event: {}'.format(message.name, message.event.description))
        message.acknowledge(self)
>>>>>>> 0f3dccb5a49acc936dbaea785f14988052a5385a

        _event = asyncio.Event()
        print(Fore.RED + 'BEGIN event tracking for message:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))

        self._log.info(self._color + 'creating task for processing message:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))
        asyncio.create_task(self.process_message(message, _event))

        self._log.info(self._color + 'creating task for cleanup after message:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))
        asyncio.create_task(self.cleanup_message(message, _event))

        # now stop caring about the message and deal solely with its payload
        _payload = message.payload
        self._log.info(self._color + 'creating task for saving and restarting message payload:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, _payload.event.description))
        results = await asyncio.gather(self._save(message), self._restart_host(_payload), return_exceptions=True)

        self._log.info(self._color + 'handling result from message:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))
        self._handle_results(results, message)

        print(Fore.RED + 'END event tracking for message:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))
        _event.set()

    # ................................................................
    async def process_message(self, message, event):
        '''
        Process the message, i.e., do something with it to change the state of the robot.

        :param message:  the message to process.
        :param event:    the asyncio.Event to watch for message extention or cleaning up.
        '''
        while not event.is_set():
            if message.gcd: # TEMP
                self._log.warning('cannot process: message has been garbage collected. [3]')
                return
            message.process(self)
            if self._message_bus.verbose:
                _elapsed_ms = (dt.now() - message.timestamp).total_seconds() * 1000.0
                self.print_message_info('processing message:', message, _elapsed_ms)
            # want to sleep for less than the deadline amount
            await asyncio.sleep(2)

    # ................................................................
    async def cleanup_message(self, message, event):
        '''
        Cleanup tasks related to completing work on a message.

        :param message:  consumed message that is done being processed.
        :param event:    the asyncio.Event to watch for message extention or cleaning up.
        '''
        # this will block until `event.set` is called
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + '🧀 BEGIN. cleanup: acknowledged {}'.format(message.name))
#       await event.wait()
        # unhelpful simulation of i/o work
#       await asyncio.sleep(random.random())
        self._log.info(self._color + Style.DIM + '🧀 expiring message {}'.format(message.name))
        message.expire()
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + '🧀 END cleanup: acknowledged {}'.format(message.name))

    # ................................................................
    async def _save(self, message):
        '''
        Save the message to a database.

        :param message:  message to be saved.
        '''
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
#       if random.randrange(1, 5) == 3:
#           raise SaveFailed('Could not save event {} from payload'.format(payload.event))
        message.save()
        self._log.info(self._color + Style.DIM + '🍑 saving payload {} into database; saved? {}'.format(message.event.name, message.saved))

    # ................................................................
    async def _restart_host(self, payload):
        '''
        Restart a given host.

        :param payload: consumed event for a particular host to be restarted.
        '''
        self._log.info(self._color + Style.DIM + '🍏 restarting host for event {}...'.format(payload.event.name, payload.restarted))
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
#       if random.randrange(1, 5) == 3:
#           raise RestartFailed('Could not restart {}'.format(payload))
        payload.restart()
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + '🍏 restarted host for event {}; restarted? {}'.format(payload.event.name, payload.restarted))

    # ................................................................
    def _handle_results(self, results, message):
        # 🍎 🍏 🍈  🍋 🍐 🍑 🍓 🍥 🥝 🥚 🥧 🧀 
        if self._message_bus.verbose:
            self._log.info(self._color + '🥝 BEGIN. handling results for message: {}'.format(message.name))
        for result in results:
            if isinstance(result, RestartFailed):
                self._log.error('🍅 retrying for failure to restart: {}'.format(message.hostname))
            elif isinstance(result, SaveFailed):
                self._log.error('🍅 failed to save: {}'.format(message.hostname))
            elif isinstance(result, Exception):
                self._log.error('🍅 handling general error: {}'.format(result))
        if self._message_bus.verbose:
            self._log.info(self._color + '🥝 END. handling results for message: {}'.format(message.name))

    # ................................................................
    def get_formatted_time(self, label, value):
       if value is None:
           return ''
       elif value > 1000.0:
           return '\n' + LOG_INDENT + Fore.RED + label + '\t{:4.3f}s'.format(value/1000.0)
       else:
           return '\n' + LOG_INDENT + label + '\t{:4.3f}ms'.format(value)

    # ................................................................
    def print_message_info(self, info, message, elapsed):
        '''
        Print an informational string followed by details about the message.

        :param info:     the information string
        :param message:  the message to display
        :param elapsed:  the optional elapsed time (in milliseconds) for an operation
        '''
        self._log.info(self._color + info + '\n' \
                + LOG_INDENT + 'id:      \t' + Style.BRIGHT + '{}\n'.format(message.name) + Style.NORMAL \
                + LOG_INDENT + 'event:   \t' + Style.BRIGHT +  ( '{}\n'.format(message.event.description) if message.event else 'n/a: [gc\'d]\n' ) + Style.NORMAL \
                + LOG_INDENT + '{:d} procd;'.format(message.processed) + ' {:d} saved;'.format(message.saved) \
                        + ' {:d} restarted;'.format(message.payload.restarted) + ' acked by: {}'.format(message.print_acks()) \
#               + LOG_INDENT + 'procd:   \t{:d}\n'.format(message.processed) \
#               + LOG_INDENT + 'saved:   \t{:d}\n'.format(message.saved) \
#               + LOG_INDENT + 'restart: \t{}\n'.format(message.restarted) \
#               + LOG_INDENT + 'ackd:    \t{}\n'.format(message.print_acks()) \
#               + LOG_INDENT + 'alive:   \t{:4.3f}ms'.format(message.age) \
                + self.get_formatted_time('alive:   ', message.age) \
                + self.get_formatted_time('elapsed: ', elapsed ))
#      + ( '\n' + LOG_INDENT + 'elapsed: \t{:4.3f}ms'.format(elapsed) if elapsed != None else '' ))

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
        if self._message_bus.is_expired(message) and message.fully_acknowledged:
            if self._message_bus.verbose:
                self.print_message_info('garbage collecting expired, fully-acknowledged message:', message, None)
            return True
        elif self._message_bus.is_expired(message):
            if self._message_bus.verbose:
                self.print_message_info('garbage collecting expired message:', message, None)
            return True
        elif message.fully_acknowledged:
            if self._message_bus.verbose:
                self.print_message_info('garbage collecting fully-acknowledged message:', message, None)
            return True
        else:
            if self._message_bus.verbose:
                self.print_message_info('garbage collector ignoring unprocessed message:', message, None)
            return False

    # ................................................................
    async def consume(self):
        '''
        Overrides the method on Subscriber to explicitly garbage collect
        the message.
        '''
        _peeked_message = await self._message_bus.peek_message()
        if not _peeked_message:
            raise Exception('peek returned none.')
        elif _peeked_message.gcd:
            self._log.warning('message has already been garbage collected. [1]'.format(self.name))
        if self._message_bus.verbose: # TEMP
<<<<<<< HEAD
            self._log.info(self._color + Style.BRIGHT + 'gc-consume() message:' + Fore.WHITE + ' {}; event: {}'.format(_peeked_message.name, _peeked_message.event.description))
        # TODO: only garbage collect (consume) if filter accepts the peeked message
        if self.acceptable(_peeked_message):
            _message = await self._message_bus.consume_message()
            self._message_bus.task_done()
            if self._message_bus.verbose:
                self._log.info(self._color + Style.NORMAL + 'garbage collecting message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
            _message.gc() # mark as garbage collected and don't republish
        else:
            # acknowledge we've seen the message
#           self._log.info(self._color + Style.NORMAL + 'acknowledging message:' + Fore.WHITE + ' {}; event: {} (queue: {:d} elements)'.format(
#                   _peeked_message.name, _peeked_message.event.description, self._message_bus.queue_size))
#           _peeked_message.acknowledge(self)
            pass

=======
            self._log.info(self._color + Style.BRIGHT + 'HANDLE_MESSAGE_GC:' + Fore.WHITE + ' {}; event: {}'.format(message.name, message.event.description))
        if message.gcd:
            raise Exception('cannot garbage collect: message has already been garbage collected.')
        elif self._message_bus.is_expired(message) and message.fully_acknowledged:
            self.print_message_info('garbage collecting expired, fully-acknowledged message:', message, None)
            message.gc() # mark as garbage collected
        elif self._message_bus.is_expired(message):
            self.print_message_info('garbage collecting expired message:', message, None)
            message.gc() # mark as garbage collected
        elif message.fully_acknowledged:
            self.print_message_info('garbage collecting fully-acknowledged message:', message, None)
            message.gc() # mark as garbage collected
        else:
            self.print_message_info('unknown status: garbage collector returning unprocessed message:', message, None)
            # don't mark as garbage collected
>>>>>>> 0f3dccb5a49acc936dbaea785f14988052a5385a

#EOF
