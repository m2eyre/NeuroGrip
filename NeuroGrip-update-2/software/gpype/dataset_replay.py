"""
Replays REAL recorded EEG from the g.tec SSVEP LED dataset (8 channels, 256 Hz).

The recording has 4 flashing LEDs (9, 10, 12, 15 Hz). Each file holds 20 trials of
7.4 s (the person looks at one LED) with 3.1 s breaks (looking at nothing).

    rest track : every break in the file, joined end to end
    LED tracks : every trial for that LED, joined end to end

While SPACE is held in the NeuroGrip window, the LED track plays ("the person is
looking at the LED"); otherwise the rest track plays. Joins are cross-faded over
50 ms so switching doesn't make a click. Nothing is synthesised: every sample is
from the recording (DC offset removed with a 1 Hz high-pass).

Control messages (UDP 56013, same as the fake headset):
    b"clench 1" / b"clench 0"   look at the LED / look away
    b"led 12"                   which LED's trials SPACE plays (9, 10, 12 or 15)
"""
import pathlib
import socket
import threading
import time

import numpy as np

FS = 256
CONTROL_PORT = 56013
LABELS = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]   # from montage.png
FREQS = [9, 10, 12, 15]
DATA_DIR = pathlib.Path(__file__).resolve().parent / "data"
DEFAULT_FILE = DATA_DIR / "subject_1_fvep_led_training_1.mat"
FADE = int(0.05 * FS)


def load_ssvep(path):
    """Return (eeg (n, 8) in uV with DC removed, labels (n,) 0/9/10/12/15)."""
    from scipy import io, signal
    y = io.loadmat(str(path))["y"]                     # (11, n): time, 8 EEG, trigger, LDA
    eeg = y[1:9].T.astype(float)
    sos = signal.butter(2, 1.0, "highpass", fs=FS, output="sos")
    eeg = signal.sosfiltfilt(sos, eeg, axis=0)
    return eeg, y[9].astype(int)


def segments(labels):
    edges = np.flatnonzero(np.diff(labels) != 0) + 1
    starts, ends = np.r_[0, edges], np.r_[edges, len(labels)]
    return [(int(labels[s]), s, e) for s, e in zip(starts, ends)]


def join(pieces):
    """Concatenate with short cross-fades so the joins don't click."""
    out = pieces[0]
    ramp = np.linspace(0, 1, FADE)[:, None]
    for p in pieces[1:]:
        mixed = out[-FADE:] * (1 - ramp) + p[:FADE] * ramp
        out = np.vstack([out[:-FADE], mixed, p[FADE:]])
    return out


class Replay:
    def __init__(self, path=DEFAULT_FILE, led=12):
        eeg, lab = load_ssvep(path)
        segs = segments(lab)
        skip = int(0.5 * FS)                           # first 0.5 s of a trial: response still building
        self.tracks = {0: join([eeg[s + 64:e - 64] for c, s, e in segs if c == 0 and e - s > 3 * FS // 2])}
        for f in FREQS:
            self.tracks[f] = join([eeg[s + skip:e] for c, s, e in segs if c == f])
        self.pos = {k: 0 for k in self.tracks}
        self.led = led
        self.looking_until = 0.0
        self.current, self.fade = 0, None
        self.lock = threading.Lock()
        self.name = pathlib.Path(path).name

    # -- control ------------------------------------------------------------
    def listen(self, port=CONTROL_PORT):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", port))

        def loop():
            while True:
                try:
                    msg = sock.recv(64).decode(errors="ignore").strip()
                except OSError:
                    continue
                with self.lock:
                    if msg == "clench 1":
                        self.looking_until = time.monotonic() + 0.35
                    elif msg == "clench 0":
                        self.looking_until = 0.0
                    elif msg.startswith("led "):
                        try:
                            f = int(msg.split()[1])
                        except ValueError:
                            continue
                        if f in FREQS:
                            self.led = f

        threading.Thread(target=loop, daemon=True).start()

    # -- samples ------------------------------------------------------------
    def _next(self, key):
        tr = self.tracks[key]
        x = tr[self.pos[key] % len(tr)]
        self.pos[key] += 1
        return x

    def sample(self):
        with self.lock:
            want = self.led if time.monotonic() < self.looking_until else 0
        if want != self.current:
            self.fade = (self.current, 0)                 # cross-fade from the old track
            self.current = want
        x = self._next(self.current)
        if self.fade is not None:
            old, k = self.fade
            a = (k + 1) / FADE
            x = a * x + (1 - a) * self._next(old)
            self.fade = (old, k + 1) if k + 1 < FADE else None
        return x


# ----------------------------------------------------------------------------
# Muscle-burst replay (for the jaw-clench detector)
# ----------------------------------------------------------------------------
MUSCLE_FILES = ["subject_1_fvep_led_training_1.mat", "subject_1_fvep_led_training_2.mat"]
MUSCLE_LABELS = LABELS


def find_muscle_bursts(eeg, fs=FS, factor=8.0, min_s=0.5, skip_s=10.0):
    """Find stretches where 30-100 Hz (muscle) power across all channels jumps
    above `factor` x the recording's median for at least `min_s`.
    Returns (bursts, calm): lists of (start, end) sample indices."""
    from scipy import signal
    sos = signal.butter(4, [30, 100], "bandpass", fs=fs, output="sos")
    e = signal.sosfiltfilt(sos, eeg, axis=0)
    w = int(0.25 * fs)
    n = len(e) // w
    p = (e[: n * w] ** 2).reshape(n, w, -1).mean(axis=(1, 2))
    med = np.median(p)
    first = int(skip_s * fs / w)
    big = p > factor * med
    bursts, i = [], first
    while i < n:
        if big[i]:
            j = i
            while j < n and big[j]:
                j += 1
            if (j - i) * w >= min_s * fs:
                bursts.append((max(0, (i - 1) * w), min(len(eeg), (j + 1) * w)))
            i = j
        else:
            i += 1
    quiet = p < 2.0 * med
    calm, i = [], first
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if j - i >= 8:                                   # at least 2 s of calm
                s, e_ = (i + 1) * w, (j - 1) * w
                if all(e_ < b0 - fs or s > b1 + fs for b0, b1 in bursts):
                    calm.append((s, e_))
            i = j
        else:
            i += 1
    return bursts, calm


class MuscleReplay(Replay):
    """Like Replay, but SPACE plays REAL muscle bursts found in the g.tec recordings
    and letting go plays real calm stretches from the same recordings."""

    def __init__(self, data_dir=DATA_DIR):
        bursts, calm, self.found = [], [], []
        for name in MUSCLE_FILES:
            eeg, _ = load_ssvep(pathlib.Path(data_dir) / name)
            b, c = find_muscle_bursts(eeg)
            bursts += [eeg[s:e] for s, e in b]
            calm += [eeg[s:e] for s, e in c]
            self.found += [(name, s / FS, (e - s) / FS) for s, e in b]
        self.tracks = {0: join(calm)}
        self.bursts = bursts
        self.pos = {0: 0}
        self.led = 1
        self.looking_until = 0.0
        self.current, self.fade = 0, None
        self.lock = threading.Lock()
        self.name = "muscle bursts from " + ", ".join(MUSCLE_FILES)
        self.next_burst, self.playing, self.was_pressed = 0, None, False

    def sample(self):
        """One press of SPACE = one real recorded burst, played start to finish."""
        with self.lock:
            pressed = time.monotonic() < self.looking_until
        if pressed and not self.was_pressed:
            self.playing = [self.bursts[self.next_burst % len(self.bursts)], 0]
            self.next_burst += 1
        self.was_pressed = pressed
        calm = self._next(0)
        if self.playing is None:
            return calm
        burst, k = self.playing
        self.playing[1] += 1
        if k + 1 >= len(burst):
            self.playing = None
        # 50 ms cross-fade in and out so the join doesn't click
        a = min(1.0, (k + 1) / FADE, (len(burst) - k) / FADE)
        return a * burst[k] + (1 - a) * calm
