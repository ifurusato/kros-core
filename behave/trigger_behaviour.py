#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2022-07-12
# modified: 2021-07-12
#

from enum import Enum

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TriggerBehaviour(Enum):
    '''
    Indicates what the Behaviour should do when triggered.
    '''
    SUPPRESS = ( 0, "suppress")
    RELEASE  = ( 1, "release")
    TOGGLE   = ( 2, "toggle")

    # ignore the first param since it's already set by __new__
    def __init__(self, num, name):
        self._name = name

    # this makes sure the name is read-only
    @property
    def name(self):
        return self._name

#EOF
