#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# author:   Murray Altheim
# created:  2021-10-09
# modified: 2021-10-09
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#

from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from core.logger import Logger, Level
from core.component import Component

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class IrqClock(Component):
    '''
    Sets up a falling-edge interrupt on a GPIO pin, whose toggle (an Interrupt
    Request) is generated by an external source. When the interrupt is
    triggered any registered callbacks are executed.

    The callbacks are not executed asynchronously so any of them can block and
    throw off the clock timing. Hence callbacks should all return immediately.

    Make sure to call close() when finished to free up the Pi resources.

    Lazily-imports and configures pigpio when the enabled.

    :param config:     The application configuration.
    :param pin:        the optional input pin, overriding the configuration.
    :param level:      the logging level.
    '''
    def __init__(self, config, pin=None, level=Level.INFO):
        self._log = Logger('irq-clock', level)
        Component.__init__(self, self._log, suppressed=False, enabled=True)
        if config is None:
            raise ValueError('no configuration provided.')
        _cfg = config['kros'].get('hardware').get('irq_clock')
        self._initd        = False
        self.__callbacks   = []
        self._pi_callback = None
        self._pin = pin if pin else _cfg.get('pin')
        self._log.info('IRQ clock pin:\t{:d}'.format(self._pin))
        self._log.info('ready.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def name(self):
        return 'irq-clock'

     # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def enable(self):
        Component.enable(self)
        if self.enabled:
            if not self._initd:
                try:
                    self._log.info('importing pigpio...')
                    import pigpio
                    self._pi = pigpio.pi()
                    if not self._pi.connected:
                        raise Exception('unable to establish connection to Pi.')
                    self._log.info('establishing callback on pin {:d}.'.format(self._pin))
                    self._pi.set_mode(gpio=self._pin, mode=pigpio.INPUT)
                    _edge = pigpio.EITHER_EDGE
#                   _edge = pigpio.FALLING_EDGE
                    self._pi_callback = self._pi.callback(self._pin, _edge, self._callback_method)
                    self._log.info('configured IRQ clock.')
                except Exception as e:
                    self._log.error('unable to enable IRQ clock: {}'.format(e))
                finally:
                    self._initd = True
        else:
            self._log.warning('unable to enable IRQ clock.')

     # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def add_callback(self, callback):
        '''
        Adds a callback to those triggered by clock ticks.
        '''
        self.__callbacks.append(callback)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _callback_method(self, gpio, level, tick):
#       self._log.info('IRQ clock callback triggered.')
        if self.enabled:
            for callback in self.__callbacks:
                callback()
        else:
            self._log.warning('IRQ clock disabled.')

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def close(self):
        try:
            if self._pi_callback:
                self._pi_callback.cancel()
            if self._pi:
                self._pi.stop()
        except Exception as e:
            self._log.error('error closing pigpio: {}'.format(e))
        Component.close(self)
        self._log.info('closed.')

#EOF
