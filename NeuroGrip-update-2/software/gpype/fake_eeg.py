"""
Fake 3-channel "headset" (Fz, C3, C4) that you control with the keyboard.

Used two ways:
  * inside g.Pype: gpype_pipeline.py --sim wraps this in a g.Pype source node,
    so the fake samples go through the SAME g.Pype filters, FFT and BandPower
    as the real Unicorn data.
  * without g.Pype: neurogrip_live.py --fallback-sim (emergency only).

The live window tells it what to do by sending tiny UDP messages to
CONTROL_PORT:  b"clench 1" (repeated while SPACE is held), b"clench 0", b"blink".
"""
import socket
import threading
import time

import numpy as np

FS = 250
CONTROL_PORT = 56013
LABELS = ["Fz", "C3", "C4"]


class FakeHead:
    """Generates one sample at a time. Thread-safe enough for this use."""

    def __init__(self, seed=None):
        self.rng = np.random.default_rng(seed)
        self.n = 0
        self.ar = np.zeros(3)               # slow 1/f-ish background state
        self.emg_level = 0.0                # 0..1, ramps so the power visibly climbs
        self.clench_until = 0.0             # clench stays on while messages keep coming
        self.blink_starts = []
        self.lock = threading.Lock()

    # -- control ------------------------------------------------------------
    def set_clench(self, on):
        with self.lock:
            self.clench_until = time.monotonic() + 0.35 if on else 0.0

    def blink(self):
        with self.lock:
            self.blink_starts.append(self.n)

    def listen(self, port=CONTROL_PORT):
        """Start a background thread that obeys the live window's key messages."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", port))

        def loop():
            while True:
                try:
                    msg = sock.recv(64).decode(errors="ignore").strip()
                except OSError:
                    continue
                if msg == "clench 1":
                    self.set_clench(True)
                elif msg == "clench 0":
                    self.set_clench(False)
                elif msg == "blink":
                    self.blink()

        threading.Thread(target=loop, daemon=True).start()

    # -- signal -------------------------------------------------------------
    def sample(self):
        """Return one sample [Fz, C3, C4] in microvolts."""
        t = self.n / FS
        rng = self.rng
        # brain-ish background: slow wandering + alpha + theta + a little white noise
        self.ar = 0.97 * self.ar + rng.normal(0, 2.0, 3)
        x = self.ar.copy()
        x += 9.0 * np.sin(2 * np.pi * 10.0 * t + np.array([0.0, 0.7, 1.3]))
        x += 5.0 * np.sin(2 * np.pi * 6.0 * t + np.array([0.4, 1.9, 2.6]))
        x += rng.normal(0, 1.2, 3)
        x += 4.0 * np.sin(2 * np.pi * 60.0 * t)          # mains hum (g.Pype notches it)

        with self.lock:
            clenching = time.monotonic() < self.clench_until
            # ~0.4 s ramp up, ~0.25 s ramp down, like a real muscle
            step = 1.0 / (0.4 * FS) if clenching else -1.0 / (0.25 * FS)
            self.emg_level = min(1.0, max(0.0, self.emg_level + step))
            starts = list(self.blink_starts)
        if self.emg_level > 0:
            # jaw muscle noise: strong on C3/C4 (near the temples), weaker on Fz
            x += self.emg_level * rng.normal(0, 1.0, 3) * np.array([8.0, 26.0, 24.0])

        for b in starts:                                    # ~240 ms blink bump on Fz
            k = self.n - b
            if 0 <= k < 60:
                bump = 160.0 * np.sin(np.pi * k / 60) ** 2
                x[0] += bump
                x[1:] += 0.15 * bump
        if starts:
            with self.lock:
                self.blink_starts = [b for b in self.blink_starts if self.n - b < 60]
        self.n += 1
        return x
