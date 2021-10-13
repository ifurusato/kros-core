#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-09-25
# modified: 2021-09-27
#

#import queue
import copy
#from copy import deepcopy
from queue import Queue, LifoQueue, Empty, Full
#import upy.heapq as hq # local copy of MicroPython heapq
from colorama import init, Fore, Style
init(autoreset=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class DeQueue(object):

    FIFO = QUEUE = 0 # use FIFO queue
    LIFO = STACK = 1 # use LIFO queue (like a stack)

    '''
    A "double-ended" FIFO or LIFO queue based on the CPython Queue class.

    :param maxsize:   the optional maximum length of the queue.
    :param mode:      uses a FIFO (default) queue or LIFO if thus specified
    '''
    def __init__(self, maxsize=-1, mode=FIFO):
        self._maxsize = maxsize
        self._mode = mode
        if mode == DeQueue.LIFO: # implemented as LIFO stack
            self._queue = LifoQueue(maxsize)
        else: # implemented as FIFO queue
            self._queue = Queue(maxsize)
        self._backing_queue = self._queue.queue

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def queue(self):
        '''
        Return the backing queue.
        '''
        return self._backing_queue

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def iterator(self):
        '''
        Return an iterator over the entries in the queue.
        '''
        return self._queue

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def size(self):
        '''
        Return the size of the queue.
        '''
        return self._queue.qsize()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def clear(self):
        '''
        Clears the contents of the queue.
        '''
        self._queue.clear()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def empty(self):
        '''
        Returns True if the queue is empty.
        '''
        return self.size == 0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def full(self):
        '''
        Returns True if the queue has reached its maximum length.
        '''
        return self._queue.full()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def peek(self):
        '''
        Return the next item on the queue without getting it.
        This functions correctly for either a FIFO queue or a LIFO stack.
        '''
        if self.empty():
            raise Empty()
        if self._mode == DeQueue.FIFO:
            return self._backing_queue[0]
        elif self._mode == DeQueue.LIFO: # stack
            return self._backing_queue[self.size-1]

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def poll(self):
        '''
        Return the next item on the queue.
        '''
        if self.empty():
            raise Empty()
        if self._mode == DeQueue.LIFO:
            raise TypeError('poll() unsuppported in LIFO mode (stack), use pop() or the more general get().')
        return self._queue.get(self.size-1)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def put_as_set(self, item):
        '''
        This puts the item onto the queue only if it doesn't already exist,
        creating a Set behaviour. This doesn't change the order of the existing
        items in the queue.
        '''
        if item not in self._queue:
            self.put(item)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def push(self, item):
        '''
        An alias for put(item).
        '''
        self.put(item)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def put(self, item):
        '''
        Put the item onto the queue.
        '''
        if self.full():
            raise Full()
        self._queue.put(item)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def pop(self):
        '''
        An alias for get().
        '''
        if self._mode == DeQueue.FIFO:
            raise TypeError('pop() unsuppported in FIFO mode (queue), use poll() or the more general get().')
        return self.get()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get(self):
        '''
        Get the next item from the queue.
        '''
        if self.empty():
            raise Empty()
        return self._queue.get()

    def __deepcopy__(self, memo):
        print(Fore.BLUE + '🍏 DeQueue.__deepcopy__: a. memo type: {}'.format(type(memo)))
        _copy = DeQueue(maxsize=self._maxsize, mode=self._mode)
        print(Fore.BLUE + '🍏 DeQueue.__deepcopy__: b. backing queue type: {}'.format(type(self._backing_queue)))
        _copy._queue = copy.copy(self._queue)
        _copy._queue.queue = copy.deepcopy(self._backing_queue)
        print(Fore.BLUE + '🍏 DeQueue.__deepcopy__: c. ')

        # perform a deep copy of the backing queue
        while not self._queue.empty():
                 _copy._queue.put(self._queue.get())
                 self._queue.task_done()

        print(Fore.BLUE + '🍏 DeQueue.__deepcopy__: d. ID of self: {}; _copy: {}'.format(id(self), id(_copy)))
#       queue._maxsize = self._maxsize
#       queue._mode    = self._mode
#       queue._backing_queue = copy.deepcopy(self._backing_queue)
        return _copy

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   def replace(self, item):
#       '''
#       Pop and return the current smallest value, and add the new item;
#       the queue size is unchanged.
#       '''
#       return hq.heapreplace(self._queue, item)
#
#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   def putget(self, item):
#       '''
#       Fast version of a put (push) followed by a get (pop).
#       '''
#       return hq.heappushpop(self._queue, item)
#
#    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   @staticmethod
#   def queueify(x):
#       '''
#       Transform list into a queue (maxheap), in-place, in O(len(x)) time.
#       '''
#       hq.heapify(x)

    # unimplemented...

#   def nlargest(n, iterable):
#   def nsmallest(n, iterable):
#   def merge(*iterables):
#   def nsmallest(n, iterable, key=None):
#   def nlargest(n, iterable, key=None):

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#class Empty(Exception):
#    '''
#    An exception thrown when an action is taken upon an empty queue.
#    '''
#    pass
#
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#class Full(Exception):
#    '''
#    An exception thrown when the queue would overflow upon fulfilling an action.
#    '''
#    pass

#EOF
