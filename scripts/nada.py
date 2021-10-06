#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# This Python script doesn't actually generate a script macro, but it will be
# executed by the MacroPublisher if it's been enabled.
#

import sys
from core.logger import Logger, Level

_nada_main_log = Logger('nada-main', Level.ERROR)
_nada_main_log.info('📃 nada script begin.')

def main(argv):

    _nada_main_log.info('📃 main() start...')
    _log = Logger('nada', Level.ERROR)
    _log.info('📃 main() this doesn\'t get executed.')

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
_nada_main_log.info('📃 main test...')
if __name__== "__main__":
    main(sys.argv[1:])
elif __name__== "core.macro_publisher":
    _nada_main_log.info('📃 this script is being run from core.macro_publisher...')
else:
    _nada_main_log.info('📃 otherwise __name__: \'{}\''.format(__name__))

_nada_main_log.info('📃 end.')

#EOF
