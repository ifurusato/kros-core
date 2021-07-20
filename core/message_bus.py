#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-10
# modified: 2021-07-19
#
# An asyncio-based publish/subscribe-style message bus guaranteeing exactly-once
# delivery for each message. This is done by populating each message with the
# list of subscribers. Each message is subsequently flagged as acknowledged by
# subscribers as they peek and/or consume the message.
#
# Delivery guarantees:
#
#  * At-most-once delivery. This means that a message will never be delivered
#    more than once but messages might be lost.
#  * At-least-once delivery. This means that we'll never lose a message but a
#    message might end up being delivered to a consumer more than once.
#  * Exactly-once delivery. The holy grail of messaging. All messages will be
#    delivered exactly one time.
#
# see; /usr/local/lib/python3.8/asyncio/queues.py
#

import sys, traceback, logging
import asyncio, signal
from datetime import datetime as dt
from colorama import init, Fore, Style
init()
from asyncio.queues import Queue, QueueEmpty

from core.logger import Logger, Level
from core.util import Util
from core.component import Component
from core.event import Event
from core.message import Message
from core.arbitrator import Arbitrator
from core.numbers import Numbers

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MessageBus(Component):
    '''
    An asyncio-based asynchronous message bus.

    :param config:  the application configuration
    :param level:   the optional log level
    '''
    def __init__(self, config, level):
        self._log = Logger("bus", level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        if isinstance(config, dict):
            self._config = config
        else:
            raise ValueError('wrong type for config argument: {}'.format(type(name)))
        if level is Level.DEBUG:
            self._log.debug('logging message bus set to debug level.')
            logging.basicConfig(level=logging.DEBUG)
        self._queue = PeekableQueue(level)
        self._arbitrator = Arbitrator(level)
        # configuration ..........................
        _cfg = config['kros'].get('message_bus')
        self._max_age_ms             = _cfg.get('max_age_ms') # was: 20.0ms
        self._publish_delay_sec      = _cfg.get('publish_delay_sec') # was: 0.01 sec
        self._publishers             = []
        self._subscribers            = []
        self._loop                   = None
        self._last_message_timestamp = None
        self._clip_event_list = False # used for printing only
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def last_message_timestamp(self):
        '''
        Return the timestamp of the moment the last message passed through 
        the message bus. Note that this is not the timestamp of the message
        itself. If no messages has passed through the bus the initial value
        is None.
        '''
        return self._last_message_timestamp

    def update_last_message_timestamp(self):
        '''
        Updates the last_message_timestamp value to dt.now().
        '''
        self._last_message_timestamp = dt.now()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def loop(self):
        '''
        Low level API, do not use.
        '''
        return self._loop

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_all_tasks(self, include_hidden=False):
        '''
        Returns the task list, not including those whose name starts with '__'.
        '''
        _tasks = []
        try:
            for _task in asyncio.all_tasks(loop=self._loop):
                if include_hidden or not _task.get_name().startswith('__'):
                    _tasks.append(_task)
        except RuntimeError:
            self._log.warning('no running loop.')
        return _tasks

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def clear_tasks(self):
        '''
        Clears the task list of any completed tasks.
        '''
#       breakpoint()
        _tasks = self.get_all_tasks()
        if len(_tasks) == 0:
            self._log.debug('no outstanding tasks.')
        else:
            self._log.debug('clearing {:d} task{}...'.format(len(_tasks), ('' if len(_tasks) == 1 else 's')))
            for _task in _tasks:
                if not _task.cancelled():
                    self._log.debug('cancelling task:\t' + Fore.YELLOW + '{}...'.format(_task.get_name()))
                    _task.cancel()
                if _task.done():
                    self._log.debug('removing completed task:\t' + Fore.YELLOW + '{}...'.format(_task.get_name()))
                    _tasks.remove(_task)
                else:
                    self._log.debug('incomplete task:\t' + Fore.BLUE + '{}'.format(_task.get_name()))
            if self._log.is_at_least(Level.DEBUG):
                self._log.debug('{:d} task{} remain{}.'.format(len(_tasks),
                        ('' if len(_tasks) == 1 else 's'),
                        ('s' if len(_tasks) == 1 else '')))
                for _task in _tasks:
                    self._log.debug('unfinished task:\t' + Fore.BLUE + '{}...'.format(_task.get_name()))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def queue(self):
        '''
        Returns the backing message queue.

        IMPORTANT: This is an admin method and should not be considered part of the API.
        '''
        return self._queue

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def queue_empty(self):
        '''
        Returns True if the queue is empty.

        IMPORTANT: This is an admin method and should not be considered part of the API.
        '''
        return self._queue.empty()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def pop_queue(self):
        '''
        Pops the queue but does nothing with the message, if there is one.

        IMPORTANT: This is an admin method and should not be considered part of the API.
        '''
        if self._queue.empty():
            self._log.info('message bus queue is empty.')
        else:
            _message = await self._queue.get()
            self._queue.task_done()
            self._log.info('popped message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.label))
            if self._queue.empty():
                self._log.info('message bus queue is now empty.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def arbitrate(self, payload):
        self._log.info('💎 arbitrating payload {}...'.format(payload.event.name))
        await self._arbitrator.arbitrate(payload)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def queue_size(self):
        return self._queue.qsize()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def clear_queue(self):
        '''
        Clear the message bus of any messages.
        '''
        self._log.info('clearing queue of {:d} message{}.'.format(self._queue.qsize(), '' if self._queue.qsize() == 1 else 's'))
        self._queue.clear()
        self._log.info('queue contains {:d} message{} after clearing.'.format(self._queue.qsize(), '' if self._queue.qsize() == 1 else 's'))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def verbose(self):
        '''
        Returns True if the logger level is INFO.
        '''
        return self._log.level == Level.INFO

    @verbose.setter
    def verbose(self, verbose):
        '''
        Sets the logger level to INFO when verbose, ERROR when not verbose.
        '''
        if verbose:
            self._log.level = Level.INFO
        else:
            self._log.level = Level.ERROR
        # now set the log level of publishers and subscribers to match that of the message bus
        for publisher in self._publishers:
            publisher.set_log_level(self._log.level)
        for subscriber in self._subscribers:
            subscriber.set_log_level(self._log.level)
        self._arbitrator.set_log_level(self._log.level)
        for _controller in self._arbitrator.controllers:
            _controller.set_log_level(self._log.level)

    # publicher ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def register_publisher(self, publisher):
        '''
        Register a message publisher with the message bus.
        '''
        if publisher in self._publishers:
            raise ValueError('publisher list already contains \'{}\''.format(publisher.name))
        self._publishers.append(publisher)
        self._log.info('registered publisher: \'{}\'; {:d} publisher{} in list.'.format( \
                publisher.name, len(self._publishers), 's' if len(self._publishers) > 1 else ''))

    def get_publisher(self, name):
        '''
        Return a registered publisher by name, None if not found.
        '''
        for publisher in self._publishers:
            if publisher.name == name:
                return publisher
        return None

    def print_publishers(self):
        '''
        Print the message publishers that have been registered with the message bus.
        '''
        if not self._publishers:
            self._log.info('no registered publishers.')
            return
        self._log.info('{} publisher{}:'.format(Numbers.from_number(len(self._publishers)), 's' if len(self._publishers) > 1 else ''))
        for publisher in self._publishers:
            self._log.info(Fore.YELLOW + '\t{}'.format(publisher.name) \
                    + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (12 - len(publisher.name)))))
                    + Fore.YELLOW + '{}\t'.format(publisher.enabled)
                    + Fore.CYAN + 'suppressed: '
                    + Fore.YELLOW + '{}'.format(publisher.suppressed))

    def print_arbitrator_info(self):
        '''
        Print the stats available from the arbitrator.
        '''
        self._log.info('arbitrator:' + Fore.YELLOW + '\t{} payloads.'.format(self._arbitrator.count))
        for _controller in self._arbitrator.controllers:
            _controller.print_statistics()

    @property
    def publishers(self):
        return self._publishers

    @property
    def publisher_count(self):
        return len(self._publishers)

    # subscriber ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def register_subscriber(self, subscriber):
        '''
        Register a message subscriber with the message bus.

        Throws a ValueError if the subscriber has already been registered.
        '''
        if subscriber in self._subscribers:
            raise ValueError('subscriber list already contains \'{}\''.format(subscriber.name))
        self._subscribers.insert(0, subscriber)
        self._log.info('registered subscriber: \'{}\'; {:d} subscriber{} in list.'.format( \
                subscriber.name, len(self._subscribers), 's' if len(self._subscribers) > 1 else ''))

    def get_subscriber(self, name):
        '''
        Return a registered subscriber by name, None if not found.
        '''
        for subscriber in self._subscribers:
            if subscriber.name == name:
                return subscriber
        return None

    def print_subscribers(self):
        '''
        Print the message subscribers that have been registered with the message bus.
        '''
        if not self._subscribers:
            self._log.info('no registered subscribers.')
            return
        self._log.info('{} subscriber{}:'.format(Numbers.from_number(len(self._subscribers)), 's' if len(self._subscribers) > 1 else ''))
        for subscriber in self._subscribers:
            if self._clip_event_list:
                _event_list = Util.ellipsis(subscriber.print_events(), 45)
            else:
                _event_list = subscriber.print_events()
            self._log.info(Fore.YELLOW + '\t{}'.format(subscriber.name)
                    + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len(subscriber.name)))))
                    + Fore.YELLOW + '{}\t'.format(subscriber.enabled)
                    + Fore.CYAN + 'suppressed: '
                    + Fore.YELLOW + '{}\t'.format(subscriber.suppressed)
                    + Fore.CYAN + 'listening for: '
                    + Fore.YELLOW + '{}'.format(_event_list))

    @property
    def subscribers(self):
        return self._subscribers

    @property
    def subscriber_count(self):
        return len(self._subscribers)

    # controller ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def register_controller(self, controller):
        '''
        Register a controller with the Arbitrator.
        '''
        self._arbitrator.register_controller(controller)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def is_expired(self, message):
        '''
        Returns True if the message has been manually expired or its age has
        passed the maximum age limit.
        '''
        return message.expired or message.age > self._max_age_ms

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def _start_consuming(self):
        '''
        Enable the publishers and then start the subscribers' consume cycle.

        This is the main event loop and remains active until the message bus
        is disabled.
        '''
        self._enable_publishers()
        self._log.info('starting {:d} subscriber{}...'.format(len(self._subscribers), '' if len(self._subscribers) == 1 else 's'))
        for subscriber in self._subscribers:
            subscriber.start()
        self._log.info('starting consume loop with {:d} subscriber{}...'.format(len(self._subscribers), '' if len(self._subscribers) == 1 else 's'))
        while self.enabled:
            for subscriber in self._subscribers:
                self._log.debug('publishing to subscriber {}...'.format(subscriber.name))
                await subscriber.consume()
                self._log.debug('published to subscriber {}...'.format(subscriber.name))
        self._log.info('completed consume loop with {:d} subscriber{}...'.format(len(self._subscribers), '' if len(self._subscribers) == 1 else 's'))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _enable_publishers(self):
        self._log.info('enabling {:d} publisher{}...'.format(len(self._publishers), '' if len(self._publishers) == 1 else 's'))
        for publisher in self._publishers:
            publisher.start()
            if not publisher.enabled:
                publisher.enable()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_system_status(self):
        '''
        Prints the current system status to the console.
        '''
        self.print_task_info()
        self.print_publishers()
        self.print_subscribers()
        self.print_arbitrator_info()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_task_info(self):
        self._log.info('in queue:    \t' + Fore.YELLOW + '{:d} message{}.'.format(self._queue.qsize(), '' if self._queue.qsize() == 1 else 's'))
        _tasks = self.get_all_tasks()
        if len(_tasks) == 0:
            self._log.info('active tasks:\t' + Fore.YELLOW + 'none.')
        else:
            if len(_tasks) == 1:
                self._log.info('active tasks:\t' + Fore.YELLOW + '1 remains:')
            else:
                self._log.info('active tasks:\t' + Fore.YELLOW + '{:d} remain:'.format(len(_tasks)))
            for _task in _tasks:
                self._log.info(Fore.YELLOW + '    \t\t{};  \t'.format(_task.get_name()) + Fore.BLACK + ' done? {}'.format(_task.done()))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def peek_message(self):
        '''
        Asynchronously waits until it peeks a message from the queue. This
        does not remove the message from the queue.
        '''
        return await self._queue.peek()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def consume_message(self):
        '''
        Asynchronously waits until it pops a message from the queue.

        NOTE: calls to this function should be await'd, and every call should
        correspond with a subsequent call to consumed().
        '''
        return self._queue.get()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def consumed(self):
        '''
        Every call to consume_message() should correspond with a call to consumed().
        This calls the asyncio.queue.task_done() method.
        '''
        self._queue.task_done()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def publish_message(self, message):
        '''
        Asynchronously publishes the Message to the MessageBus, and therefore to any Subscribers.

        NOTE: calls to this function should be await'd.
        '''
#       if ( message.event is not Event.CLOCK_TICK and message.event is not Event.CLOCK_TOCK ):
        self._log.info('rx request to publish message: {}'.format(message.name)
                + ' (event: {}; age: {:d}ms);'.format(message.event.label, message.age))
        _put_task = asyncio.create_task(self._queue.put(message), name='publish-message-{}'.format(message.name))
        # the first time the message is published we update the 'last_message_timestamp'
        self.update_last_message_timestamp()
        self._log.info(Style.DIM + 'created task: {}'.format(_put_task.get_name()))
        await asyncio.sleep(self._publish_delay_sec)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def republish_message(self, message):
        '''
        Asynchronously re-publishes a Message to the MessageBus, making it
        available again to any Subscribers.

        NOTE: calls to this function should be await'd.
        '''
#       self._log.debug('republishing message: {} (event: {}; age: {:d}ms);'.format(message.name, message.event.label, message.age))
        asyncio.create_task(self._queue.put(message), name='republish-message-{}'.format(message.name))
        # when the message is republished we also update the 'last_message_timestamp'
        self.update_last_message_timestamp()
        self._log.debug('republished message: {} (event: {}; age: {:d}ms);'.format(message.name, message.event.label, message.age))

    # exception handling ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def handle_exception(self, loop, context):
        self._log.error('handle exception on loop: {}'.format(loop))
        # context["message"] will always be there; but context["exception"] may not
        _exception = context.get('exception', context['message'])
        if _exception != None:
            self._log.error('caught {}: {}\n{}'.format(type(_exception), _exception, traceback.print_stack()))
        else:
            self._log.error('caught exception: {}'.format(context.get('message')))
        if loop.is_running() and not loop.is_closed():
            asyncio.create_task(self.shutdown(loop), name='shutdown-on-exception')
        else:
            self._log.info("loop already shut down.")

    # shutdown ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    async def shutdown(self, signal=None):
        '''
        Cleanup tasks tied to the service's shutdown.
        '''
        if signal:
            self._log.info('received exit signal {}...'.format(signal))
        self._log.info(Fore.RED + 'nacking outstanding tasks...' + Style.RESET_ALL)
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        self._log.info(Fore.RED + 'cancelling {:d} outstanding tasks...'.format(len(tasks)) + Style.RESET_ALL)
        _result = await asyncio.gather(*tasks, return_exceptions=True)
        self._log.info(Fore.RED + 'stopping loop...; result: {}'.format(_result) + Style.RESET_ALL)
        self._loop.stop()
        self._log.info(Fore.RED + 'shutting down...' + Style.RESET_ALL)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get_task_by_name(self, name):
        '''
        A convenience method that returns the first found instance of a task
        with the given name, otherwise null (None).
        '''
        if name is None:
            raise ValueError('null name argument.')
        for _task in asyncio.all_tasks():
            if _task.get_name() == name:
                return _task
        return None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        if not self.closed:
            Component.enable(self)
            # this call will block
            self._get_event_loop()
            self._log.info('exited forever loop.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_event_loop(self):
        '''
        Return the asyncio event loop, starting it if it is not already running.

        Calling this method will basically start the OS, blocking until disabled.
        '''
        if not self._loop:
            self._log.debug('creating asyncio task loop...')
            self._loop = asyncio.get_event_loop()
            if self._log.level is Level.DEBUG:
                self._loop.set_debug(True) # also set asyncio debug
            # may want to catch other signals too
            signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
            for s in signals:
                self._loop.add_signal_handler(
                    s, lambda s = s: asyncio.create_task(self.shutdown(s), name='shutdown'),)
            self._loop.set_exception_handler(self.handle_exception)
            self._loop.create_task(self._start_consuming(), name='__event_loop__')
        if not self._loop.is_running():
            self._log.debug('starting asyncio task loop...')
            self._loop.run_forever()
        return self._loop

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def disable(self):
        '''
        NOTE: we are at this point incidentally tying publishing with
        the enabled state of the publisher, and subscribing with the
        enabled state of the subscriber. This may not be desired.
        '''
        if self.enabled:
            Component.disable(self)
            self._log.info('disabling {:d} publishers...'.format(len(self._publishers)))
            for publisher in self._publishers:
                publisher.disable()
            self._log.info('disabling {:d} subscribers...'.format(len(self._subscribers)))
            for subscriber in self._subscribers:
                subscriber.disable()
            if self._loop and self._loop.is_running():
                self._loop.stop()
            self._log.info('disabled.')
            self.clear_queue()
            self.clear_tasks()
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class PeekableQueue(Queue):
    '''
    Extends the asyncio Queue to add peek() and clear() methods.
    '''
    def __init__(self, level=Level.INFO):
        Queue.__init__(self, maxsize=0)
        self._log = Logger("queue", level)
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    async def peek(self):
        '''
        Returns the message at the top of the queue without removing it.
        If the queue is empty this returns None.

        This actually gets (removes) the message but immediately puts it
        back onto the queue.
        '''
        _message = await self.get()
        self.task_done()
        self.put_nowait(_message)
        return _message

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def clear(self):
        '''
        Clears the queue of any messages, brute-force, without waiting.
        '''
        while not self.empty():
            try:
                self.get_nowait()
            except Empty or QueueEmpty:
                continue
        self._log.info('cleared.')

#EOF
