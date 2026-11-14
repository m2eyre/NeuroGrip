"""Keyboard as the input: hold G in the plot window to "act".

Good for testing the whole chain without any sensor, and as an accessibility
input in its own right (swap the key handling for a foot pedal or a big
USB button that shows up as a key).

    python neurogrip_bridge.py --source sources/keyboard_source.py --mode level --threshold 0.5

Hold G for longer than hold_ms (150 ms) and the gripper toggles. SPACE still
works as an instant toggle, as in every mode.
"""
import time

import numpy as np

KEY = "g"


class KeyboardSource:
    def __init__(self, fs=100.0):
        self.fs, self.n_ch, self.labels = fs, 1, [f"key {KEY.upper()}"]
        self.down = False
        self._t0, self._sent = time.perf_counter(), 0

    def on_key(self, key, down):
        if key == KEY:
            self.down = down

    def read(self):
        due = int((time.perf_counter() - self._t0) * self.fs)
        n = due - self._sent
        if n <= 0:
            return np.empty((0, 1))
        self._sent = due
        return np.full((n, 1), 1.0 if self.down else 0.0)


def make_source(args):
    return KeyboardSource()
