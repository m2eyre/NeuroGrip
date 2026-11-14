"""Read numbers from a microcontroller over USB serial (EMG sensors, FSRs, pots...).

Made for the MyoWare 2.0 muscle sensor, but works with anything that can be
read with analogRead(). Flash firmware/AnalogStreamer/AnalogStreamer.ino onto
a SECOND board (not the one driving the servo), wire the sensor to A0, then:

    python neurogrip_bridge.py --source sources/serial_analog_source.py --mode level

Settings: edit the constants below, or set environment variables
NG_ANALOG_PORT / NG_ANALOG_FS.

The board sends one line per sample, e.g. "512\n" (one channel) or
"512,300\n" (two channels). Values are passed through unchanged, so in level
mode the threshold is in raw ADC counts (0-1023 on a 10-bit board, 0-16383 on
the Nano R4's 14-bit ADC if you raise its resolution).

Use the MyoWare ENV output with --mode level. If you wire the RAW output
instead (and stream at 500 Hz or more) you can try --mode clench, which
band-passes and RMS-es it like the EEG path.
"""
import os

import numpy as np

PORT = os.environ.get("NG_ANALOG_PORT")          # e.g. "COM7" or "/dev/ttyACM1"; None = ask
FS = float(os.environ.get("NG_ANALOG_FS", 200))  # must match SAMPLE_HZ in the sketch
BAUD = 115200


class SerialAnalogSource:
    def __init__(self, port, fs=FS):
        import serial

        self.ser = serial.Serial(port, BAUD, timeout=0)
        self.fs = fs
        self.buf = b""
        self.n_ch = self._detect_channels()
        self.labels = [f"A{i}" for i in range(self.n_ch)]
        print(f"Analog source on {port}: {self.n_ch} channel(s) at {fs:.0f} Hz")

    def _detect_channels(self):
        import time

        t0 = time.time()
        while time.time() - t0 < 3:
            line = self.ser.readline().decode(errors="ignore").strip()
            if line and all(p.strip().lstrip("-").isdigit() for p in line.split(",")):
                return len(line.split(","))
        raise SystemExit("No numbers arriving on the analog port. Is AnalogStreamer flashed?")

    def read(self):
        self.buf += self.ser.read(self.ser.in_waiting or 0)
        *lines, self.buf = self.buf.split(b"\n")
        rows = []
        for ln in lines:
            parts = ln.decode(errors="ignore").strip().split(",")
            if len(parts) == self.n_ch:
                try:
                    rows.append([float(p) for p in parts])
                except ValueError:
                    pass
        return np.asarray(rows, float) if rows else np.empty((0, self.n_ch))


def make_source(args):
    port = PORT
    if port is None:
        from serial.tools import list_ports

        ports = [p.device for p in list_ports.comports() if p.device != args.port]
        print("Serial ports:", ports)
        port = input("Port of the SENSOR board (not the gripper Nano): ").strip()
    return SerialAnalogSource(port)
