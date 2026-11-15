"""
NeuroGrip LIVE - one window: brain waves, jaw power vs threshold, gripper state.

    g.Pype pipeline (gpype_pipeline.py)  --UDP-->  THIS WINDOW  --serial 9600-->  UNO Q (GripTest sketch)
      headset or fake headset                     g.Pype trigger logic            't' = toggle the gripper
      filters, FFT, BandPower                     (GPypeTrigger from gpype_trigger.py)

Usage (Windows: put "py -3.13" in front instead of "python"):
    python neurogrip_live.py --sim --no-board     # fake headset, no Arduino. Hold SPACE = jaw clench
    python neurogrip_live.py --sim                # fake headset, real gripper on the UNO Q
    python neurogrip_live.py                      # real Unicorn headset + real gripper
    python neurogrip_live.py --calibrate          # real headset: 24 s guided calibration
    python neurogrip_live.py --muscle --no-board  # REAL muscle bursts from the g.tec recordings.
                                                  # Hold SPACE = replay a burst (clench-like signal)
    python neurogrip_live.py --dataset --no-board # REAL g.tec SSVEP recording replayed through g.Pype.
                                                  # Hold SPACE = the person looks at the 12 Hz LED

This script starts gpype_pipeline.py for you (use --no-pipeline if it is already running).

Keys (click the window first):
    SPACE (hold)  sim: jaw clench          real headset: manual toggle (backup)
    B             sim: one blink (tap twice quickly = double blink)
    T / O / C     manual toggle / open / close
    UP / DOWN     raise / lower the threshold
    S             save the threshold to calibration.json (real headset only)
    Q / ESC       quit
"""
import argparse
import collections
import importlib.util
import pathlib
import socket
import subprocess
import sys
import threading
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gpype_trigger as gt                     # noqa: E402  (the g.Pype trigger logic)
from fake_eeg import CONTROL_PORT, FS, LABELS  # noqa: E402

VIEW_PORT = 56012
# The fake headset's jaw power sits around 3-20 at rest and 500-900 when clenched.
SIM_THRESHOLDS = {"jaw_on": 120.0, "jaw_off": 40.0, "blink_uv": 80.0}
# Real recorded muscle bursts: calm ~6 (max ~18), bursts ~60-200.
MUSCLE_THRESHOLDS = {"jaw_on": 35.0, "jaw_off": 15.0, "blink_uv": 120.0}


# ----------------------------------------------------------------------------
# Talking to the board
# ----------------------------------------------------------------------------
class Board:
    def __init__(self, port, baud):
        self.ser = None
        self.angle = None
        if port is None:
            print("No board: triggers are shown on screen only.")
            return
        import serial
        print(f"Opening board on {port} at {baud} baud")
        self.ser = serial.Serial(port, baud, timeout=0.1)
        time.sleep(2)                                 # board may reset when the port opens
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        while True:
            try:
                line = self.ser.readline().decode(errors="ignore").strip()
            except Exception as e:
                print("Serial error:", e)
                return
            if line:
                print("[board]", line)
                if line.startswith("Angle:"):
                    try:
                        self.angle = int(line.split(":")[1])
                    except ValueError:
                        pass

    def send(self, cmd):
        print(f"  -> board: '{cmd}'")
        if self.ser:
            self.ser.write((cmd + "\n").encode())


# ----------------------------------------------------------------------------
# Emergency fake data WITHOUT g.Pype (only if g.Pype will not install)
# ----------------------------------------------------------------------------
def start_fallback_sim():
    from scipy import signal
    from fake_eeg import FakeHead

    head = FakeHead()
    head.listen()
    out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    blink_sos = signal.butter(2, [0.5, 10], btype="band", fs=FS, output="sos")
    view_sos = np.vstack([signal.butter(2, [0.5, 100], btype="band", fs=FS, output="sos"),
                          signal.butter(2, [58, 62], btype="bandstop", fs=FS, output="sos")])
    notch_sos = signal.butter(2, [58, 62], btype="bandstop", fs=FS, output="sos")
    zb = np.zeros((blink_sos.shape[0], 2, 3))
    zv = np.zeros((view_sos.shape[0], 2, 3))
    zn = np.zeros((notch_sos.shape[0], 2, 3))
    win = np.hanning(64)
    freqs = np.fft.rfftfreq(64, 1 / FS)
    band = (freqs >= 30) & (freqs <= 100)

    def loop():
        nonlocal zb, zv, zn
        buf = collections.deque(maxlen=64)
        t0, i = time.monotonic(), 0
        while True:
            x = head.sample()[None, :]
            b, zb = signal.sosfilt(blink_sos, x, axis=0, zi=zb)
            v, zv = signal.sosfilt(view_sos, x, axis=0, zi=zv)
            n, zn = signal.sosfilt(notch_sos, x, axis=0, zi=zn)
            out.sendto(b[0].tobytes(), ("127.0.0.1", 56010))
            out.sendto(v[0].tobytes(), ("127.0.0.1", VIEW_PORT))
            buf.append(n[0])
            i += 1
            if i % 32 == 0 and len(buf) == 64:
                spec = 2 * np.abs(np.fft.rfft(np.array(buf) * win[:, None], axis=0)) / win.sum()
                out.sendto((spec[band] ** 2).sum(axis=0).tobytes(), ("127.0.0.1", 56011))
            delay = t0 + i / FS - time.monotonic()
            if delay > 0:
                time.sleep(delay)

    threading.Thread(target=loop, daemon=True).start()
    print("!! FALLBACK SIM: fake data made in plain Python, NOT through g.Pype.")


# ----------------------------------------------------------------------------
# Starting the g.Pype pipeline
# ----------------------------------------------------------------------------
def start_pipeline(sim, show_scope, muscle=False):
    if importlib.util.find_spec("gpype") is None:
        if muscle:
            sys.exit("g.Pype is not installed for this Python. Run:  py -3.13 -m pip install -r requirements.txt")
        if sim:
            print("\n!! g.Pype is not installed for this Python. Using the fallback sim.\n"
                  "   (Install it with:  py -3.13 -m pip install gpype)\n")
            start_fallback_sim()
            return None, "fallback sim (no g.Pype)"
        sys.exit("g.Pype is not installed for this Python. Run:  py -3.13 -m pip install gpype")
    cmd = [sys.executable, str(HERE / "gpype_pipeline.py")]
    if muscle:
        cmd.append("--muscle")
    elif sim:
        cmd.append("--sim")
    if not show_scope:
        cmd.append("--no-scope")
    print("Starting g.Pype pipeline:", " ".join(cmd[1:]))
    name = ("REAL muscle bursts from g.tec recordings, replayed through g.Pype" if muscle else
            "g.Pype pipeline, FAKE headset" if sim else "g.Pype pipeline, Unicorn headset")
    return subprocess.Popen(cmd), name


# ----------------------------------------------------------------------------
# The window
# ----------------------------------------------------------------------------
def run_window(a, trig, board, proc, source_name):
    import matplotlib
    import matplotlib.pyplot as plt

    for k in list(matplotlib.rcParams):          # free up keys like s, o, c, q, t, b
        if k.startswith("keymap."):
            matplotlib.rcParams[k] = []
    plt.style.use("dark_background")

    view = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    view.bind(("127.0.0.1", VIEW_PORT))
    view.setblocking(False)
    ctrl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    n_wave = int(5 * FS)
    waves = np.zeros((n_wave, 3))
    jaw = collections.deque(maxlen=200)          # (time, power), ~25 s
    trig_marks = collections.deque(maxlen=20)    # (time, power, label)
    st = {"grip": "OPEN" if a.cmd != "c" else "?", "held": False, "release_at": None,
          "msg": "", "msg_until": 0.0, "got_data": False, "flash_until": 0.0}
    t_start = time.monotonic()

    fig = plt.figure(figsize=(12, 7.5))
    try:
        fig.canvas.manager.set_window_title("NeuroGrip LIVE")
    except Exception:
        pass
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 2], left=0.07, right=0.98, top=0.86, bottom=0.12, hspace=0.35)
    ax1, ax2 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])

    spacing = 90.0
    colors = ["#7dd3fc", "#c4b5fd", "#f9a8d4"]
    t_w = np.arange(-n_wave, 0) / FS
    wave_lines = [ax1.plot(t_w, waves[:, i] + (2 - i) * spacing, lw=0.7, color=colors[i])[0] for i in range(3)]
    labels = ["O1", "Oz", "O2"] if a.muscle else LABELS
    view_idx = [5, 6, 7] if a.muscle else [0, 1, 2]
    ax1.set_yticks([(2 - i) * spacing for i in range(3)], labels)
    ax1.set_ylim(-spacing * 0.7, 2.7 * spacing)
    ax1.set_xlim(t_w[0], 0)
    ax1.set_title("REAL recorded EEG  (g.Pype: 50 Hz notch + 0.5-100 Hz band-pass)" if a.muscle else
                  "Brain waves  (g.Pype: 0.5-100 Hz band-pass + 60 Hz notch)", loc="left", fontsize=11)
    ax1.grid(alpha=0.15)

    pw_line, = ax2.plot([], [], lw=2.0, color="#a3e635", label="jaw muscle power")
    pw_hot, = ax2.plot([], [], lw=3.0, color="#f87171")
    thr_line = ax2.axhline(trig.jaw_on, color="#ef4444", ls="--", lw=1.5, label="threshold")
    off_line = ax2.axhline(trig.jaw_off, color="#9ca3af", ls=":", lw=1.0, label="re-arm level")
    mk_pts, = ax2.plot([], [], "v", color="#fde047", ms=13, label="TRIGGER -> gripper")
    ax2.set_xlim(-10, 0)
    ax2.set_title(f"Muscle (clench) power  (g.Pype: FFT -> BandPower 30-100 Hz, {'all 8 channels' if a.muscle else 'C3/C4'})     x-axis: seconds ago", loc="left", fontsize=11)
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(alpha=0.15)

    fig.text(0.07, 0.93, "NeuroGrip", fontsize=20, weight="bold")
    fig.text(0.07, 0.895, f"Source: {source_name}", fontsize=10, color="#9ca3af")
    grip_txt = fig.text(0.98, 0.915, "", fontsize=22, weight="bold", ha="right")
    status = fig.text(0.07, 0.025, "", fontsize=10, family="monospace")
    hint = ("AUTO (real data): press SPACE = replay one real recorded muscle burst     MANUAL: J = toggle, O/C = open/close     "
            "UP/DOWN = threshold   Q = quit" if a.muscle else
            "Hold SPACE = jaw clench   B = blink   J/T = manual toggle   O/C = open/close   UP/DOWN = threshold   Q = quit"
            if a.sim else
            "SPACE/J/T = manual toggle   O/C = open/close   UP/DOWN = threshold   S = save   Q = quit")
    fig.text(0.07, 0.055, hint, fontsize=9, color="#9ca3af")

    def say(msg, secs=3.0):
        st["msg"], st["msg_until"] = msg, time.monotonic() + secs

    def fire(label):
        if a.cmd == "t":
            st["grip"] = "CLOSED" if st["grip"] == "OPEN" else "OPEN"
        elif a.cmd == "c":
            st["grip"] = "CLOSED"
        elif a.cmd == "o":
            st["grip"] = "OPEN"
        st["flash_until"] = time.monotonic() + 0.6
        print(f"[{time.strftime('%H:%M:%S')}] TRIGGER: {label} -> '{a.cmd}'   gripper now {st['grip']}")
        board.send(a.cmd)

    def manual(cmd):
        st["grip"] = {"o": "OPEN", "c": "CLOSED"}.get(cmd, "CLOSED" if st["grip"] == "OPEN" else "OPEN")
        board.send(cmd)

    def set_thr(on):
        ratio = trig.jaw_off / trig.jaw_on if trig.jaw_on else 0.4
        trig.jaw_on, trig.jaw_off = on, on * ratio
        thr_line.set_ydata([trig.jaw_on] * 2)
        off_line.set_ydata([trig.jaw_off] * 2)
        say(f"threshold = {trig.jaw_on:.3g}")

    def on_key(ev):
        k = (ev.key or "").lower()
        if k == " ":
            if a.sim:
                st["held"], st["release_at"] = True, None
            elif not st["held"]:                     # real headset: SPACE = manual toggle
                st["held"] = True
                manual("t")
        elif k == "b" and a.sim and not a.muscle:
            ctrl.sendto(b"blink", ("127.0.0.1", CONTROL_PORT))
        elif k in ("j", "t", "o", "c"):
            manual("t" if k == "j" else k)          # J = manual toggle
        elif k == "up":
            set_thr(trig.jaw_on * 1.15)
        elif k == "down":
            set_thr(trig.jaw_on / 1.15)
        elif k == "s":
            if a.sim:
                say("Not saved: sim thresholds are separate from your headset calibration")
            else:
                cal = gt.load_calibration()
                cal.update({"jaw_on": round(trig.jaw_on, 4), "jaw_off": round(trig.jaw_off, 4)})
                gt.CAL_FILE.write_text(gt.json.dumps(cal, indent=2))
                say(f"Saved to {gt.CAL_FILE.name}")
        elif k in ("q", "escape"):
            plt.close(fig)

    def on_release(ev):
        if (ev.key or "").lower() == " ":
            if a.sim:
                st["release_at"] = time.monotonic() + 0.12   # ignore key auto-repeat flicker
            else:
                st["held"] = False

    fig.canvas.mpl_connect("key_press_event", on_key)
    fig.canvas.mpl_connect("key_release_event", on_release)

    def tick():
        now = time.monotonic()
        # --- keyboard -> fake headset
        if a.sim:
            if st["release_at"] and now > st["release_at"]:
                st["held"], st["release_at"] = False, None
                ctrl.sendto(b"clench 0", ("127.0.0.1", CONTROL_PORT))
            if st["held"]:
                ctrl.sendto(b"clench 1", ("127.0.0.1", CONTROL_PORT))

        # --- g.Pype features -> trigger logic
        for ev in trig.poll(0.0, record=True):
            trig_marks.append((now, trig.last_jaw, ev))
            fire(ev)
        for p in trig.raw["jaw"]:
            jaw.append((now, p))
        trig.raw = {"blink": [], "jaw": []}

        # --- g.Pype wide-band view -> waves
        new = []
        while True:
            try:
                payload, _ = view.recvfrom(65535)
            except (BlockingIOError, ConnectionResetError):
                break
            if len(payload) % 8 == 0 and len(payload) >= 24:
                v = np.frombuffer(payload, dtype=np.float64)
                if v.size > max(view_idx):
                    new.append(v[view_idx])
        if new:
            st["got_data"] = True
            new = np.array(new)[-n_wave:]
            waves[:-len(new)] = waves[len(new):]
            waves[-len(new):] = new
        for i, ln in enumerate(wave_lines):
            ln.set_ydata(np.clip(waves[:, i], -spacing * 0.65, spacing * 0.65) + (2 - i) * spacing)

        if jaw:
            tj = np.array([t for t, _ in jaw]) - now
            pj = np.array([p for _, p in jaw])
            pw_line.set_data(tj, pj)
            pw_hot.set_data(tj, np.where(pj > trig.jaw_on, pj, np.nan))
            top = max(trig.jaw_on * 2.5, float(pj[tj > -10].max(initial=0)) * 1.15)
            ax2.set_ylim(0, top)
        if trig_marks:
            mk_pts.set_data([t - now for t, _, _ in trig_marks], [p for _, p, _ in trig_marks])

        # --- text
        flash = now < st["flash_until"]
        g = st["grip"]
        grip_txt.set_text(f"GRIPPER: {g}")
        grip_txt.set_color("#fde047" if flash else ("#4ade80" if g == "OPEN" else "#f87171" if g == "CLOSED" else "white"))
        if proc is not None and proc.poll() is not None:
            line = "!! The g.Pype pipeline stopped - look at the black console window for the error."
        elif not st["got_data"]:
            line = "Waiting for data from g.Pype..." + ("" if now - t_start < 15 else
                                                       "  (nothing yet - is the headset on and paired?)")
        else:
            line = (f"jaw power {trig.last_jaw:8.1f}   threshold {trig.jaw_on:6.1f}   "
                    f"board: {'connected' if board.ser else 'NOT connected (screen only)'}"
                    + (f"   servo angle {board.angle}" if board.angle is not None else ""))
        if now < st["msg_until"]:
            line += "   |  " + st["msg"]
        status.set_text(line)
        fig.canvas.draw_idle()

    timer = fig.canvas.new_timer(interval=40)
    timer.add_callback(tick)
    timer.start()
    plt.show()


VERSION = "v4 (J = manual toggle, --muscle)"


def main():
    print(f"NeuroGrip LIVE {VERSION}")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sim", action="store_true", help="fake headset driven by the SPACE key (through g.Pype)")
    ap.add_argument("--no-board", action="store_true", help="don't talk to the UNO Q, just show triggers")
    ap.add_argument("--serial", help="UNO Q port, e.g. COM5 (default: find it automatically)")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--cmd", default="t", choices=["t", "o", "c"], help="sent on each trigger (t = toggle)")
    ap.add_argument("--no-pipeline", action="store_true", help="gpype_pipeline.py is already running elsewhere")
    ap.add_argument("--gpype-scope", action="store_true", help="sim: also open g.Pype's own scope window")
    ap.add_argument("--no-gpype-scope", action="store_true", help="real headset: don't open g.Pype's scope")
    ap.add_argument("--fallback-sim", action="store_true", help="emergency: fake data without g.Pype")
    ap.add_argument("--calibrate", action="store_true", help="real headset: guided 24 s calibration, then exit")
    ap.add_argument("--jaw-on", type=float)
    ap.add_argument("--jaw-off", type=float)
    ap.add_argument("--blink-uv", type=float)
    ap.add_argument("--no-blink", action="store_true", help="ignore double blinks, jaw clench only")
    ap.add_argument("--cooldown", type=float, default=1.0)
    ap.add_argument("--dataset", nargs="?", const="data/subject_1_fvep_led_training_1.mat",
                    help="replay REAL g.tec SSVEP EEG (default: subject 1, run 1). SPACE = look at the LED")
    ap.add_argument("--led", type=int, default=12, choices=[9, 10, 12, 15],
                    help="dataset: which LED's recorded trials SPACE plays at the start")
    ap.add_argument("--muscle", action="store_true",
                    help="replay REAL muscle bursts found in the g.tec recordings. SPACE = burst (clench)")
    ap.add_argument("--freq", type=int, default=12, choices=[9, 10, 12, 15],
                    help="dataset: the LED frequency that moves the gripper")
    a = ap.parse_args()
    if a.dataset:
        return main_dataset(a)
    if a.muscle:
        from dataset_replay import DATA_DIR, MUSCLE_FILES
        missing = [f for f in MUSCLE_FILES if not (DATA_DIR / f).exists()]
        if missing:
            sys.exit(f"Missing g.tec data files in {DATA_DIR}: {', '.join(missing)}. See data/README.md.")
        a.sim, a.no_blink = True, True
    if a.fallback_sim:
        a.sim = True

    th = dict(MUSCLE_THRESHOLDS) if a.muscle else dict(SIM_THRESHOLDS) if a.sim else {"jaw_on": 40.0, "jaw_off": 15.0, "blink_uv": 120.0}
    if not a.sim:
        cal = gt.load_calibration()
        if cal:
            print(f"Using {gt.CAL_FILE.name}: {cal}")
            th.update(cal)
        else:
            print("No calibration.json yet - using guesses. Run with --calibrate first for best results.")
    for k in ("jaw_on", "jaw_off", "blink_uv"):
        if getattr(a, k) is not None:
            th[k] = getattr(a, k)

    try:
        trig = gt.GPypeTrigger(blink_uv=th["blink_uv"], jaw_on=th["jaw_on"], jaw_off=th["jaw_off"],
                               cooldown_s=a.cooldown, enable_blink=not a.no_blink,
                               jaw_ch=range(8) if a.muscle else (1, 2))
    except OSError:
        sys.exit("UDP ports 56010/56011 are busy. Close any other NeuroGrip / gpype_trigger window and try again.")

    proc = None
    if a.fallback_sim:
        start_fallback_sim()
        source_name = "fallback sim (no g.Pype)"
    elif a.no_pipeline:
        source_name = "g.Pype pipeline (started separately)"
    else:
        show_scope = a.gpype_scope if a.sim else not a.no_gpype_scope
        proc, source_name = start_pipeline(a.sim, show_scope, a.muscle)

    try:
        if a.calibrate:
            time.sleep(4)                    # let the headset connect
            gt.calibrate(trig)
            return
        port = None
        if not a.no_board:
            port = a.serial or gt.find_board_port()
        board = Board(port, a.baud)
        run_window(a, trig, board, proc, source_name)
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()


def main_dataset(a):
    import dataset_window as dw
    path = pathlib.Path(a.dataset)
    if not path.is_absolute():
        path = HERE / path
    if not path.exists():
        sys.exit(f"Can't find {path}. The g.tec .mat files belong in the data folder next to this script (see data/README.md).")
    th = dict(dw.DATASET_THRESHOLDS)
    if a.jaw_on is not None:
        th["jaw_on"] = a.jaw_on
    if a.jaw_off is not None:
        th["jaw_off"] = a.jaw_off
    try:
        trig = gt.GPypeTrigger(jaw_on=th["jaw_on"], jaw_off=th["jaw_off"], cooldown_s=a.cooldown,
                               enable_blink=False)
    except OSError:
        sys.exit("UDP ports are busy. Close any other NeuroGrip / gpype_trigger window and try again.")
    proc = None
    if importlib.util.find_spec("gpype") is None:
        sys.exit("g.Pype is not installed for this Python. Run:  py -3.13 -m pip install -r requirements.txt")
    if not a.no_pipeline:
        proc = dw.start_dataset_pipeline(path, a.led, a.gpype_scope)
    try:
        port = None if a.no_board else (a.serial or gt.find_board_port())
        board = Board(port, a.baud)
        dw.run_dataset_window(a, trig, board, proc, path)
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
