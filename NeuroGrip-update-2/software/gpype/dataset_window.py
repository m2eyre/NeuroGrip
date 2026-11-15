"""
NeuroGrip LIVE, dataset mode: REAL recorded g.tec SSVEP EEG -> g.Pype -> gripper.

    data/*.mat (g.tec recording) -> g.Pype source node -> g.Pype Bandpass 5-45 Hz -> UDP 56012 -> waves + SSVEP detector
                                                       -> g.Pype FFT (2 s)         -> UDP 56014 -> live spectrum
    SSVEP detector (CCA, 3 s window) -> GPypeTrigger logic (threshold, hold, re-arm, cooldown) -> 't' -> UNO Q

Hold SPACE = play the recorded trials where the person looked at the flashing LED.
Let go     = play the recorded breaks where they looked at nothing.
1-4        = which LED's trials SPACE plays (9 / 10 / 12 / 15 Hz). The gripper only
             answers the --freq LED (12 Hz by default), so the others show it ignoring them.
Started from neurogrip_live.py --dataset.
"""
import collections
import pathlib
import socket
import subprocess
import sys
import time

import numpy as np

from dataset_replay import FREQS, FS, LABELS, load_ssvep, segments

VIEW_PORT, SPEC_PORT, CONTROL_PORT = 56012, 56014, 56013
WIN_S = 3.0                       # detector window
SHOW = [5, 6, 7, 2]               # O1, Oz, O2, POz
DATASET_THRESHOLDS = {"jaw_on": 0.15, "jaw_off": 0.05}


# ----------------------------------------------------------------------------
# SSVEP detector: canonical correlation with sine/cosine templates (+2 harmonics)
# ----------------------------------------------------------------------------
_REF_CACHE = {}


def refs(f, n, harmonics=3):
    key = (f, n)
    if key not in _REF_CACHE:
        t = np.arange(n) / FS
        cols = [fn(2 * np.pi * h * f * t) for h in range(1, harmonics + 1) for fn in (np.sin, np.cos)]
        r = np.column_stack(cols)
        _REF_CACHE[key], _ = np.linalg.qr(r - r.mean(0))
    return _REF_CACHE[key]


def cca_scores(x):
    """x: (n, ch) EEG -> {freq: canonical correlation}."""
    q, _ = np.linalg.qr(x - x.mean(0))
    return {f: float(np.linalg.svd(q.T @ refs(f, len(x)), compute_uv=False)[0]) for f in FREQS}


def offline_accuracy(path, win_s=4.0):
    """Classify every recorded trial (first win_s seconds after 0.5 s) into one of the 4 LEDs."""
    from scipy import signal
    eeg, lab = load_ssvep(path)
    eeg = signal.sosfilt(signal.butter(4, [5, 45], "band", fs=FS, output="sos"), eeg, axis=0)
    n, ok, tot = int(win_s * FS), 0, 0
    for c, s, e in segments(lab):
        if c == 0 or e - s < n + FS // 2:
            continue
        r = cca_scores(eeg[s + FS // 2: s + FS // 2 + n])
        ok += max(r, key=r.get) == c
        tot += 1
    return ok, tot


# ----------------------------------------------------------------------------
def start_dataset_pipeline(path, led, show_scope):
    cmd = [sys.executable, str(pathlib.Path(__file__).with_name("gpype_pipeline.py")),
           "--dataset", str(path), "--led", str(led)]
    if not show_scope:
        cmd.append("--no-scope")
    print("Starting g.Pype pipeline:", " ".join(cmd[1:]))
    return subprocess.Popen(cmd)


def run_dataset_window(a, trig, board, proc, path):
    import matplotlib
    import matplotlib.pyplot as plt

    for k in list(matplotlib.rcParams):
        if k.startswith("keymap."):
            matplotlib.rcParams[k] = []
    plt.style.use("dark_background")

    target = a.freq
    ok, tot = offline_accuracy(path)
    acc_txt = f"4-LED accuracy on this recording: {ok}/{tot} trials = {100 * ok / max(tot, 1):.0f}%  (CCA, 4 s, chance 25%)"
    print(acc_txt)

    view = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    view.bind(("127.0.0.1", VIEW_PORT))
    view.setblocking(False)
    spec = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    spec.bind(("127.0.0.1", SPEC_PORT))
    spec.setblocking(False)
    ctrl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    n_buf = int(5 * FS)
    buf = np.zeros((n_buf, 8))
    st = {"grip": "OPEN" if a.cmd != "c" else "?", "held": False, "release_at": None, "led": a.led,
          "n": 0, "last_det": 0.0, "flash_until": 0.0, "msg": "", "msg_until": 0.0, "score": 0.0}
    score_hist = collections.deque(maxlen=200)
    marks = collections.deque(maxlen=20)
    t_start = time.monotonic()

    fig = plt.figure(figsize=(13, 8))
    try:
        fig.canvas.manager.set_window_title("NeuroGrip LIVE - g.tec dataset replay")
    except Exception:
        pass
    gs = fig.add_gridspec(2, 2, height_ratios=[3, 2], width_ratios=[3, 2], left=0.06, right=0.98,
                          top=0.82, bottom=0.12, hspace=0.38, wspace=0.18)
    ax1 = fig.add_subplot(gs[0, :])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])

    spacing = 40.0
    colors = ["#7dd3fc", "#c4b5fd", "#f9a8d4", "#fcd34d"]
    tw = np.arange(-n_buf, 0) / FS
    nl = len(SHOW)
    lines = [ax1.plot(tw, np.zeros(n_buf) + (nl - 1 - i) * spacing, lw=0.7, color=colors[i])[0] for i in range(nl)]
    ax1.set_yticks([(nl - 1 - i) * spacing for i in range(nl)], [LABELS[c] for c in SHOW])
    ax1.set_ylim(-spacing * 0.7, (nl - 0.3) * spacing)
    ax1.set_xlim(tw[0], 0)
    ax1.set_title("REAL recorded EEG over the visual cortex  (g.Pype: 5-45 Hz band-pass)", loc="left", fontsize=11)
    ax1.grid(alpha=0.15)

    sc_line, = ax2.plot([], [], lw=2.0, color="#a3e635", label=f"{target} Hz LED score")
    sc_hot, = ax2.plot([], [], lw=3.0, color="#f87171")
    thr_line = ax2.axhline(trig.jaw_on, color="#ef4444", ls="--", lw=1.5, label="threshold")
    off_line = ax2.axhline(trig.jaw_off, color="#9ca3af", ls=":", lw=1.0, label="re-arm level")
    mk, = ax2.plot([], [], "v", color="#fde047", ms=13, label="TRIGGER -> gripper")
    ax2.set_xlim(-20, 0)
    ax2.set_ylim(-0.6, 0.55)
    ax2.set_title(f"SSVEP detector: is the person looking at the {target} Hz LED?  (seconds ago)", loc="left", fontsize=10, pad=14)
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(alpha=0.15)

    freqs = np.fft.rfftfreq(512, 1 / FS)
    keep = (freqs >= 4) & (freqs <= 34)
    sp_line, = ax3.plot(freqs[keep], np.zeros(keep.sum()), lw=1.5, color="#7dd3fc")
    ax3.axvline(2 * target, color="#ef4444", ls=":", lw=1)
    ax3.text(2 * target, 1.0, f"{2 * target}", color="#ef4444", ha="center", va="bottom", fontsize=8,
             transform=ax3.get_xaxis_transform())
    for f in FREQS:
        ax3.axvline(f, color="#ef4444" if f == target else "#6b7280", ls="--" if f == target else ":", lw=1)
        ax3.text(f, 1.0, f"{f}", color="#ef4444" if f == target else "#9ca3af", ha="center", va="bottom",
                 fontsize=8, transform=ax3.get_xaxis_transform())
    ax3.set_xlim(4, 34)
    ax3.set_title(f"g.Pype FFT spectrum (O1/Oz/O2). Red = {target} Hz + harmonic", loc="left", fontsize=10, pad=14)
    ax3.set_xlabel("Hz")
    ax3.grid(alpha=0.15)

    fig.text(0.06, 0.935, "NeuroGrip", fontsize=20, weight="bold")
    fig.text(0.06, 0.895, f"Source: REAL g.tec SSVEP recording '{path.name}' replayed through a g.Pype pipeline",
             fontsize=10, color="#9ca3af")
    fig.text(0.06, 0.870, acc_txt, fontsize=10, color="#9ca3af")
    grip_txt = fig.text(0.98, 0.92, "", fontsize=22, weight="bold", ha="right")
    play_txt = fig.text(0.98, 0.875, "", fontsize=11, ha="right")
    status = fig.text(0.06, 0.025, "", fontsize=10, family="monospace")
    fig.text(0.06, 0.06, "AUTO (real data): hold SPACE = look at the LED, 1/2/3/4 = which LED (9/10/12/15 Hz)     "
             "MANUAL: J = toggle, O/C = open/close     UP/DOWN = threshold   Q = quit", fontsize=9, color="#9ca3af")

    def say(msg, secs=3.0):
        st["msg"], st["msg_until"] = msg, time.monotonic() + secs

    def fire(label):
        st["grip"] = {"o": "OPEN", "c": "CLOSED"}.get(a.cmd, "CLOSED" if st["grip"] == "OPEN" else "OPEN")
        st["flash_until"] = time.monotonic() + 0.6
        print(f"[{time.strftime('%H:%M:%S')}] TRIGGER: {label} -> '{a.cmd}'   gripper now {st['grip']}")
        board.send(a.cmd)

    def manual(cmd):
        st["grip"] = {"o": "OPEN", "c": "CLOSED"}.get(cmd, "CLOSED" if st["grip"] == "OPEN" else "OPEN")
        st["flash_until"] = time.monotonic() + 0.6
        say(f"MANUAL: gripper {st['grip']}")
        print(f"[{time.strftime('%H:%M:%S')}] MANUAL -> '{cmd}'   gripper now {st['grip']}")
        board.send(cmd)

    def set_thr(on):
        trig.jaw_on, trig.jaw_off = on, on / 3
        thr_line.set_ydata([on] * 2)
        off_line.set_ydata([on / 3] * 2)
        say(f"threshold = {on:.3f}")

    def on_key(ev):
        k = (ev.key or "").lower()
        if k == " ":
            st["held"], st["release_at"] = True, None
        elif k in ("1", "2", "3", "4"):
            st["led"] = FREQS[int(k) - 1]
            ctrl.sendto(f"led {st['led']}".encode(), ("127.0.0.1", CONTROL_PORT))
            say(f"SPACE now plays the trials where the person looked at the {st['led']} Hz LED")
        elif k in ("j", "t", "o", "c"):
            manual("t" if k == "j" else k)          # J = manual toggle, no brain data needed
        elif k == "up":
            set_thr(trig.jaw_on + 0.02)
        elif k == "down":
            set_thr(max(0.02, trig.jaw_on - 0.02))
        elif k in ("q", "escape"):
            plt.close(fig)

    def on_release(ev):
        if (ev.key or "").lower() == " ":
            st["release_at"] = time.monotonic() + 0.12

    fig.canvas.mpl_connect("key_press_event", on_key)
    fig.canvas.mpl_connect("key_release_event", on_release)
    ctrl.sendto(f"led {st['led']}".encode(), ("127.0.0.1", CONTROL_PORT))

    def tick():
        now = time.monotonic()
        if st["release_at"] and now > st["release_at"]:
            st["held"], st["release_at"] = False, None
            ctrl.sendto(b"clench 0", ("127.0.0.1", CONTROL_PORT))
        if st["held"]:
            ctrl.sendto(b"clench 1", ("127.0.0.1", CONTROL_PORT))

        # g.Pype filtered EEG
        new = []
        while True:
            try:
                payload, _ = view.recvfrom(65535)
            except (BlockingIOError, ConnectionResetError):
                break
            if len(payload) >= 64 and len(payload) % 8 == 0:
                new.append(np.frombuffer(payload, dtype=np.float64)[:8])
        if new:
            new = np.array(new)[-n_buf:]
            buf[:-len(new)] = buf[len(new):]
            buf[-len(new):] = new
            st["n"] += len(new)
        for i, ln in enumerate(lines):
            ln.set_ydata(np.clip(buf[:, SHOW[i]], -spacing * 0.6, spacing * 0.6) + (nl - 1 - i) * spacing)

        # g.Pype FFT spectrum
        last = None
        while True:
            try:
                payload, _ = spec.recvfrom(65535)
                last = payload
            except (BlockingIOError, ConnectionResetError):
                break
        if last is not None and len(last) % 8 == 0:
            s = np.frombuffer(last, dtype=np.float64)
            if s.size % 257 == 0:
                s = s.reshape(257, -1)
                occ = s[:, [c for c in (5, 6, 7) if c < s.shape[1]]].mean(1)[keep]
                sm = st.get("spec")
                sm = occ if sm is None else 0.6 * sm + 0.4 * occ      # light smoothing for display
                st["spec"] = sm
                sp_line.set_ydata(sm)
                ax3.set_ylim(0, max(float(sm.max()) * 1.2, 1e-3))

        # SSVEP detector -> friend's trigger rules (hold 2 updates, re-arm, cooldown)
        n_win = int(WIN_S * FS)
        if st["n"] >= n_win and now - st["last_det"] >= 0.25:
            st["last_det"] = now
            r = cca_scores(buf[-n_win:])
            score = r[target] - max(v for f, v in r.items() if f != target)
            st["score"] = score
            score_hist.append((now, score))
            trig.last_jaw = score
            ev = trig._jaw_step(score)
            if ev and trig._cooldown_ok():
                marks.append((now, score))
                fire(f"SSVEP {target} Hz")

        if score_hist:
            ts = np.array([t for t, _ in score_hist]) - now
            vs = np.array([v for _, v in score_hist])
            sc_line.set_data(ts, vs)
            sc_hot.set_data(ts, np.where(vs > trig.jaw_on, vs, np.nan))
        if marks:
            mk.set_data([t - now for t, _ in marks], [v for _, v in marks])

        g = st["grip"]
        grip_txt.set_text(f"GRIPPER: {g}")
        grip_txt.set_color("#fde047" if now < st["flash_until"] else
                           ("#4ade80" if g == "OPEN" else "#f87171" if g == "CLOSED" else "white"))
        looking = st["held"]
        play_txt.set_text(f"Now playing: recorded trials, looking at the {st['led']} Hz LED" if looking
                          else "Now playing: recorded break, looking at nothing")
        play_txt.set_color("#fde047" if looking else "#9ca3af")
        if proc is not None and proc.poll() is not None:
            line = "!! The g.Pype pipeline stopped - look at the black console window for the error."
        elif st["n"] == 0:
            line = "Waiting for data from g.Pype..." + ("" if now - t_start < 15 else "  (still nothing - see the console)")
        elif st["n"] < n_win:
            line = "Filling the 3 s detector window..."
        else:
            line = (f"score {st['score']:+.3f}   threshold {trig.jaw_on:.3f}   "
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
