# SPDX-FileCopyrightText: 2019 Dave Astels for Adafruit Industries
# SPDX-License-Identifier: MIT
#
# Based on the adafruit_debouncer by Dave Astels.
#__version__ = "0.0.0-auto.0"
#__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Debouncer.git"

import time
from micropython import const

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Debouncer:

    _TICKS_PER_SEC   = const(1)
    _DEBOUNCED_STATE = const(0x01)
    _UNSTABLE_STATE  = const(0x02)
    _CHANGED_STATE   = const(0x04)

    '''
    Debounces an arbitrary predicate function (typically created as a lambda)
    of zero arguments. Since a very common use is debouncing a digital input
    pin, the initializer accepts a DigitalInOut object instead of a lambda.
    '''
    def __init__(self, predicate, interval=0.010):
        '''
        Make am instance.

        :param predicate:      the lambda to debounce
        :param int interval:   bounce threshold in seconds (default is 0.010, i.e. 10 milliseconds)
        '''
        self.state = 0x00
        print('using lambda: {}'.format(type(predicate)))
        self.function = predicate
#       self.function = lambda: predicate.value
        if self.function():
            self._set_state(Debouncer._DEBOUNCED_STATE | Debouncer._UNSTABLE_STATE)
        self._last_bounce_ticks   = 0
        self._last_duration_ticks = 0
        self._state_changed_ticks = 0
        # Could use the .interval setter, but pylint prefers that we explicitly
        # set the real underlying attribute:
        self._interval_ticks = interval * Debouncer._TICKS_PER_SEC

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _set_state(self, bits):
        self.state |= bits

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _unset_state(self, bits):
        self.state &= ~bits

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _toggle_state(self, bits):
        self.state ^= bits

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def _get_state(self, bits):
        return (self.state & bits) != 0

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    def update(self):
        '''
        Update the debouncer state, must be called frequently.
        '''
        now_ticks = time.monotonic()
        self._unset_state(Debouncer._CHANGED_STATE)
        current_state = self.function()
        if current_state != self._get_state(Debouncer._UNSTABLE_STATE):
            self._last_bounce_ticks = now_ticks
            self._toggle_state(Debouncer._UNSTABLE_STATE)
        else:
            if now_ticks - self._last_bounce_ticks >= self._interval_ticks:
                if current_state != self._get_state(Debouncer._DEBOUNCED_STATE):
                    self._last_bounce_ticks = now_ticks
                    self._toggle_state(Debouncer._DEBOUNCED_STATE)
                    self._set_state(Debouncer._CHANGED_STATE)
                    self._last_duration_ticks = now_ticks - self._state_changed_ticks
                    self._state_changed_ticks = now_ticks

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def interval(self):
        '''
        The debounce delay, in seconds.
        '''
        return self._interval_ticks / Debouncer._TICKS_PER_SEC

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @interval.setter
    def interval(self, new_interval_s):
        self._interval_ticks = new_interval_s * Debouncer._TICKS_PER_SEC

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def value(self):
        '''
        Return the current debounced value.
        '''
        return self._get_state(Debouncer._DEBOUNCED_STATE)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def rose(self):
        '''
        Return whether the debounced value went from low to high at the most recent update.
        '''
        return self._get_state(Debouncer._DEBOUNCED_STATE) and self._get_state(Debouncer._CHANGED_STATE)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def fell(self):
        '''
        Return whether the debounced value went from high to low at the most recent update.
        '''
        return (not self._get_state(Debouncer._DEBOUNCED_STATE)) and self._get_state(Debouncer._CHANGED_STATE)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def last_duration(self):
        '''
        Return the number of seconds the state was stable prior to the most recent transition.
        '''
        return self._last_duration_ticks / Debouncer._TICKS_PER_SEC

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
    @property
    def current_duration(self):
        '''
        Return the number of seconds since the most recent transition.
        '''
        return (time.monotonic() - self._state_changed_ticks) / Debouncer._TICKS_PER_SEC

#EOF
