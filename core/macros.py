#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2021-09-23
# modified: 2021-10-07
#
# A collection of classes related to macro scripting.
#

from copy import deepcopy
from colorama import init, Fore, Style
init(autoreset=True)

from core.logger import Logger, Level
from core.event import Event
from core.dequeue import DeQueue

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

#   # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
#   def get_macro(self, name):
#       for _macro in self._macros.iterator:
#           if _macro.name == name:
#               return _macro
#       return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Macro(object):
    '''
    A named, queued container for Statements.

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
    def poll(self):
        return self._queue.poll()

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_event(self, event, duration_ms):
        '''
        Add an Event to the queue.
        '''
        _statement = Statement('stmt-{:d}'.format(self.size), event, duration_ms)
        self._queue.put(_statement)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_function(self, function, duration_ms):
        '''
        Add a lambda function to the queue, encapsulated in an Event:

          LAMBDA = ( 20, "lambda function", 5,  Group.LAMBDA )

        '''
        _statement = Statement('stmt-{:d}'.format(self.size), function, duration_ms)
        self._queue.put(_statement)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def __deepcopy__(self, memo):
        print(Fore.BLUE + '🍎 Macro.__deepcopy__: a. name: {}'.format(self.name))
        _copy = Macro(self.name, self.description, None)
        print(Fore.BLUE + '🍎 Macro.__deepcopy__: b. deepcopy queue...')
        _qeueu_copy = deepcopy(self._queue)
        print(Fore.BLUE + '🍎 Macro.__deepcopy__: c. deepcopy complete.')

        print(Fore.BLUE + '🍎 Macro.__deepcopy__: d. self ID: {}; copy ID: {}'.format(id(self), id(_copy)))
#       for _key, _value in _macro.items():
#           print('key: {}; value: {}'.format(_key, _value))
#       raise Exception('unimplemented: {}'.format(_copy))
        print(Fore.BLUE + '🍎 Macro.__deepcopy__: e. self._queue.size: {:d}; _copy._queue.size: {:d}'.format(self._queue.size, _copy._queue.size))
        print(Fore.BLUE + '🍎 Macro.__deepcopy__: f. id(self._queue): {:d}; id(_copy._queue): {:d}'.format(id(self._queue), id(_copy._queue)))
        return _copy

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Statement(object):
    '''
    Documentation.
    '''
    def __init__(self, label, command, duration_ms):
        '''
        Command can be either a lambda or an Event.
        '''
        self._label         = label
        self._duration_ms   = duration_ms
        if isinstance(command, Event):
            self._is_lambda = False
            self._event     = command
            self._function  = None
        elif callable(command): # is lambda
            self._is_lambda = True
            self._event     = Event.LAMBDA
            self._function  = command
            # LAMBDA = ( 20, "lambda function", 5,   Group.LAMBDA ) # with lambda as value
        else:
            raise TypeError('expected an event or a lambda as an argument, not a {}'.format(type(command)))

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

    def __hash__(self):
        return hash(self._event)

    def __eq__(self, other):
        return isinstance(other, Statement) and self.__hash__() is other.__hash__()

    def __deepcopy__(self, memo):
        if self._is_lambda:
            print(Fore.BLUE + '🍊 Statement.__deepcopy__() copy lambda.')
            return Statement(self.label, self._function, self.duration_ms)
        else:
            print(Fore.BLUE + '🍊 Statement.__deepcopy__() copy event.')
            return Statement(self.label, Event.LAMBDA, self.duration_ms)

#EOF
