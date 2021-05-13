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

import asyncio, signal, traceback
import sys, logging
from colorama import init, Fore, Style
init()
from asyncio.queues import Queue

from core.logger import Logger, Level
from core.event import Event
from core.message import Message
from core.arbitrator import Arbitrator
from core.subscriber import GarbageCollector

# ..............................................................................
class MessageBus(object):
    '''
    An asyncio-based asynchronous message bus.
    '''
    def __init__(self, level):
        self._log = Logger("bus", level)
        if level is Level.DEBUG:
            self._log.debug('logging message bus set to debug level.')
            logging.basicConfig(level=logging.DEBUG)
            self._loop.set_debug(True) # also set asyncio debug
        self._loop        = asyncio.get_event_loop()
        self._queue       = PeekableQueue(level)
        self._publishers  = []
        self._subscribers = []
        self._tasks       = []
        # may want to catch other signals too
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            self._loop.add_signal_handler(
                s, lambda s = s: asyncio.create_task(self.shutdown(s), name='shutdown'),)
        self._loop.set_exception_handler(self.handle_exception)
        self._garbage_collector = GarbageCollector('gc', Fore.RED, self, Level.INFO)
#       self.register_subscriber(self._garbage_collector)
        self._arbitrator  = Arbitrator(level)
        self._max_age     = 20.0 # ms
        self._verbose     = True
        self._enabled     = True # by default
        self._closed      = False
        self._log.info('creating subscriber task...')
        self._loop.create_task(self.start_consuming(), name='consume-loop')
        self._log.info('ready.')

    # ..........................................................................
    @property
    def loop(self):
        '''
        Low level API, do not use.
        '''
        return self._loop

    # ..........................................................................
    def add_task(self, task):
        self._tasks.append(task)
        self._log.debug('{:d} active tasks.'.format(len(self._tasks)))

    # ..........................................................................
    def clear_tasks(self):
        '''
        Clears the task list of any completed tasks.
        '''
        if len(self._tasks) == 0:
            self._log.info('clear: no outstanding tasks.')
        else:
            self._log.info('clearing {:d} task{}...'.format(len(self._tasks), ('' if len(self._tasks) == 1 else 's')))
            for _task in self._tasks:
                if _task.done():
                    self._log.info('removing completed task:\t' + Fore.YELLOW + '{}...'.format(_task.get_name()))
                    self._tasks.remove(_task)
                else:
                    self._log.warning(Fore.RED + 'task not complete:      \t' + Fore.YELLOW + '{}'.format(_task.get_name()))
            self._log.info('{:d} task{} remain.'.format(len(self._tasks), ('' if len(self._tasks) == 1 else 's')))
            for _task in self._tasks:
                self._log.debug('unfinished task:\t' + Fore.YELLOW + '{}...'.format(_task.get_name()))

    # ..........................................................................
    @property
    def queue(self):
        '''
        Returns the backing message queue.

        IMPORTANT: This is an admin function and should not be considered part of the API.
        '''
        return self._queue

    # ..........................................................................
    @property
    def queue_empty(self):
        '''
        Returns True if the queue is empty.

        IMPORTANT: This is an admin function and should not be considered part of the API.
        '''
        return self._queue.empty()

    # ..........................................................................
    async def pop_queue(self):
        '''
        Pops the queue but does nothing with the message, if there is one.

        IMPORTANT: This is an admin function and should not be considered part of the API.
        '''
        if self._queue.empty():
            self._log.info('message bus queue is empty.')
        else:
            _message = await self._queue.get()
            self._queue.task_done()
            self._log.info('popped message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
            if self._queue.empty():
                self._log.info('message bus queue is now empty.')

    # ..........................................................................
    async def arbitrate(self, payload):
        self._log.debug('arbitrating payload {}...'.format(payload.event.name))
        await self._arbitrator.arbitrate(payload)

    # ..........................................................................
#   @property
#   def queue(self):
#       return self._queue

    @property
    def queue_size(self):
        return self._queue.qsize()

    def clear(self):
        '''
        Clear the message bus of any messages.
        '''
        self._queue.mutex.acquire()
        self._queue.queue.clear()
        self._queue.all_tasks_done.notify_all()
        self._queue.unfinished_tasks = 0
        self._queue.mutex.release()
#       while not self._queue.empty():
#           try:
#               self._queue.get(False)
#           except Empty:
#               continue
#           self._queue.task_done()

    # ..........................................................................
    @property
    def verbose(self):
        return self._verbose

    @verbose.setter
    def verbose(self, verbose):
        self._verbose = verbose

    # ..........................................................................
    def register_publisher(self, publisher):
        '''
        Register a message publisher with the message bus.
        '''
        if publisher in self._publishers:
            raise ValueError('publisher list already contains \'{}\''.format(publisher.name))
        self._publishers.append(publisher)
        self._loop.create_task(publisher.publish(), name='publisher-{}'.format(publisher.name))
        self._log.info('registered publisher \'{}\'; {:d} publisher{} in list.'.format( \
                publisher.name,
                len(self._publishers),
                's' if len(self._publishers) > 1 else ''))

    # ..........................................................................
    def get_publisher(self, name):
        '''
        Return a registered publisher by name.
        '''
        for publisher in self._publishers:
            if publisher.name == name:
                return publisher
        raise NameError('no publisher found with name \'{}\'.'.format(name))

    def print_publishers(self):
        '''
        Print the message publishers that have been registered with the message bus.
        '''
        if not self._publishers:
            self._log.info('no registered publishers.')
            return
        self._log.info('{:d} publisher{}:'.format( \
                len(self._publishers),
                's' if len(self._publishers) > 1 else ''))
        for publisher in self._publishers:
            self._log.info(Fore.YELLOW + '\t{}'.format(publisher.name) \
                    + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len(publisher.name)))))
                    + Fore.YELLOW + '{}\t'.format(publisher.enabled)
                    + Fore.CYAN + 'suppressed: '
                    + Fore.YELLOW + '{}'.format(publisher.suppressed))

    @property
    def publishers(self):
        return self._publishers

    @property
    def publisher_count(self):
        return len(self._publishers)

    # ..........................................................................
    def register_controller(self, controller):
        '''
        Register a controller with the Arbitrator.
        '''
        self._arbitrator.register_controller(controller)

    # ..........................................................................
    def register_subscriber(self, subscriber):
        '''
        Register a message subscriber with the message bus.

        Throws a ValueError if the subscriber has already been registered.
        '''
        if subscriber in self._subscribers:
            raise ValueError('subscriber list already contains \'{}\''.format(subscriber.name))
        self._subscribers.insert(0, subscriber)
        self._loop.create_task(subscriber.consume(), name='subscriber-{}'.format(subscriber.name))
        self._log.info('registered subscriber \'{}\'; {:d} subscriber{} in list.'.format( \
                subscriber.name,
                len(self._subscribers),
                's' if len(self._subscribers) > 1 else ''))

    def print_subscribers(self):
        '''
        Print the message subscribers that have been registered with the message bus.
        '''
        if not self._subscribers:
            self._log.info('no registered subscribers.')
            return
        self._log.info('{:d} subscriber{}:'.format( \
                len(self._subscribers),
                's' if len(self._subscribers) > 1 else ''))
        for subscriber in self._subscribers:
            self._log.info(Fore.YELLOW + '\t{}'.format(subscriber.name)
                    + Fore.CYAN + ' {}enabled: '.format((' ' * max(0, (10 - len(subscriber.name)))))
                    + Fore.YELLOW + '{}\t'.format(subscriber.enabled)
                    + Fore.CYAN + 'listening for: '
                    + Fore.YELLOW + '{}'.format(subscriber.print_events()))
    @property
    def subscribers(self):
        return self._subscribers

    @property
    def subscriber_count(self):
        return len(self._subscribers)

    # ..........................................................................
    def is_expired(self, message):
        '''
        Returns True if the message has been manually expired or its age has
        passed the maximum age limit.
        '''
        return message.expired or message.age > self._max_age

    # ..........................................................................
    async def start_consuming(self):
        '''
        Start the subscribers' consume cycle. This remains active until the
        message bus is disabled.
        '''
        self._log.info('begin {:d} subscribers\' consume cycle...'.format(len(self._subscribers)))
        _sub_list = []
        for subscriber in self._subscribers:
            _sub_list.append(subscriber.consume())

        self._log.info('begin {:d} gathering subscribers\' consume cycle...'.format(len(self._subscribers)))
        await asyncio.gather(*_sub_list, loop=self._loop)
        self._log.info('begin {:d} gathered subscribers\' consume cycle...'.format(len(self._subscribers)))
#       while self._enabled:
#           for subscriber in self._subscribers:
#               self._log.debug('publishing to subscriber {}...'.format(subscriber.name))
#               await subscriber.consume()

    # ..........................................................................
    def print_bus_info(self):
        self._log.info('in queue:    \t' + Fore.YELLOW + '{:d} message{}.'.format(self._queue.qsize(), '' if self._queue.qsize() == 1 else 's'))
        if len(self._tasks) == 0:
            self._log.info('active tasks:\t' + Fore.YELLOW + 'none.')
        else:
            if len(self._tasks) == 1:
                self._log.info('active tasks:\t' + Fore.YELLOW + '1 remains:')
            else:
                self._log.info('active tasks:\t' + Fore.YELLOW + '{:d} remain:'.format(len(self._tasks)))
            for _task in self._tasks:
                self._log.info(Fore.YELLOW + '    \t\t{};  \t'.format(_task.get_name()) + Fore.BLACK + ' done? {}'.format(_task.done()))
        self.print_publishers()
        self.print_subscribers()

    # ..........................................................................
    def peek_message(self):
        '''
        Asynchronously waits until it peeks a message from the queue. This
        does not remove the message from the queue.
        '''
        return self._queue.peek()

    # ..........................................................................
    def consume_message(self):
        '''
        Asynchronously waits until it pops a message from the queue.

        NOTE: calls to this function should be await'd, and every call should
        correspond with a subsequent call to consumed().
        '''
        return self._queue.get()

    # ..........................................................................
    def consumed(self):
        '''
        Every call to consume_message() should correspond with a call to consumed().
        This calls the asyncio.queue.task_done() method.
        '''
        self._queue.task_done()

    # ..........................................................................
    async def publish_message(self, message):
        '''
        Asynchronously publishes the Message to the MessageBus, and therefore to any Subscribers.

        NOTE: calls to this function should be await'd.
        '''
        if ( message.event is not Event.CLOCK_TICK and message.event is not Event.CLOCK_TOCK ):
            self._log.info(Style.BRIGHT + 'publishing message: {}'.format(message.name) + Style.NORMAL + ' (event: {}; age: {:d}ms);'.format(message.event, message.age))
        _result = asyncio.create_task(self._queue.put(message), name='publish-message-{}'.format(message.name))
        self._log.info(Style.DIM + 'result from published message: {}'.format(_result.get_name()))
        await asyncio.sleep(0.005)

    # ..........................................................................
    async def republish_message(self, message):
        '''
        Asynchronously re-publishes a Message to the MessageBus, making it
        available again to any Subscribers.

        NOTE: calls to this function should be await'd.
        '''
        self._log.debug('republishing message: {} (event: {}; age: {:d}ms);'.format(message.name, message.event, message.age))
        asyncio.create_task(self._queue.put(message), name='republish-message-{}'.format(message.name))
        self._log.info('republished message: {} (event: {}; age: {:d}ms);'.format(message.name, message.event, message.age))

    # ..........................................................................
    async def x_garbage_collect(self, message):
        '''
        Explicitly garbage collect the message.
        '''
        await self._garbage_collector.collect(message)

    # exception handling .......................................................
    def handle_exception(self, loop, context):
        self._log.error('handle exception on loop: {}'.format(loop))
        # context["message"] will always be there; but context["exception"] may not
        _exception = context.get('exception', context['message'])
        if _exception != None:
            self._log.error('caught {}: {}'.format(type(_exception), _exception))
        else:
            self._log.error('caught exception: {}'.format(context.get('message')))
        if loop.is_running() and not loop.is_closed():
            asyncio.create_task(self.shutdown(loop), name='shutdown-on-exception')
        else:
            self._log.info("loop already shut down.")

    # shutdown .....................................................................
    async def shutdown(self, signal=None):
        '''
        Cleanup tasks tied to the service's shutdown.
        '''
        if signal:
            self._log.info('received exit signal {}...'.format(signal))
#       self._log.info(Fore.RED + 'closing services...' + Style.RESET_ALL)
        self._log.info(Fore.RED + 'nacking outstanding tasks...' + Style.RESET_ALL)
        tasks = [t for t in asyncio.all_tasks() if t is not
                asyncio.current_task()]
        [task.cancel() for task in tasks]
        self._log.info(Fore.RED + 'cancelling {:d} outstanding tasks...'.format(len(tasks)) + Style.RESET_ALL)
        await asyncio.gather(*tasks, return_exceptions=True)
        self._log.info(Fore.RED + "stopping loop..." + Style.RESET_ALL)
        self._loop.stop()
        self._log.info(Fore.RED + "shutting down..." + Style.RESET_ALL)
#       sys.exit(1) # not really

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._enabled = True
            self._log.info('enabled.')
            if not self._loop.is_running():
                self._log.info('starting asyncio task loop...')
                self._loop.run_forever()
            self._log.info('exited forever loop.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def disable(self):
        '''
        NOTE: we are at this point incidentally tying publishing with
        the enabled state of the publisher, and subscribing with the
        enabled state of the subscriber. This may not be desired.
        '''
        if self._enabled:
            self._enabled = False
            for publisher in self._publishers:
                publisher.disable()
            for subscriber in self._subscribers:
                subscriber.disable()
            if self._loop.is_running():
                self._loop.stop()
            self._log.info('disabled.')
            self.clear_tasks()
            for _task in self._tasks:
                if not _task.cancelled():
                    _task.cancel()
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

# ..............................................................................
class PeekableQueue(Queue):

    def __init__(self, level=Level.INFO):
        super().__init__(maxsize=0, loop=None)
        self._log = Logger("q", level)
        self._log.info('ready.')

    # ..........................................................................
    async def peek(self):
        _message = await self.get()
        self.task_done()
        await self.put(_message)
        return _message

#EOF
