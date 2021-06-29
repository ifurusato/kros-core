#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-06-29
# modified: 2021-06-29
#

#from abc import ABC, abstractmethod
from core.logger import Logger

# ..............................................................................
class Component(object): # ABC
    '''
    A basic component providing support for enable, disable and close states.
    The Logger is passed in as an argument on the constructor. This is only
    implicitly an abstract class, (not explicitly) because while we expect it
    to be subclassed, but there is no reason to enforce and API or reimplment
    methods unless to hook additional functionality to them.

    The Component is disabled by default, though an optional argument can
    set it True.

    :param logger:  the Logger used for the component
    '''
    def __init__(self, logger, enabled=False):
        self._log     = logger
        self._enabled = enabled
        self._closed  = False

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    def enable(self):
        if not self._closed:
            self._enabled = True
            self._log.info('enabled.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    @property
    def disabled(self):
        return not self._enabled

    def disable(self):
        '''
        Disable this component.
        '''
        if self._enabled:
            self._enabled = False
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    @property
    def closed(self):
        return self._closed

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

#EOF
