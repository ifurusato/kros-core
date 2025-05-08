#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-11-18
# modified: 2024-11-18
#

import psutil
import subprocess
from datetime import datetime as dt, timedelta
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class PigpiodUtility:
    '''
    A simple class to determine if pigpiod is running, and if not, start it.
    '''
    @staticmethod
    def is_pigpiod_running():
        '''
        Check if the pigpiod process is running.

        :return: True if pigpiod is running, False otherwise.
        '''
        for process in psutil.process_iter(['name']):
            if process.info['name'] == 'pigpiod':
                return True
        return False

    @staticmethod
    def ensure_pigpiod_is_running():
        '''
        Ensure the pigpiod service is running, starting it if necessary.
        '''
        _log = Logger('pig-util', Level.INFO)
        if PigpiodUtility.is_pigpiod_running():
            _log.debug("pigpiod is already running.")
        else:
            _log.info(Fore.YELLOW + "pigpiod is not running: attempting to start it…")
            PigpiodUtility.start_pigpiod(skip_check=True)

    @staticmethod
    def start_pigpiod(skip_check=False):
        '''
        Start the pigpiod service using systemctl.

        :param skip_check: If True, skip the check for whether pigpiod is already running.
        '''
        _log = Logger('pig-util', Level.INFO)
        if not skip_check and PigpiodUtility.is_pigpiod_running():
            _log.info("pigpiod is already running.")
            return
        try:
            start_time = dt.now()
            subprocess.run(['sudo', 'systemctl', 'start', 'pigpiod'], check=True)
            PigpiodUtility.wait_for_daemon('pigpiod', timeout=10)
            end_time = dt.now()
            elapsed_time_ms = (end_time - start_time).total_seconds() * 1000
            _log.info(Fore.GREEN + f'pigpiod service started, elapsed time: {elapsed_time_ms:.2f} ms')
        except subprocess.CalledProcessError as e:
            _log.info("failed to start pigpiod service: {}".format(e))
        except FileNotFoundError:
            _log.info("The 'systemctl' command is not found. Ensure it is installed and accessible.")

    @staticmethod
    def wait_for_daemon(service_name, timeout=10):
        _log = Logger('pig-util', Level.INFO)
        deadline = dt.now() + timedelta(seconds=timeout)
        while dt.now() < deadline:
            result = subprocess.run(["systemctl", "is-active", service_name], capture_output=True, text=True)
            if result.stdout.strip() == "active":
                _log.info(f"{service_name} is now active.")
                return True
            # busy-wait for 1 second
            wait_until = dt.now() + timedelta(seconds=1)
            while dt.now() < wait_until:
                pass  # busy wait
        _log.warning(f"timeout: {service_name} did not become active within {timeout} seconds.")
        return False

    @staticmethod
    def stop_pigpiod(skip_check=False):
        '''
        Stop the pigpiod service using systemctl.

        :param skip_check: If True, skip the check for whether pigpiod is already stopped.
        '''
        _log = Logger('pig-util', Level.INFO)
        if not skip_check and not PigpiodUtility.is_pigpiod_running():
            _log.info("pigpiod is already stopped.")
            return
        try:
            start_time = dt.now()
            subprocess.run(['sudo', 'systemctl', 'stop', 'pigpiod'], check=True)
            PigpiodUtility.wait_for_daemon_to_stop('pigpiod', timeout=10)
            end_time = dt.now()
            elapsed_time_ms = (end_time - start_time).total_seconds() * 1000
            _log.info(Fore.GREEN + f'pigpiod service stopped, elapsed time: {elapsed_time_ms:.2f} ms')
        except subprocess.CalledProcessError as e:
            _log.info("failed to stop pigpiod service: {}".format(e))
        except FileNotFoundError:
            _log.info("The 'systemctl' command is not found. Ensure it is installed and accessible.")

    @staticmethod
    def wait_for_daemon_to_stop(service_name, timeout=10):
        _log = Logger('pig-util', Level.INFO)
        deadline = dt.now() + timedelta(seconds=timeout)
        while dt.now() < deadline:
            result = subprocess.run(["systemctl", "is-active", service_name], capture_output=True, text=True)
            if result.stdout.strip() in ("inactive", "failed", "unknown"):  # includes "failed" in case it crashes
                _log.info(f"{service_name} has stopped.")
                return True
            # busy-wait for 1 second
            wait_until = dt.now() + timedelta(seconds=1)
            while dt.now() < wait_until:
                pass
        _log.warning(f"timeout: {service_name} did not stop within {timeout} seconds.")
        return False

#EOF
