#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2021-09-23
# modified: 2021-10-15
#
# A collection of classes related to macro scripting, including Statement,
# Macro, Macros, and MacroLibrary.
#

from copy import deepcopy
from colorama import init, Fore, Style
init(autoreset=True)

from core.logger import Logger, Level
from core.event import Event
from core.stringbuilder import StringBuilder
from core.dequeue import DeQueue

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Statement(object):
    '''
    A single Statement in a Macro. This either executes a lambda function or
    publishes an Event for a specified duration in milliseconds.

    If a lambda function is specified the Event value will automatically be
    set to Event.LAMBDA, so it can be left as None.

    :param label:         the label or description of the statement
    :param event:         the Event to publish for the Statement
    :param function:      the lambda function to execute for the Statement
    :param duration_ms:   the duration in milliseconds of the Statement
    '''
    def __init__(self, label=None, event=None, function=None, duration_ms=None):
        '''
        Command can be either a lambda or an Event.
        '''
        self._label         = label
        self._function      = function
        if self._function:
            self._event = Event.LAMBDA
        else:
            self._event = event
        self._duration_ms   = duration_ms
        self._is_lambda     = function != None

    @property
    def label(self):
        return self._label

    @property
    def is_lambda(self):
        return self._is_lambda

    @property
    def duration_ms(self):
        return self._duration_ms

    @property
    def function(self):
        return self._function

    @property
    def event(self):
        return self._event

    def __lt__(self, other):
        return self.__hash__() < other.__hash__()

    def __eq__(self, other):
        return isinstance(other, Statement) and self.__hash__() == other.__hash__()

    def __hash__(self):
        return hash((self._label, self._duration_ms, self._is_lambda, self._event, self._function))

    def __deepcopy__(self, memo):
        return Statement(label=self.label, event=self.event, function=self.function, duration_ms=self.duration_ms)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __str__(self):
        _sb = StringBuilder('Statement[', indent=10, delim='\n')
        _sb.append('id={}'.format(id(self)))
        _sb.append('hash={}'.format(hash(self)))
        _sb.append('label={}'.format(self._label))
        _sb.append('is_lambda={}'.format(self._is_lambda))
        _sb.append('event={}'.format(self._event))
        _sb.append('duration={}ms'.format(self._duration_ms))
        _sb.append('function={}'.format('lambda' if self._function else 'none'))
        _sb.append(']', indent=8, delim=StringBuilder.NONE)
        return _sb.to_string()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Macro(object):
    '''
    A named, queued container for Statements.

    This can also contain an optional Payload.

    :param name:              the name of the macro
    :param description:       an optional description of the macro
    :param queue:             an optional initial queue
    :param statement_limit:   optionally limits the size of the queue (unlimited/-1 default)
    '''
    def __init__(self, name, description=None, queue=None, statement_limit=-1):
        self._name = name
        self._description = description
        if queue:
            self._queue = queue
        else:
            self._queue = DeQueue(maxsize=statement_limit, mode=DeQueue.QUEUE)
        self._payload = None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return self._name

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def size(self):
        return self._queue.size

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def empty(self):
        return self._queue.empty()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def description(self):
        return self._description

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def payload(self):
        return self._payload

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_payload(self, payload):
        self._payload = payload

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def poll(self):
        return self._queue.poll()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_event(self, event, duration_ms=0):
        '''
        Add an Event to the queue.
        '''
        _statement = Statement(label='stmt-{}'.format(chr(97 + self.size)), event=event, function=None, duration_ms=duration_ms)
        self._queue.put(_statement)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_function(self, function, duration_ms=0):
        '''
        Add a lambda function to the queue, encapsulated in an Event:
        '''
        _statement = Statement(label='stmt-{}'.format(chr(97 + self.size)), event=Event.LAMBDA, function=function, duration_ms=duration_ms)
        self._queue.put(_statement)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __eq__(self, other):
        return isinstance(other, Macro) \
                and self.__hash__() == other.__hash__()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __hash__(self):
        return hash((self._name, self._description, self._queue.size))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __str__(self):
        _sb = StringBuilder('Macro[', indent=2, delim='\n')
        _sb.append('id={}'.format(id(self)))
        _sb.append('hash={}'.format(hash(self)))
        _sb.append('name={}'.format(self._name))
        _sb.append('description={}'.format(self._description))
        _sb.append('queue:')
        _sb.append(self._queue)
        _sb.append(']', indent=4, delim=StringBuilder.NONE)
        return _sb.to_string()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __deepcopy__(self, memo):
        return Macro(self.name, self.description, deepcopy(self._queue))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Macros(DeQueue):
    '''
    A container for Macros.
    '''
    def __init__(self):
        self._macros = DeQueue(mode=DeQueue.QUEUE)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def size(self):
        return self._macros.size

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def empty(self):
        return self.size == 0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def put(self, macro):
        '''
        Add a Macro to the dictionary.
        '''
        self._macros.put(macro)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get(self):
        return self._macros.get()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MacroLibrary():
    '''
    A reference library for named Macros.

    '''
    def __init__(self, level=Level.INFO):
        self._log = Logger('macro-lib', level)
        self._macros = {}

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def size(self):
        return len(self._macros)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def empty(self):
        return self.size == 0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def put(self, macro):
        '''
        Add a Macro to the dictionary.
        '''
        if isinstance(macro, Macro):
            self._macros[macro.name] = macro
        else:
            raise TypeError('expected macro.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def get(self, name):
        for _name, _macro in self._macros.items():
            if _name == name:
                return _macro
        return None

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_info(self):
        if self.empty():
            self._log.info('macro library:\t' + Fore.YELLOW + 'empty.')
        else:
            self._log.info('macro library:')
            for _name, _macro in self._macros.items():
                self._log.info(Fore.YELLOW + '\t{} '.format(_name) + Style.DIM + '({:d} statements)'.format(_macro.size)
                        + Style.NORMAL + '{}'.format('\t: ' + _macro.description if _macro.description else ''))

#EOF