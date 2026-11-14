#!/usr/bin/env python3
"""
NeuroGrip EEG bridge
====================
g.tec Unicorn Hybrid Black --(Bluetooth)--> Unicorn LSL app --(LSL)--> THIS SCRIPT
--(USB serial)--> Arduino Nano R4 --> SG90 servo gripper

What it does
  * Reads the 8 EEG channels from the Unicorn through Lab Streaming Layer (LSL)
    (or any other LSL stream, the built-in simulator, or your own source plugin)
  * Detects a JAW CLENCH (default), a DOUBLE BLINK, or a plain LEVEL crossing
  * Sends "toggle" to the Nano so the gripper opens/closes
  * Shows a live plot with the signal, the detection feature and the threshold
  * Has a guided calibration (press K) that picks the threshold for you

Keys (click the plot window first so it has focus):
  SPACE       fake trigger (toggle the gripper) - keyboard fallback
  O / C       force open / force close
  K           start guided calibration (relax, then clench/blink)
  UP / DOWN   raise / lower the threshold by 10 %
  S           save threshold + settings to neurogrip_calibration.json
  J (hold)    simulated jaw clench      (only with --source sim)
  B           simulated blink           (only with --source sim)
  Q / ESC     quit

Examples
  python neurogrip_bridge.py --list                 # show LSL streams + serial ports
  python neurogrip_bridge.py --source sim --no-serial   # try everything without hardware
  python neurogrip_bridge.py                        # Unicorn via LSL, auto-find the Nano
  python neurogrip_bridge.py --port COM5 --mode blink
  python neurogrip_bridge.py --source sources/keyboard_source.py --mode level --no-serial

Swapping the input: see docs/alternative-inputs.md. In short, a source is any
object with .fs, .n_ch, .labels and .read() -> array (n_samples, n_channels).
Put one in a .py file with a make_source(args) function and pass the file to
--source.
"""
import argparse
import importlib.util
import json
import pathlib
import sys
import threading
import time

import numpy as np
from scipy import signal

CAL_FILE = pathlib.Path(__file__).with_name("neurogrip_calibration.json")
UNICORN_LABELS = ["Fz", "C3", "Cz", "C4", "Pz", "PO7", "Oz", "PO8"]

DEFAULTS = {
    "mode": "clench",          # clench | blink | level
    "threshold": None,         # µV; None = not calibrated yet (a guess is used)
    "hold_ms": 150,            # clench must stay above threshold this long
    "refractory_ms": 1200,     # ignore new triggers for this long after one
    "double_blink_ms": 700,    # max gap between the two blinks
    "blink_channel": 0,        # 0 = Fz, the most frontal Unicorn electrode
    "blink_polarity": 1,       # set to -1 if your blinks show up as downward bumps
    "mains_hz": 60,            # 60 in North America, 50 in Europe
}
GUESS_THRESHOLD = {"clench": 25.0, "blink": 60.0, "level": 0.5}


# ----------------------------------------------------------------------------
# Signal sources
# ----------------------------------------------------------------------------
class LSLSource:
    """Pulls EEG from an LSL stream (the Unicorn LSL app, or any EEG stream)."""

    def __init__(self, stream_name=None, n_eeg=8):
        n_eeg = n_eeg or 8
        from pylsl import StreamInlet, resolve_streams

        print("Looking for LSL streams (5 s)...")
        streams = resolve_streams(wait_time=5.0)
        if not streams:
            sys.exit("No LSL stream found. Is the Unicorn LSL app open and STREAMING? "
                     "Or run with --source sim to test without the headset.")
        chosen = None
        for s in streams:
            if stream_name and s.name() == stream_name:
                chosen = s
        if chosen is None and not stream_name:
            for s in streams:
                if s.type().lower() in ("eeg", "data") or s.name().upper().startswith("UN"):
                    chosen = s
                    break
            chosen = chosen or streams[0]
        if chosen is None:
            sys.exit(f"No stream named {stream_name!r}. Found: {[s.name() for s in streams]}")

        self.inlet = StreamInlet(chosen, max_buflen=10)
        self.fs = chosen.nominal_srate() or 250.0
        self.n_ch = min(n_eeg, chosen.channel_count())
        print(f"Using LSL stream '{chosen.name()}' type={chosen.type()} "
              f"{chosen.channel_count()} ch @ {self.fs:.0f} Hz (first {self.n_ch} = EEG)")
        self.labels = self._labels(self.inlet) or UNICORN_LABELS[: self.n_ch]

    def _labels(self, inlet):
        """Channel names from the stream metadata, if the sender published them."""
        try:
            ch = inlet.info(timeout=2.0).desc().child("channels").child("channel")
            names = []
            while ch.name() == "channel" and len(names) < self.n_ch:
                names.append(ch.child_value("label") or f"ch{len(names) + 1}")
                ch = ch.next_sibling()
            return names if len(names) == self.n_ch else None
        except Exception:
            return None

    def read(self):
        chunk, _ = self.inlet.pull_chunk(timeout=0.0, max_samples=2048)
        if not chunk:
            return np.empty((0, self.n_ch))
        return np.asarray(chunk, dtype=float)[:, : self.n_ch]


class SimSource:
    """Fake 8-channel EEG so you can test the whole pipeline with no headset.
    Hold J for a jaw clench (broadband EMG), tap B for a blink."""

    def __init__(self, fs=250.0, n_ch=8):
        self.fs, self.n_ch = fs, n_ch
        self.labels = (UNICORN_LABELS + [f"ch{i + 1}" for i in range(8, n_ch)])[:n_ch]
        self.t0 = time.perf_counter()
        self.produced = 0
        self.clenching = False
        self.blink_at = []          # sample indices where a blink starts
        self.rng = np.random.default_rng(0)

    def blink(self):
        self.blink_at.append(self.produced)

    def read(self):
        due = int((time.perf_counter() - self.t0) * self.fs)
        n = due - self.produced
        if n <= 0:
            return np.empty((0, self.n_ch))
        idx = np.arange(self.produced, due)
        t = idx / self.fs
        x = self.rng.normal(0, 6, (n, self.n_ch))                       # background
        x += 10 * np.sin(2 * np.pi * 10 * t)[:, None]                   # alpha
        x += 8 * np.sin(2 * np.pi * self.mains_hz * t)[:, None]         # mains hum
        if self.clenching:
            x += self.rng.normal(0, 45, (n, self.n_ch))                 # EMG burst
        for b in self.blink_at:                                         # ~250 ms blink bump
            k = idx - b
            m = (k >= 0) & (k < int(0.25 * self.fs))
            if m.any():
                shape = 150 * np.sin(np.pi * k[m] / (0.25 * self.fs))
                x[m, 0] += shape
                x[m, 1:] += shape[:, None] * 0.3
        self.blink_at = [b for b in self.blink_at if due - b < self.fs]
        self.produced = due
        return x

    mains_hz = 60


def load_source_plugin(path, args):
    """Load a source from a .py file that defines make_source(args).
    See software/sources/template_source.py for a starting point."""
    path = pathlib.Path(path)
    if not path.exists():
        sys.exit(f"--source {path}: file not found (use lsl, sim, or a path to a .py file)")
    spec = importlib.util.spec_from_file_location(f"ng_source_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "make_source"):
        sys.exit(f"{path} has no make_source(args) function")
    src = mod.make_source(args)
    for attr in ("fs", "n_ch", "labels", "read"):
        if not hasattr(src, attr):
            sys.exit(f"The source from {path} is missing .{attr}")
    print(f"Using source plugin {path.name}: {src.n_ch} ch @ {src.fs:.0f} Hz")
    return src


# ----------------------------------------------------------------------------
# Detector
# ----------------------------------------------------------------------------
class Detector:
    def __init__(self, fs, n_ch, cfg):
        self.fs, self.cfg = fs, cfg
        self.mode = cfg["mode"]
        stages = []
        if self.mode != "level" and cfg["mains_hz"] < 0.5 * fs:
            b, a = signal.iirnotch(cfg["mains_hz"], 30, fs)
            stages.append(signal.tf2sos(b, a))
        if self.mode == "clench":
            hi = min(100.0, 0.45 * fs)
            if hi <= 30.0:
                sys.exit(f"Clench mode needs a sample rate above ~70 Hz (this source is {fs:.0f} Hz). "
                         "Use --mode level for slow signals.")
            stages.append(signal.butter(4, [30.0, hi], btype="band", fs=fs, output="sos"))
            self.chans = list(range(n_ch))
        elif self.mode == "blink":
            stages.append(signal.butter(2, [0.5, 8.0], btype="band", fs=fs, output="sos"))
            self.chans = [cfg["blink_channel"]]
        else:
            # level: the source already gives a "how strong is the action" number
            # (an EMG envelope, a key held down, a classifier output...). No filters.
            self.chans = list(range(n_ch))
        self.sos = np.vstack(stages) if stages else None
        if self.sos is not None:
            self.zi = np.zeros((self.sos.shape[0], 2, len(self.chans)))
        # envelope smoother for clench (power -> 4 Hz low-pass -> sqrt = moving RMS)
        self.env_b, self.env_a = signal.butter(1, 4.0, fs=fs)
        self.env_zi = np.zeros(1)

        self.n = 0
        self.last_trig = -1e9
        self.armed = True
        self.above = 0
        self.in_peak = False
        self.last_peak = None

    def process(self, x):
        """x: (n_samples, n_channels) raw µV -> (filtered, feature, trigger_flags)"""
        if len(x) == 0:
            return np.empty((0, len(self.chans))), np.empty(0), np.empty(0, bool)
        if self.sos is None:
            y = x[:, self.chans]
        else:
            y, self.zi = signal.sosfilt(self.sos, x[:, self.chans], axis=0, zi=self.zi)
        if self.mode == "level":
            feat = np.mean(y, axis=1)
        elif self.mode == "clench":
            p = np.mean(y ** 2, axis=1)
            env, self.env_zi = signal.lfilter(self.env_b, self.env_a, p, zi=self.env_zi)
            feat = np.sqrt(np.maximum(env, 0))
        else:
            # blinks are a big POSITIVE bump on frontal channels; the band-pass adds a
            # negative overshoot afterwards, so only the positive side is used
            feat = np.maximum(self.cfg["blink_polarity"] * y[:, 0], 0)
        trig = np.zeros(len(feat), bool)
        thr = self.cfg["threshold"] or GUESS_THRESHOLD[self.mode]
        fs = self.fs
        for i, v in enumerate(feat):
            self.n += 1
            t = self.n / fs
            if self.mode in ("clench", "level"):
                if self.armed:
                    self.above = self.above + 1 if v > thr else 0
                    if self.above >= self.cfg["hold_ms"] / 1000 * fs and \
                            t - self.last_trig >= self.cfg["refractory_ms"] / 1000:
                        trig[i] = True
                        self.last_trig, self.armed, self.above = t, False, 0
                elif v < 0.7 * thr:          # must relax before the next clench counts
                    self.armed = True
            else:
                if not self.in_peak and v > thr:
                    self.in_peak = True
                    if self.last_peak is not None and \
                            0.15 < t - self.last_peak <= self.cfg["double_blink_ms"] / 1000 and \
                            t - self.last_trig >= self.cfg["refractory_ms"] / 1000:
                        trig[i] = True
                        self.last_trig, self.last_peak = t, None
                    else:
                        self.last_peak = t
                elif self.in_peak and v < 0.6 * thr:
                    self.in_peak = False
        return y, feat, trig


# ----------------------------------------------------------------------------
# Serial link to the Nano
# ----------------------------------------------------------------------------
def find_arduino_port():
    from serial.tools import list_ports

    ports = list(list_ports.comports())
    for p in ports:
        if p.vid == 0x2341 or "arduino" in (p.description or "").lower():
            return p.device
    return ports[0].device if len(ports) == 1 else None


class Gripper:
    def __init__(self, port, baud=115200):
        self.state = "?"
        self.ser = None
        if port is None:
            print("Serial disabled: triggers will only be printed.")
            return
        import serial

        self.ser = serial.Serial(port, baud, timeout=0.1)
        time.sleep(1.5)                       # let the board finish booting
        print(f"Connected to Nano on {port} @ {baud}")
        threading.Thread(target=self._reader, daemon=True).start()
        self.send("status")

    def _reader(self):
        while True:
            try:
                raw = self.ser.readline().decode(errors="ignore").strip()
            except Exception as e:            # unplugged
                print("Serial error:", e)
                return
            if raw:
                print("[Nano]", raw)
                if raw.startswith("STATE "):
                    self.state = raw.split()[1]

    def send(self, cmd):
        print(f"-> {cmd}")
        if self.ser:
            self.ser.write((cmd + "\n").encode())
        elif cmd in ("open", "close"):
            self.state = cmd.upper().replace("CLOSE", "CLOSED")
        elif cmd == "toggle":
            self.state = "OPEN" if self.state == "CLOSED" else "CLOSED"


# ----------------------------------------------------------------------------
# Guided calibration
# ----------------------------------------------------------------------------
class Calibrator:
    def __init__(self, mode):
        action = {"clench": "CLENCH your jaw and hold", "blink": "DOUBLE-BLINK every ~2 s",
                  "level": "DO YOUR ACTION and hold it"}[mode]
        self.mode = mode
        self.phases = [("Get ready...", 3, None), ("RELAX - jaw loose, eyes open, stay still", 10, "rest"),
                       (action, 10 if mode == "blink" else 8, "act")]
        self.data = {"rest": [], "act": []}
        self.i, self.t_phase = 0, time.time()
        self.done, self.result = False, None

    def prompt(self):
        name, dur, _ = self.phases[self.i]
        return f"CALIBRATING: {name}  ({max(0, dur - (time.time() - self.t_phase)):.0f} s)"

    def feed(self, feat):
        if self.done:
            return
        name, dur, key = self.phases[self.i]
        if key and len(feat):
            self.data[key].extend(feat.tolist())
        if time.time() - self.t_phase >= dur:
            self.i += 1
            self.t_phase = time.time()
            if self.i == len(self.phases):
                self.finish()

    def finish(self):
        self.done = True
        rest, act = np.array(self.data["rest"]), np.array(self.data["act"])
        if len(rest) < 10 or len(act) < 10:
            self.result = (None, "Not enough data - is the stream running?")
            return
        r = np.percentile(rest, 98)
        a = np.percentile(act, 99.5 if self.mode == "blink" else 70)
        thr = r + 0.4 * (a - r)
        ratio = a / max(r, 1e-6)
        msg = f"rest(98%)={r:.3g}  action={a:.3g}  ratio={ratio:.1f}x  -> threshold {thr:.3g}"
        if ratio < 1.5:
            msg += "  WARNING: weak contrast - check sensor contact / make the action stronger"
            thr = max(thr, r * 1.3)
        self.result = (float(thr), msg)


# ----------------------------------------------------------------------------
# Live plot app
# ----------------------------------------------------------------------------
def run(args, cfg):
    import matplotlib
    import matplotlib.pyplot as plt

    for k in list(matplotlib.rcParams):          # free up keys like s, o, c, q, k, j
        if k.startswith("keymap."):
            matplotlib.rcParams[k] = []

    if args.source == "sim":
        src = SimSource(n_ch=args.channels or 8)
        src.mains_hz = cfg["mains_hz"]
    elif args.source == "lsl":
        src = LSLSource(args.stream, args.channels)
    else:
        src = load_source_plugin(args.source, args)
    port = None if args.no_serial else (args.port or find_arduino_port())
    if not args.no_serial and port is None:
        sys.exit("Could not find the Nano. Plug it in, close the Arduino Serial Monitor, "
                 "or pass --port COMx / --port /dev/tty.usbmodemXXXX. Use --list to see ports.")
    grip = Gripper(port, args.baud)
    det = Detector(src.fs, src.n_ch, cfg)

    fs = src.fs
    n_raw, n_feat = int(5 * fs), int(10 * fs)
    raw_buf = np.zeros((n_raw, len(det.chans)))
    feat_buf = np.zeros(n_feat)
    trig_buf = np.full(n_feat, np.nan)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), gridspec_kw={"height_ratios": [3, 2]})
    try:
        fig.canvas.manager.set_window_title("NeuroGrip bridge")
    except Exception:
        pass
    t_raw = np.arange(-n_raw, 0) / fs
    t_feat = np.arange(-n_feat, 0) / fs
    spacing = {"clench": 100.0, "blink": 200.0}.get(det.mode, 1.0)
    labels = [src.labels[c] for c in det.chans]
    raw_lines = [ax1.plot(t_raw, raw_buf[:, i] + i * spacing, lw=0.6)[0] for i in range(len(det.chans))]
    ax1.set_yticks([i * spacing for i in range(len(labels))], labels)
    ax1.set_ylim(-spacing, len(labels) * spacing)
    ax1.set_xlim(t_raw[0], 0)
    band = {"clench": "Filtered EEG, 30-100 Hz (EMG)", "blink": "Filtered EEG, 0.5-8 Hz (blinks)",
            "level": "Raw input (level mode)"}[det.mode]
    ax1.set_title(band)
    feat_line, = ax2.plot(t_feat, feat_buf, lw=1.2, label="feature" if det.mode == "level" else "feature (µV)")
    thr_line = ax2.axhline(cfg["threshold"] or GUESS_THRESHOLD[det.mode], color="r", ls="--", label="threshold")
    trig_pts, = ax2.plot(t_feat, trig_buf, "v", color="k", ms=10, label="trigger")
    ax2.set_xlim(t_feat[0], 0)
    ax2.set_xlabel("seconds")
    ax2.legend(loc="upper left")
    status = fig.text(0.01, 0.01, "", fontsize=10, family="monospace")
    fig.tight_layout(rect=(0, 0.07, 1, 1))

    st = {"cal": None, "msg": "SPACE=toggle  O/C=open/close  K=calibrate  UP/DOWN=threshold  S=save  Q=quit"}

    def thr():
        return cfg["threshold"] or GUESS_THRESHOLD[det.mode]

    def set_thr(v):
        cfg["threshold"] = float(v)
        thr_line.set_ydata([v, v])

    def on_key(ev):
        k = (ev.key or "").lower()
        if hasattr(src, "on_key"):           # let a source plugin use the keyboard too
            src.on_key(k, True)
        if k == " ":
            grip.send("toggle")
        elif k == "o":
            grip.send("open")
        elif k == "c":
            grip.send("close")
        elif k == "up":
            set_thr(thr() * 1.1)
        elif k == "down":
            set_thr(thr() / 1.1)
        elif k == "k":
            st["cal"] = Calibrator(det.mode)
        elif k == "s":
            save_cfg(cfg)
            st["msg"] = f"Saved to {CAL_FILE.name}"
        elif k == "j" and isinstance(src, SimSource):
            src.clenching = True
        elif k == "b" and isinstance(src, SimSource):
            src.blink()
        elif k in ("q", "escape"):
            plt.close(fig)

    def on_key_release(ev):
        if hasattr(src, "on_key"):
            src.on_key((ev.key or "").lower(), False)
        if (ev.key or "").lower() == "j" and isinstance(src, SimSource):
            src.clenching = False

    fig.canvas.mpl_connect("key_press_event", on_key)
    fig.canvas.mpl_connect("key_release_event", on_key_release)

    def roll(buf, new):
        n = len(new)
        if n >= len(buf):
            buf[:] = new[-len(buf):]
        elif n:
            buf[:-n] = buf[n:]
            buf[-n:] = new

    def tick():
        x = src.read()
        y, feat, trig = det.process(x)
        if len(feat):
            roll(raw_buf, y)
            roll(feat_buf, feat)
            roll(trig_buf, np.where(trig, feat, np.nan))
        cal = st["cal"]
        if cal:
            cal.feed(feat)
            if cal.done:
                t, msg = cal.result
                if t:
                    set_thr(t)
                print("Calibration:", msg)
                st["msg"] = msg + "   (press S to save)"
                st["cal"] = None
        elif trig.any():
            print(f"TRIGGER ({det.mode}) -> toggle")
            grip.send("toggle")

        sp = spacing
        if det.mode == "level":              # unknown units: scale the top plot to the data
            lo, hi = float(raw_buf.min()), float(raw_buf.max())
            sp = max(hi - lo, 1e-6) * 1.2
            raw_view = raw_buf - (lo + hi) / 2
            ax1.set_ylim(-sp, len(raw_lines) * sp)
            ax1.set_yticks([i * sp for i in range(len(labels))], labels)
        else:
            raw_view = raw_buf
        for i, ln in enumerate(raw_lines):
            ln.set_ydata(np.clip(raw_view[:, i], -sp / 2, sp / 2) + i * sp)
        feat_line.set_ydata(feat_buf)
        trig_pts.set_ydata(trig_buf)
        top = max(thr() * 2.0, np.nanmax(feat_buf) * 1.1, 1.0)
        ax2.set_ylim(0, top)
        head = st["cal"].prompt() if st["cal"] else st["msg"]
        unit = "" if det.mode == "level" else " µV"
        status.set_text(f"GRIP: {grip.state:<7} threshold={thr():8.3g}{unit}   mode={det.mode}\n{head}")
        fig.canvas.draw_idle()

    timer = fig.canvas.new_timer(interval=40)
    timer.add_callback(tick)
    timer.start()
    plt.show()


def save_cfg(cfg):
    CAL_FILE.write_text(json.dumps(cfg, indent=2))
    print("Saved", CAL_FILE)


def list_everything():
    from serial.tools import list_ports

    print("Serial ports:")
    for p in list_ports.comports():
        tag = "  <- Arduino" if p.vid == 0x2341 or "arduino" in (p.description or "").lower() else ""
        print(f"  {p.device:20s} {p.description}{tag}")
    try:
        from pylsl import resolve_streams

        print("LSL streams (3 s search):")
        for s in resolve_streams(wait_time=3.0):
            print(f"  name='{s.name()}' type={s.type()} ch={s.channel_count()} fs={s.nominal_srate()}")
    except Exception as e:
        print("  pylsl not usable:", e)


def main():
    ap = argparse.ArgumentParser(description="NeuroGrip: EEG -> gripper bridge")
    ap.add_argument("--source", default="lsl",
                    help="lsl = Unicorn (or any EEG) via LSL, sim = fake data, "
                         "or a path to a source plugin .py file (see sources/)")
    ap.add_argument("--channels", type=int,
                    help="use only the first N channels of the stream (default 8, e.g. 4 for a Muse)")
    ap.add_argument("--stream", help="exact LSL stream name (default: first EEG/Data/UN* stream)")
    ap.add_argument("--port", help="serial port of the Nano, e.g. COM5 or /dev/tty.usbmodem1101")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--no-serial", action="store_true", help="run without the Nano attached")
    ap.add_argument("--mode", choices=["clench", "blink", "level"],
                    help="what to detect (default clench). level = trigger when the raw input "
                         "stays above the threshold (EMG envelopes, buttons, classifier outputs)")
    ap.add_argument("--threshold", type=float, help="override the saved threshold (µV, or input units in level mode)")
    ap.add_argument("--hold-ms", type=int)
    ap.add_argument("--refractory-ms", type=int)
    ap.add_argument("--mains", type=int, choices=[50, 60], help="power-line frequency (default 60)")
    ap.add_argument("--list", action="store_true", help="list serial ports and LSL streams, then exit")
    args = ap.parse_args()

    if args.list:
        list_everything()
        return

    cfg = dict(DEFAULTS)
    if CAL_FILE.exists():
        saved = json.loads(CAL_FILE.read_text())
        if args.mode and saved.get("mode") != args.mode:
            print(f"Saved calibration is for '{saved.get('mode')}', ignoring its threshold.")
            saved.pop("threshold", None)
        cfg.update(saved)
        print(f"Loaded {CAL_FILE.name}: threshold={cfg['threshold']}")
    for key, val in (("mode", args.mode), ("threshold", args.threshold), ("hold_ms", args.hold_ms),
                     ("refractory_ms", args.refractory_ms), ("mains_hz", args.mains)):
        if val is not None:
            cfg[key] = val
    if cfg["threshold"] is None:
        unit = "" if cfg["mode"] == "level" else " µV"
        print(f"No calibration yet: using a guess of {GUESS_THRESHOLD[cfg['mode']]}{unit}. Press K to calibrate.")
    run(args, cfg)


if __name__ == "__main__":
    main()
