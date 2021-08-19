#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-07-13
# modified: 2021-07-13
#

import os, psutil
from pathlib import Path
from colorama import init, Fore, Style
init()

from core.logger import Level, Logger

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class System(object):
    '''
    A collection of system control/info/statistical methods.
    '''
    def __init__(self, kros, level=Level.INFO):
        self._log = Logger('system', level)
        self._kros = kros
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_nice(self):
        # set KROS as high priority process
        self._log.info('setting process as high priority...')
        proc = psutil.Process(os.getpid())
        proc.nice(10)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_sys_info(self):
        self._log.info('kros: \t' + Fore.YELLOW + 'state: {}; enabled: {}'.format(self._kros.state, self._kros.enabled))
        _M = 1000000
        _vm = psutil.virtual_memory()
        self._log.info('virtual memory: \t' + Fore.YELLOW + 'total: {:4.1f}MB; available: {:4.1f}MB ({:5.2f}%); used: {:4.1f}MB; free: {:4.1f}MB'.format(\
                _vm[0]/_M, _vm[1]/_M, _vm[2], _vm[3]/_M, _vm[4]/_M))
        # svmem(total=n, available=n, percent=n, used=n, free=n, active=n, inactive=n, buffers=n, cached=n, shared=n)
        _sw = psutil.swap_memory()
        # sswap(total=n, used=n, free=n, percent=n, sin=n, sout=n)
        self._log.info('swap memory:    \t' + Fore.YELLOW + 'total: {:4.1f}MB; used: {:4.1f}MB; free: {:4.1f}MB ({:5.2f}%)'.format(\
                _sw[0]/_M, _sw[1]/_M, _sw[2]/_M, _sw[3]))
        temperature = self.read_cpu_temperature()
        if temperature:
            self._log.info('cpu temperature:\t' + Fore.YELLOW + '{:5.2f}°C'.format(temperature))

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def read_cpu_temperature(self):
        temp_file = Path('/sys/class/thermal/thermal_zone0/temp')
        if temp_file.is_file():
            with open(temp_file, 'r') as f:
                data = int(f.read())
                temperature = data / 1000
                return temperature
        else:
            return None

#EOF
