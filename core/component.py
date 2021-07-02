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
    A basic component providing support for enable or disable, suppress or
    release, and close flags. The enable/disable and suppress/release differ
    in that in a disabled state a component does not operate at all, whereas
    in a suppressed state it operates as normal but cannot send or receive
    messages. This functionality is provided solely as flags, not enforced by
    this class.

    The Logger is passed in as an argument on the constructor. This is only
    implicitly an abstract class, (not explicitly) because while we expect it
    to be subclassed, but there is no reason to enforce and API or reimplment
    methods unless to hook additional functionality to them.

    The Component is suppressed and disabled by default, though via optional
    constructor arguments either can set be set to True.

    :param logger:  the Logger used for the component
    '''
    def __init__(self, logger, suppressed=True, enabled=False):
        self._log        = logger
        self._suppressed = suppressed
        self._enabled    = enabled
        self._closed     = False

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
    def suppressed(self):
        '''
        Return True if the behaviour is suppressed.
        '''
        return self._suppressed

    def release(self):
        '''
        Releases (un-suppresses) the component.
        '''
        self._suppressed = False
        self._log.info('released.')

    def suppress(self):
        '''
        Suppresses the component.
        '''
        self._suppressed = True
        self._log.info('suppressed.')

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
