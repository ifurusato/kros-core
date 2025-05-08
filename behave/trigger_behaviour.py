#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2022-07-12
# modified: 2025-05-08
#
# An Enum indicating what a Behaviour should do when triggered.

from enum import Enum

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TriggerBehaviour(Enum):
    '''
    Indicates what the Behaviour should do when triggered:

      suppress:  suppress the behaviour
      release:   release the behaviour
      toggle:    toggle the suppress/release state of the behaviour
      execute:   execute the behaviour
      ignore:    ignore the trigger
    '''
    SUPPRESS = ( 0, "suppress")
    RELEASE  = ( 1, "release")
    TOGGLE   = ( 2, "toggle")
    EXECUTE  = ( 3, "execute")
    IGNORE   = ( 4, "ignore")

    # ignore the first param since it's already set by __new__
    def __init__(self, num, name):
        self._name = name

    # this makes sure the name is read-only
    @property
    def name(self):
        return self._name

#EOF
