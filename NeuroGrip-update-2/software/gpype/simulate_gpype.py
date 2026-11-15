"""
Fake gpype_pipeline.py output for testing gpype_trigger.py without a headset.
Loops: rest -> single blink (ignored) -> double blink (TRIGGER) -> rest -> jaw clench (TRIGGER)

    python simulate_gpype.py          # terminal 1
    python gpype_trigger.py --dry-run # terminal 2
"""
import socket
import time

import numpy as np

FS = 250
rng = np.random.default_rng(0)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
BLINK, JAW = ("127.0.0.1", 56010), ("127.0.0.1", 56011)


def blink_shape(n=60, amp=250.0):            # ~240 ms positive EOG bump
    return amp * np.sin(np.linspace(0, np.pi, n)) ** 2


def build_fz():
    seg = lambda s: rng.normal(0, 10, int(s * FS))
    single = np.concatenate([seg(2), blink_shape(), seg(2.5)])
    double = np.concatenate([blink_shape(), seg(0.2), blink_shape(), seg(3)])
    return np.concatenate([seg(1), single, double]), len(single) + FS


def run():
    while True:
        fz, _ = build_fz()
        clench_at = len(fz)                    # clench after the blinks
        total = clench_at + int(4 * FS)
        fz = np.concatenate([fz, rng.normal(0, 10, total - len(fz))])
        t0 = time.monotonic()
        for i in range(total):
            sock.sendto(np.array([fz[i], 0.0, 0.0]).tobytes(), BLINK)
            if i % 32 == 0:                    # jaw power at ~8 Hz
                clench = clench_at + FS <= i < clench_at + 2 * FS
                p = rng.uniform(80, 120) if clench else rng.uniform(3, 8)
                sock.sendto(np.array([0.0, p, p * 0.8]).tobytes(), JAW)
            # keep real-time pace
            delay = t0 + (i + 1) / FS - time.monotonic()
            if delay > 0:
                time.sleep(delay)


if __name__ == "__main__":
    print("Simulating g.Pype streams on UDP 56010/56011... Ctrl+C to stop")
    try:
        run()
    except KeyboardInterrupt:
        pass
