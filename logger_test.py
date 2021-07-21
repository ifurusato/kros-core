#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019-2021 by Murray Altheim. All rights reserved. This file is part
# of the K-Series Robot Operating System (KROS) project, released under the MIT
# License. Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-14
# modified: 2021-04-22
#

import pytest
import sys, traceback
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_logger():

    _log = Logger("test", Level.DEBUG)

    _log.debug('debug.')
    _log.info('info.')
    _log.notice('notice.')
    _log.warning('warning.')
    _log.error('error.')
    _log.critical('critical.')
    _log.heading('title', 'message.', 'info [0/0]')

    # manual re-coloring of output:
    _log.info(Fore.RED + 'RED')
    _log.info(Fore.GREEN + 'GREEN')
    _log.info(Fore.BLUE + 'BLUE')

    _log.info(Fore.YELLOW + 'YELLOW')
    _log.info(Fore.MAGENTA + 'MAGENTA')
    _log.info(Fore.CYAN + 'CYAN')

    _log.info(Fore.BLACK + 'BLACK')
    _log.info(Fore.WHITE + 'WHITE')

#   raise Exception('error message.')

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():
    try:
        test_logger()
    except KeyboardInterrupt:
        print('Ctrl-C caught: test interrupted.')
        sys.exit(0)
    except Exception as e:
        print(Fore.RED + 'Error in test: {} / {}'.format(e, traceback.format_exc()) + Style.RESET_ALL)
        sys.exit(1)
    finally:
        pass

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
if __name__ == "__main__":
    main()

#EOF
