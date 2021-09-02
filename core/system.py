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
        global _kros
        self._log = Logger('system', level)
        self._kros = kros
        _kros = kros
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @staticmethod
    def get_kros():
        '''
        This (perversely) provides static method access to the KROS instance
        so we don't have to pass it around.
        '''
        global _kros
        return _kros

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def set_nice(self):
        # set KROS as high priority process
        self._log.info('setting process as high priority...')
        proc = psutil.Process(os.getpid())
        proc.nice(10)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def print_sys_info(self):
        self._log.info('kros:  state: ' + Fore.YELLOW + '{}  \t'.format(self._kros.state.name) \
                + Fore.CYAN + 'enabled: ' + Fore.YELLOW + '{}'.format(self._kros.enabled))
        # disk space ...................
        self._log.info('root file system:')
        _rootfs = psutil.disk_usage('/')
        _div = float(1<<30)
        _div = 1024.0 ** 3
#       self._log.info('  total:  \t' + Fore.YELLOW + '{:>6.2f}GB'.format(_rootfs.total / _div))
#       self._log.info('  used:   \t' + Fore.YELLOW + '{:>6.2f}GB ({}%)'.format((_rootfs.used / _div), _rootfs.percent))
#       self._log.info('  free:   \t' + Fore.YELLOW + '{:>6.2f}GB'.format(_rootfs.free / _div))
        self._log.info('  total: ' + Fore.YELLOW + '{:>4.2f}GB'.format(_rootfs.total / _div) 
                + Fore.CYAN + '; used: ' + Fore.YELLOW + '{:>4.2f}GB ({}%)'.format((_rootfs.used / _div), _rootfs.percent)
                + Fore.CYAN + '; free: ' + Fore.YELLOW + '{:>4.2f}GB'.format(_rootfs.free / _div))
        # memory .......................
        _MB = 1000000
        _vm = psutil.virtual_memory()
        # svmem(total=n, available=n, percent=n, used=n, free=n, active=n, inactive=n, buffers=n, cached=n, shared=n)
        self._log.info('virtual memory:')
#       self._log.info('  total:    \t' + Fore.YELLOW + '{:>6.2f}MB'.format(_vm[0]/_MB))
#       self._log.info('  available:\t' + Fore.YELLOW + '{:>6.2f}MB'.format(_vm[1]/_MB))
#       self._log.info('  used:     \t' + Fore.YELLOW + '{:>6.2f}GB ({:4.1f}%)'.format(_vm[3]/_MB, _vm[2]))
#       self._log.info('  free:     \t' + Fore.YELLOW + '{:>6.2f}GB'.format( _vm[4]/_MB))
        self._log.info('  total: ' + Fore.YELLOW + '{:>4.2f}MB'.format(_vm[0]/_MB)
                + Fore.CYAN + '; available: ' + Fore.YELLOW + '{:>4.2f}MB'.format(_vm[1]/_MB)
                + Fore.CYAN + '; used: ' + Fore.YELLOW + '{:>4.2f}GB ({:4.1f}%)'.format(_vm[3]/_MB, _vm[2])
                + Fore.CYAN + '; free: ' + Fore.YELLOW + '{:>4.2f}GB'.format( _vm[4]/_MB))
        # sswap(total=n, used=n, free=n, percent=n, sin=n, sout=n)
        _sw = psutil.swap_memory()
        self._log.info('swap memory:')
#       self._log.info('  total:  \t' + Fore.YELLOW + '{:>6.2f}MB'.format(_sw[0]/_MB))
#       self._log.info('  used:   \t' + Fore.YELLOW + '{:>6.2f}MB ({:3.1f}%)'.format(_sw[1]/_MB, _sw[3]))
#       self._log.info('  free:   \t' + Fore.YELLOW + '{:>6.2f}MB'.format(_sw[2]/_MB))
        self._log.info('  total: ' + Fore.YELLOW + '{:>4.2f}MB'.format(_sw[0]/_MB)
                + Fore.CYAN + '; used: ' + Fore.YELLOW + '{:>4.2f}MB ({:3.1f}%)'.format(_sw[1]/_MB, _sw[3])
                + Fore.CYAN + '; free: ' + Fore.YELLOW + '{:>4.2f}MB'.format(_sw[2]/_MB))
        # CPU temperature ..............
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
