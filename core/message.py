#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-10
# modified: 2021-03-16
#
# NOTE: to guarantee exactly-once delivery each message must contain a list
# of the identifiers for all current subscribers, with each subscriber 
# acknowledgement removing it from that list.
#

import string, uuid, random
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.event import Event
from core.subscriber import Subscriber

# ..............................................................................
class Message(object):
    '''
    Don't create one of these directly: use the MessageFactory class.
    '''

    ID_CHARACTERS = string.ascii_uppercase + string.digits

    def __init__(self, event, value):
        if event is None:
            raise ValueError('null event argument.')
        self._payload       = Payload(event, value)
        self._timestamp     = dt.now()
        self._message_id    = uuid.uuid4()
        # generate instance name
        _host_id = "".join(random.choices(Message.ID_CHARACTERS, k=4))
        _instance_name = 'id-{}'.format(_host_id)
        self._instance_name = _instance_name
        self._sent          = 0
        self._expired       = False
        self._gc            = False
        self._processors    = {} # list of processor names who've processed message
        self._subscribers   = {} # list of subscriber names who've acknowledged message

    # ..........................................................................
    def set_subscribers(self, subscribers):
        '''
        Set the list of expected subscribers to this message.
        '''
        for subscriber in subscribers:
            self._subscribers[subscriber] = False

    # timestamp     ............................................................

    @property
    def timestamp(self):
        return self._timestamp

    # age      .................................................................

    @property
    def age(self):
        _age_ms = (dt.now() - self._timestamp).total_seconds() * 1000.0
        return int(_age_ms)

    # message_id    ............................................................

    @property
    def message_id(self):
        return self._message_id

    # processed     ............................................................

    def print_procd(self):
        '''
        Returns a pretty-printed list of processors that have processed
        this message, or '[none]' if none.
        '''
        _list = []
        for processor in self._processors:
            if self._processors[processor]:
                _list.append('{} '.format(processor.name))
        return ''.join(_list) if len(_list) > 0 else '[none]'

    @property
    def processed(self):
        return len(self._processors)

    def process(self, processor):
        '''
        Sets the flag that the given processor has finished processing this
        message.
        '''
        if processor in self._processors:
            raise Exception('message {} already processed by {}.'.format(self.name, processor.name))
        else:
            self._processors[processor] = True

    # expired       ............................................................

    @property
    def expired(self):
        return self._expired

    def expire(self):
#       print(Fore.CYAN + 'expire: {}'.format(self.name) + Style.RESET_ALL)
        self._expired = True

    # garbage collection   .....................................................

    @property
    def gcd(self):
        return self._gc

    def gc(self):
        '''
        Garbage collect this message. This sets the 'gc' flag and nullifies
        the event and value properties so no further processing is possible.
        '''
#       print(Fore.CYAN + 'gc: {}'.format(self.name) + Style.RESET_ALL)
        if self._gc:
            raise Exception('already garbage collected.')
        self._gc = True

    # acknowledged  ............................................................

    def print_acks(self):
        '''
        Returns a pretty-printed list of subscribers that have acknowledged
        this message, or '[none]' if none.
        '''
        _list = []
        for subscriber in self._subscribers:
            if self._subscribers[subscriber]:
                _list.append('{} '.format(subscriber.name))
        return ''.join(_list) if len(_list) > 0 else '[none]'

#   @property
#   def acknowledgements(self):
#       return self._subscribers

    @property
    def unacknowledged_count(self):
        _count = 0
        for subscriber in self._subscribers:
            if not self._subscribers[subscriber]:
                _count += 1
        return _count

    # ..........................................................................
    @property
    def fully_acknowledged(self):
        '''
        Returns True if the message has been acknowledged by all subscribers,
        i.e., no subscriber flags remain set as False, ignoring the garbage
        collector.
        '''
        for subscriber in self._subscribers:
            if subscriber.is_gc:
                continue
            elif not self._subscribers[subscriber]:
                return False
        return True

    def acknowledged_by(self, subscriber):
        '''
        Returns True if the message has been acknowledged by the specified subscriber.
        '''
        for subscr in self._subscribers:
            if subscr == subscriber and self._subscribers[subscriber] == True:
#               print(Fore.GREEN + 'message {} acknowledged_by subscriber {}; return True.'.format(self.name, subscriber.name) + Style.RESET_ALL)
                return True
#       print(Fore.RED + 'message {} has not been acknowledged by subscriber {}; return False.'.format(self.name, subscriber.name) + Style.RESET_ALL)
        return False

    def acknowledge(self, subscriber):
        '''
        To be called by each subscriber, acknowledging receipt of the message.
        '''
        if not isinstance(subscriber, Subscriber):
            raise Exception('expected subscriber, not {}.'.format(type(subscriber)))
        if len(self._subscribers) == 0:
            raise Exception('no subscribers set ({}).'.format(self._instance_name))
        if self._subscribers[subscriber] is True:
            if subscriber.is_gc:
                print(Fore.YELLOW + 'WARNING: ' + Fore.CYAN + 'message {} already acknowledged by subscriber: {}'.format(self.name, subscriber.name) + Style.RESET_ALL)
            else:
                raise Exception('message {} already acknowledged by subscriber: {}'.format(self.name, subscriber.name))
        else:
            self._subscribers[subscriber] = True
#           print(Fore.GREEN + Style.BRIGHT + 'message {} acknowledged by subscriber {}; still unacknowledged by {:d}.'.format(\
#                   self.name, subscriber.name, self.unacknowledged_count) + Style.RESET_ALL)

    # instance_name ............................................................

    @property
    def name(self):
        '''
        Return the instance name of the message.
        '''
        return self._instance_name

    # event         ............................................................

    @property
    def event(self):
        return self._payload.event

    # payload       ............................................................

    @property
    def payload(self):
        return self._payload

    # sent         .............................................................

    @property
    def sent(self):
        '''
        Returns the number of times this message's payload has been sent to
        the Arbitrator.
        '''
        return self._sent

    def acknowledge_sent(self):
        '''
        To be called when the message's payload has been sent the Arbitrator.
        '''
        self._sent += 1
#       print(Fore.CYAN + 'payload {} sent {:d} times.'.format(self._payload.event.description, self._sent) + Style.RESET_ALL)

# ..............................................................................
class Payload(object):
    '''
    A Message's payload, containing the Event (with priority) and an optional value.
    '''
    def __init__(self, event, value):
        self._event = event
        self._value = value

    # priority      ............................................................

    @property
    def priority(self):
        return self._event.priority

    # event         ............................................................

    @property
    def event(self):
        return self._event

    # value         ............................................................

    @property
    def value(self):
        return self._value

    # equals        ............................................................
    def __eq__(self, other):
        if other is None:
            return False
        print(Fore.GREEN + '👾💚 __eq__() self.value: {}; other.value: {}'.format(self.value, other.value) + Style.RESET_ALL)
        return self.event == other.event and self.value == other.value

#EOF
