"""Template: write your own NeuroGrip input source.

Copy this file, fill in read(), then run:

    python neurogrip_bridge.py --source sources/my_source.py --mode level

A source only needs four things:
    fs      sample rate in Hz (float)
    n_ch    number of channels (int)
    labels  list of n_ch channel names, used on the plot
    read()  return a NumPy array of shape (n_samples, n_ch) with every sample
            that arrived since the last call. Return np.empty((0, n_ch)) when
            nothing is new. Never block: the plot calls this 25 times a second.

Optional:
    on_key(key, down)   called on every key press (down=True) and release
                        (down=False) in the plot window.

Which --mode to use:
    clench  your source gives raw EEG/EMG in microvolts at >= ~200 Hz
            (the bridge band-passes 30-100 Hz and takes the RMS)
    blink   raw EEG with a frontal channel (set blink_channel in the JSON)
    level   your source already gives "how strong is the action" (an EMG
            envelope, a pressure sensor, a button, a classifier score).
            No filtering. A trigger fires when it stays above the threshold
            for hold_ms, and the input must drop below 70 % of the threshold
            before the next trigger.
"""
import time

import numpy as np


class MySource:
    def __init__(self, fs=100.0):
        self.fs = fs
        self.n_ch = 1
        self.labels = ["my signal"]
        self._t0 = time.perf_counter()
        self._sent = 0

    def read(self):
        # Example: produce samples at a steady rate. Replace with your device.
        due = int((time.perf_counter() - self._t0) * self.fs)
        n = due - self._sent
        if n <= 0:
            return np.empty((0, self.n_ch))
        self._sent = due
        return np.zeros((n, self.n_ch))   # <- your samples here


def make_source(args):
    """Called once by the bridge. args are the bridge's command-line options."""
    return MySource()
