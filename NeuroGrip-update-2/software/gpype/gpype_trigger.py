"""
NeuroGrip - g.Pype trigger detector -> Arduino UNO Q
Listens to gpype_pipeline.py's UDP streams, detects a jaw clench or a double
blink, and sends 't' (toggle) to the proof-of-concept sketch at 9600 baud.

    pip install pyserial numpy
    python gpype_trigger.py --calibrate                 # guided 24 s calibration
    python gpype_trigger.py --dry-run --verbose         # watch detections, no board
    python gpype_trigger.py                             # live: auto-finds the board, uses calibration.json

The detector is the GPypeTrigger class, so it can also be wrapped as a
--source plugin for neurogrip_bridge.py.
"""
import argparse
import json
import pathlib
import select
import socket
import sys
import time

import numpy as np

FS = 250
CAL_FILE = pathlib.Path(__file__).with_name("calibration.json")


class GPypeTrigger:
    """Turns g.Pype's UDP feature streams into 'jaw' / 'double_blink' events."""

    def __init__(self, blink_port=56010, jaw_port=56011, blink_ch=0, jaw_ch=(1, 2),
                 blink_uv=120.0, jaw_on=40.0, jaw_off=15.0,
                 blink_max_s=0.5, double_gap=(0.1, 0.8), jaw_frames=2,
                 cooldown_s=1.0, enable_blink=True, enable_jaw=True):
        self.blink_ch, self.jaw_ch = blink_ch, list(jaw_ch)
        self.blink_uv, self.jaw_on, self.jaw_off = blink_uv, jaw_on, jaw_off
        self.blink_max_s, self.double_gap = blink_max_s, double_gap
        self.jaw_frames, self.cooldown_s = jaw_frames, cooldown_s
        self.enable_blink, self.enable_jaw = enable_blink, enable_jaw

        self.socks = {}
        for name, port in (("blink", blink_port), ("jaw", jaw_port)):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(("127.0.0.1", port))
            s.setblocking(False)
            self.socks[s] = name

        # live state
        self.n = 0                    # blink-stream sample counter (time base)
        self.in_blink, self.blink_start, self.last_blink_end = False, 0.0, None
        self.jaw_count, self.jaw_armed = 0, True
        self.last_trigger = -1e9
        self.last_fz, self.last_jaw = 0.0, 0.0
        self.raw = {"blink": [], "jaw": []}   # filled only when recording

    # -- packet decoding: UDPSender sends float64 arrays --------------------
    @staticmethod
    def _decode(payload):
        if len(payload) % 8:
            return None
        v = np.frombuffer(payload, dtype=np.float64)
        return v if v.size else None

    def poll(self, timeout=0.05, record=False):
        """Read pending packets. Returns a list of events ('jaw', 'double_blink')."""
        events = []
        ready, _, _ = select.select(list(self.socks), [], [], timeout)
        for s in ready:
            while True:
                try:
                    payload, _ = s.recvfrom(65535)
                except (BlockingIOError, ConnectionResetError):
                    break
                v = self._decode(payload)
                if v is None:
                    continue
                kind = self.socks[s]
                if kind == "blink":
                    fz = float(v[self.blink_ch])
                    self.last_fz = fz
                    if record:
                        self.raw["blink"].append(fz)
                    ev = self._blink_step(fz)
                else:
                    pw = float(max(v[i] for i in self.jaw_ch if i < v.size))
                    self.last_jaw = pw
                    if record:
                        self.raw["jaw"].append(pw)
                    ev = self._jaw_step(pw)
                if ev and self._cooldown_ok():
                    events.append(ev)
        return events

    def _cooldown_ok(self):
        now = time.monotonic()
        if now - self.last_trigger >= self.cooldown_s:
            self.last_trigger = now
            return True
        return False

    def _blink_step(self, fz):
        self.n += 1
        t = self.n / FS
        if not self.in_blink and fz > self.blink_uv:
            self.in_blink, self.blink_start = True, t
        elif self.in_blink and fz < 0.5 * self.blink_uv:
            self.in_blink = False
            if t - self.blink_start <= self.blink_max_s:        # a real blink is short
                prev, self.last_blink_end = self.last_blink_end, t
                if prev is not None and self.double_gap[0] <= t - prev <= self.double_gap[1]:
                    self.last_blink_end = None
                    return "double_blink" if self.enable_blink else None
        return None

    def _jaw_step(self, pw):
        if pw > self.jaw_on:
            self.jaw_count += 1
            if self.jaw_armed and self.jaw_count >= self.jaw_frames:
                self.jaw_armed = False
                return "jaw" if self.enable_jaw else None
        elif pw < self.jaw_off:
            self.jaw_count, self.jaw_armed = 0, True
        return None


def record_phase(trig, prompt, seconds):
    print(f"\n>>> {prompt}  ({seconds} s)")
    for i in (3, 2, 1):
        print(f"    starting in {i}...", end="\r")
        time.sleep(1)
    trig.raw = {"blink": [], "jaw": []}
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        trig.poll(0.05, record=True)
    b, j = np.array(trig.raw["blink"]), np.array(trig.raw["jaw"])
    if b.size < FS or j.size < 5:
        sys.exit("Not enough data received - is gpype_pipeline.py running?")
    return b, j


def calibrate(trig):
    print("Calibration: sit still, look straight ahead.")
    rb, rj = record_phase(trig, "RELAX - eyes open, jaw loose, blink normally", 8)
    _, cj = record_phase(trig, "CLENCH your jaw hard 3-4 times (1 s each)", 8)
    bb, _ = record_phase(trig, "BLINK hard 4-5 times, spaced out", 8)

    relax_jaw, clench_jaw = np.percentile(rj, 95), np.percentile(cj, 90)
    relax_fz, blink_fz = np.percentile(np.abs(rb), 99), np.percentile(bb, 99.5)

    jaw_on = relax_jaw + 0.35 * (clench_jaw - relax_jaw)
    jaw_off = relax_jaw + 0.10 * (clench_jaw - relax_jaw)
    blink_uv = relax_fz + 0.5 * (blink_fz - relax_fz)

    print("\nResults")
    print(f"  jaw power   relax p95 = {relax_jaw:10.2f}   clench p90 = {clench_jaw:10.2f}")
    print(f"  Fz (uV)     relax p99 = {relax_fz:10.2f}   blink peak = {blink_fz:10.2f}")
    if clench_jaw < 3 * relax_jaw:
        print("  ! Jaw clench barely stands out - check C3/C4 contact or try other --jaw-ch.")
    if blink_fz < 2 * relax_fz:
        print("  ! Blinks barely stand out - check Fz contact, or blinks may be negative on your montage.")
    if clench_jaw <= relax_jaw or blink_fz <= relax_fz:
        print("\nNo usable thresholds - fix the electrode contact and run --calibrate again.")
        return
    cal = {"blink_uv": round(float(blink_uv), 2), "jaw_on": round(float(jaw_on), 4),
           "jaw_off": round(float(jaw_off), 4)}
    CAL_FILE.write_text(json.dumps(cal, indent=2))
    print(f"\nSaved to {CAL_FILE.name}: {cal}")
    print("Live runs now use these automatically.")


def load_calibration():
    try:
        return json.loads(CAL_FILE.read_text())
    except (OSError, ValueError):
        return {}


def find_board_port():
    """Pick the Arduino's serial port automatically."""
    from serial.tools import list_ports
    ports = list(list_ports.comports())
    for p in ports:
        text = f"{p.description} {p.manufacturer or ''}".lower()
        if "arduino" in text or (p.vid == 0x2341):          # 0x2341 = Arduino USB vendor ID
            return p.device
    if len(ports) == 1:
        return ports[0].device
    listing = "\n  ".join(f"{p.device}: {p.description}" for p in ports) or "(none found)"
    sys.exit(f"Couldn't pick the board automatically. Ports:\n  {listing}\n"
             "Run again with --serial COMx")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serial", help="UNO Q port, e.g. COM5 or /dev/tty.usbmodemXXXX")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--cmd", default="t", help="command sent on trigger (t=toggle, c=close)")
    ap.add_argument("--dry-run", action="store_true", help="detect only, no serial")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--verbose", action="store_true", help="print live Fz / jaw values")
    ap.add_argument("--blink-ch", type=int, default=0)
    ap.add_argument("--jaw-ch", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--blink-uv", type=float, default=120.0)
    ap.add_argument("--jaw-on", type=float, default=40.0)
    ap.add_argument("--jaw-off", type=float, default=15.0)
    ap.add_argument("--cooldown", type=float, default=1.0)
    ap.add_argument("--no-blink", action="store_true")
    ap.add_argument("--no-jaw", action="store_true")
    ap.add_argument("--blink-port", type=int, default=56010)
    ap.add_argument("--jaw-port", type=int, default=56011)
    cal = load_calibration()
    ap.set_defaults(**cal)          # saved calibration; CLI flags still override
    a = ap.parse_args()
    if cal and not a.calibrate:
        print(f"Using {CAL_FILE.name}: {cal}")

    trig = GPypeTrigger(a.blink_port, a.jaw_port, a.blink_ch, a.jaw_ch, a.blink_uv,
                        a.jaw_on, a.jaw_off, cooldown_s=a.cooldown,
                        enable_blink=not a.no_blink, enable_jaw=not a.no_jaw)
    if a.calibrate:
        return calibrate(trig)

    ser = None
    if not a.dry_run:
        import serial  # pyserial
        port = a.serial or find_board_port()
        print(f"Opening board on {port} at {a.baud} baud")
        ser = serial.Serial(port, a.baud, timeout=0)
        time.sleep(2)  # board may reset when the port opens

    print("Listening for jaw clench / double blink... Ctrl+C to quit.")
    last_print = 0.0
    while True:
        for ev in trig.poll(0.05):
            print(f"[{time.strftime('%H:%M:%S')}] TRIGGER: {ev} -> '{a.cmd}'")
            if ser:
                ser.write((a.cmd + "\n").encode())
        if a.verbose and time.monotonic() - last_print > 0.5:
            last_print = time.monotonic()
            print(f"  Fz {trig.last_fz:8.1f} uV   jaw {trig.last_jaw:10.2f}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
