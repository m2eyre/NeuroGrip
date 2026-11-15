"""
NeuroGrip - g.Pype front end
g.tec headset (or the keyboard-driven fake headset) -> g.Pype filters + features -> UDP

Three streams go out over UDP (localhost):
  BLINK_PORT  56010 : Fz/C3/C4 bandpassed 0.5-10 Hz, every sample (250 Hz)
                      -> blinks show up as big positive spikes on Fz
  JAW_PORT    56011 : EMG power 30-100 Hz from g.Pype FFT + BandPower, ~8 updates/s
                      -> a jaw clench makes this jump by 10x or more
  VIEW_PORT   56012 : Fz/C3/C4 bandpassed 0.5-100 Hz + 60 Hz notch, every sample
                      -> the "brain waves" drawn by neurogrip_live.py

Run (normally neurogrip_live.py starts this for you):
    python gpype_pipeline.py                 # real Unicorn, with g.Pype's own scope window
    python gpype_pipeline.py --sim           # fake headset, SPACE in neurogrip_live = jaw clench
    python gpype_pipeline.py --sim --no-scope
    python gpype_pipeline.py --dataset data/subject_1_fvep_led_training_1.mat
                             # REAL recorded g.tec SSVEP EEG, SPACE = look at the 12 Hz LED

The --sim source is a real g.Pype source node (a gp.Generator subclass), so the
fake data goes through exactly the same g.Pype nodes as headset data.
"""
import argparse
import time

import gpype as gp

from fake_eeg import FakeHead

DEVICE = "unicorn"   # "unicorn" = Unicorn Hybrid Black, "core8" = BCI Core-8

FS = 250
# Unicorn electrode order (0-based): 0 Fz, 1 C3, 2 Cz, 3 C4, 4 Pz, 5 PO7, 6 Oz, 7 PO8
# We stream Fz (blinks) plus C3 and C4 (closest to the jaw muscles), in that order.
# gpype_trigger.py defaults match this: --blink-ch 0  --jaw-ch 1 2
UNICORN_CHANNELS = [0, 1, 3]

BLINK_PORT = 56010
JAW_PORT = 56011
VIEW_PORT = 56012
SPEC_PORT = 56014   # dataset mode: g.Pype FFT spectrum


class KeyboardHeadset(gp.Generator):
    """g.Pype source node: fake Fz/C3/C4 EEG, jaw clench while SPACE is held
    in the NeuroGrip live window, blink on B. Built on gp.Generator so g.Pype
    handles the 250 Hz pacing and timestamps; we only fill in the samples."""

    def __init__(self, **kwargs):
        super().__init__(sampling_rate=FS, channel_count=3, frame_size=1,
                         signal_amplitude=0.0, noise_amplitude=0.0, **kwargs)
        self._head = FakeHead()
        self._head.listen()

    def step(self, data):
        out = super().step(data)                 # zeros + g.Pype's timestamp column
        if out is None:
            return None
        for frame in out.values():
            for row in frame:
                row[:3] = self._head.sample()
        return out


class DatasetHeadset(gp.Generator):
    """g.Pype source node that replays REAL recorded EEG from the g.tec SSVEP
    LED dataset (8 occipital channels, 256 Hz). SPACE in the NeuroGrip window
    switches from the recorded breaks to the recorded "looking at the LED" trials."""

    def __init__(self, path, led=12, muscle=False, **kwargs):
        from dataset_replay import FS as DFS, MuscleReplay, Replay
        super().__init__(sampling_rate=DFS, channel_count=8, frame_size=1,
                         signal_amplitude=0.0, noise_amplitude=0.0, **kwargs)
        self._replay = MuscleReplay() if muscle else Replay(path, led)
        self._replay.listen()

    def step(self, data):
        out = super().step(data)
        if out is None:
            return None
        for frame in out.values():
            for row in frame:
                row[:8] = self._replay.sample()
        return out


def make_source(sim):
    if sim:
        return KeyboardHeadset()
    # frame_size=1: the FFT node needs 1-sample input frames
    if DEVICE == "unicorn":
        return gp.HybridBlack(channel_selection=UNICORN_CHANNELS, frame_size=1)
    # All 8 channels. Pass --blink-ch / --jaw-ch to match your cap.
    return gp.BCICore8(frame_size=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", action="store_true", help="keyboard-driven fake headset instead of the Unicorn")
    ap.add_argument("--no-scope", action="store_true", help="don't open g.Pype's scope window")
    ap.add_argument("--dataset", help="replay a g.tec SSVEP .mat recording instead of a headset")
    ap.add_argument("--led", type=int, default=12, help="dataset: which LED's trials SPACE plays")
    ap.add_argument("--muscle", action="store_true",
                    help="replay REAL muscle bursts from the g.tec recordings through the jaw branch")
    a = ap.parse_args()

    p = gp.Pipeline()
    if a.dataset:
        return run_dataset(p, a)
    if a.muscle:
        return run_muscle(p, a)
    src = make_source(a.sim)

    # --- Blink branch: slow, large EOG deflections ------------------------
    blink_filt = gp.Bandpass(f_lo=0.5, f_hi=10)
    blink_out = gp.UDPSender(ip="127.0.0.1", port=BLINK_PORT)

    # --- Jaw branch: high-frequency muscle (EMG) power ---------------------
    jaw_notch = gp.Bandstop(f_lo=58, f_hi=62)          # 60 Hz mains (Michigan)
    jaw_fft = gp.FFT(window_size=64, overlap=0.5)       # 256 ms window, update every 128 ms
    jaw_power = gp.BandPower(bands=[[30, 100]])
    jaw_out = gp.UDPSender(ip="127.0.0.1", port=JAW_PORT)

    # --- Wide-band view for the NeuroGrip live window ----------------------
    wide_filt = gp.Bandpass(f_lo=0.5, f_hi=100)
    wide_notch = gp.Bandstop(f_lo=58, f_hi=62)
    wide_out = gp.UDPSender(ip="127.0.0.1", port=VIEW_PORT)

    p.connect(src, blink_filt)
    p.connect(blink_filt, blink_out)

    p.connect(src, jaw_notch)
    p.connect(jaw_notch, jaw_fft)
    p.connect(jaw_fft, jaw_power)
    p.connect(jaw_power, jaw_out)

    p.connect(src, wide_filt)
    p.connect(wide_filt, wide_notch)
    p.connect(wide_notch, wide_out)

    tag = "FAKE keyboard headset" if a.sim else f"{DEVICE} headset"
    print(f"g.Pype pipeline running ({tag}). UDP {BLINK_PORT}/{JAW_PORT}/{VIEW_PORT}. Ctrl+C to stop.")

    # --- g.Pype's own live view (check electrode contact, show judges) -----
    view_filt = gp.Bandpass(f_lo=0.5, f_hi=40)
    view_notch = gp.Bandstop(f_lo=58, f_hi=62)
    run(p, a, [(src, view_filt), (view_filt, view_notch)], view_notch, 200)


def run_dataset(p, a):
    """Recorded SSVEP EEG -> g.Pype band-pass -> UDP (waves + detector) and g.Pype FFT -> UDP (spectrum)."""
    src = DatasetHeadset(a.dataset, a.led)
    band = gp.Bandpass(f_lo=5, f_hi=45)                 # SSVEP band, removes drift and mains
    p.connect(src, band)
    p.connect(band, gp.UDPSender(ip="127.0.0.1", port=VIEW_PORT))
    fft = gp.FFT(window_size=512, overlap=0.875)          # 2 s window, 0.5 Hz bins, 4 updates/s
    p.connect(band, fft)
    p.connect(fft, gp.UDPSender(ip="127.0.0.1", port=SPEC_PORT))
    print(f"g.Pype pipeline running (REPLAY of {a.dataset}). UDP {VIEW_PORT}/{SPEC_PORT}. Ctrl+C to stop.")
    run(p, a, [], band, 50)


def run_muscle(p, a):
    """Real recorded muscle bursts -> the SAME jaw branch the headset uses (notch, FFT, BandPower 30-100 Hz)."""
    src = DatasetHeadset(None, muscle=True)
    notch = gp.Bandstop(f_lo=48, f_hi=52)                # recorded in Austria: 50 Hz mains
    p.connect(src, notch)
    fft = gp.FFT(window_size=64, overlap=0.5)
    power = gp.BandPower(bands=[[30, 100]])
    p.connect(notch, fft)
    p.connect(fft, power)
    p.connect(power, gp.UDPSender(ip="127.0.0.1", port=JAW_PORT))
    wide = gp.Bandpass(f_lo=0.5, f_hi=100)
    p.connect(notch, wide)
    p.connect(wide, gp.UDPSender(ip="127.0.0.1", port=VIEW_PORT))
    print(f"g.Pype pipeline running (REPLAY of real muscle bursts). UDP {JAW_PORT}/{VIEW_PORT}. Ctrl+C to stop.")
    run(p, a, [], wide, 100)


def run(p, a, scope_links, scope_src, amp):
    """Start the pipeline, with g.Pype's scope window if possible."""
    app = None
    if not a.no_scope:
        try:
            app = gp.MainApp(caption="NeuroGrip - g.Pype signal view")
        except Exception as e:              # GUI extras missing: keep streaming without the scope
            print(f"(g.Pype scope window unavailable: {e}. Fix: pip install \"gpype[all]\". Continuing without it.)")

    if app is None:
        p.start()
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        p.stop()
        return

    for a_, b_ in scope_links:
        p.connect(a_, b_)
    scope = gp.TimeSeriesScope(amplitude_limit=amp, time_window=10)
    p.connect(scope_src, scope)
    app.add_widget(scope)
    p.start()
    app.run()   # blocks until the window is closed (macOS needs this on the main thread)
    p.stop()


if __name__ == "__main__":
    main()
