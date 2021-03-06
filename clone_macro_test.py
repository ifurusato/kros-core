#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-10-13
# modified: 2021-10-15
#
# Tests the ability to clone a macro using various deepcopy features.
#

import pytest
import sys, numpy, time, traceback
from datetime import datetime as dt
from math import isclose
from colorama import init, Fore, Style
init()

import core.globals as globals
globals.init()

from core.message_bus import MessageBus
from core.message_factory import MessageFactory
from core.orientation import Orientation
from core.direction import Direction
from core.logger import Logger, Level
from core.config_loader import ConfigLoader
from hardware.i2c_scanner import I2CScanner, DeviceNotFound
from core.macro_publisher import MacroPublisher

#from behave.travel import Travel

_log = Logger('test', Level.INFO)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def key_callback(event):
    _log.info('callback on event: {}'.format(event))

class FakeKros(object):
    '''
    Only to fulfill: _macro_publisher = _kros.get_macro_publisher()
    '''
    def __init__(self, macro_publisher, level=Level.INFO):
        self._macro_publisher = macro_publisher
        globals.put('kros', self)

    def get_macro_publisher(self):
        return self._macro_publisher

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
@pytest.mark.unit
def test_motors():

    _errcode = -1
    _start_time = dt.now()

    try:

        # read YAML configuration
        _level = Level.INFO
        _loader = ConfigLoader(_level)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _log.info('creating message bus...')
        _message_bus = MessageBus(_config, _level)
        _log.info('creating message factory...')
        _message_factory = MessageFactory(_message_bus, _level)

        _i2c_scanner = I2CScanner(_config, _level)

        _log.info('starting test...')
        _mp = MacroPublisher(_config, _message_bus, _message_factory, callback=key_callback, level=Level.INFO)

        _fake_kros = FakeKros(_mp, _level)

        _log.info('loading macro files...')
        _mp.load_macro_files()

        _name = 'avoid'
        _log.info('queuing macro "{}"...'.format(_name))
        _mp.queue_macro_by_name(_name)
        _log.info('queued macro "{}".'.format(_name))

        _orig = _mp.original_macro()
        _log.info('macro orig:\n' + Fore.WHITE + '{}'.format(_orig))
        _copy = _mp.copied_macro()
        _log.info('macro copy:\n' + Fore.WHITE + '{}'.format(_copy))

        assert _orig is not _copy, 'expected original not to be the same as the copy.'
        assert _orig == _copy, 'expected original to be equal to the copy.'
        assert _orig == _orig, 'expected original to be equal to the original.'
        assert _copy == _copy, 'expected the copy to be equal to the copy.'

        _mp.close()

        _log.info('complete.')
        _errcode = 0

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
        _errcode = 1
    except DeviceNotFound as e:
        _log.error('no potentiometer found, exiting.')
        _errcode = 2
    except Exception as e:
        _log.error('{} encountered, exiting: {}'.format(type(e), e))
        _errcode = 3
    finally:
        if _errcode == 0:
            _log.info('executed without error.')
        else:
            _log.warning('exited with error code: {:d}'.format(_errcode))
        _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
        _log.info('complete: elapsed: {:d}ms'.format(_elapsed_ms))
        sys.exit(_errcode)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def main():
    test_motors()

if __name__== "__main__":
    main()

#EOF
