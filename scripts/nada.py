#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# This Python script doesn't actually generate a script macro, but it will be
# executed by the MacroProcessor if it's been enabled.
#

import sys
from core.logger import Logger, Level

print('📃 nada script begin.')

def main(argv):

    print('📃 main() start...')
    _log = Logger('nada', Level.INFO)
    _log.info('📃 main() this doesn\'t get executed.')

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
print('📃 main test...')
if __name__== "__main__":
    main(sys.argv[1:])
elif __name__== "core.macro":
    print('📃 this script is being run from core.macro...')
else:
    print('📃 otherwise __name__: \'{}\''.format(__name__))

print('📃 end.')

#EOF
