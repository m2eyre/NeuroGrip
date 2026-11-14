# Alternative inputs: using something other than the g.tec headset

NeuroGrip was built around a g.tec Unicorn, but the gripper doesn't care where the "close now" decision comes from. This guide shows every way to swap the input, from "change one command-line flag" to "write your own source".

| Input | Effort | How |
|---|---|---|
| [Any LSL stream](#any-lsl-stream) | None | `--stream NAME` |
| [OpenBCI Cyton / Ganglion](#openbci) | Low | OpenBCI GUI → LSL, or the BrainFlow plug-in |
| [Muse 2 / Muse S](#muse) | Low | `muselsl` / BlueMuse → LSL, or the BrainFlow plug-in |
| [Other BrainFlow boards](#brainflow-any-supported-board) | Low | `sources/brainflow_source.py` |
| [EMG (MyoWare 2.0)](#emg-myoware-20) | Medium | Second Arduino + `sources/serial_analog_source.py` |
| [Keyboard, button, foot pedal, accessibility switch](#keyboard-buttons-and-switches) | None | SPACE, the D2 pushbutton, or `sources/keyboard_source.py` |
| [Simulator](#simulator) | None | `--source sim` |
| [Your own program or classifier](#your-own-program-or-classifier) | Medium | Send serial commands, or publish an LSL stream |
| [Anything else](#writing-a-source-plug-in) | Medium | Write a plug-in from `sources/template_source.py` |

## How the bridge sees an input

Everything happens in [`software/neurogrip_bridge.py`](../software/neurogrip_bridge.py). The pieces you care about:

| Where | What it does |
|---|---|
| `class LSLSource` | Reads any LSL stream. Picks the stream named by `--stream`, or the first one of type EEG/Data or named `UN…`. Uses the first `--channels` channels (default 8) and reads channel names from the stream if it publishes them |
| `class SimSource` | Fake 8-channel EEG for testing (hold J = clench, B = blink) |
| `def load_source_plugin` | Loads any `.py` file passed to `--source` and calls its `make_source(args)` |
| `def run` → `if args.source == "sim" … elif "lsl" … else plug-in` | The one place the source is chosen |
| `class Detector` | Turns samples into a "feature" and decides when to trigger. Three modes, below |
| `class Gripper` | Sends `open` / `close` / `toggle` to the Nano. You never need to touch it to change the input |

A **source** is any object with four things:

```python
src.fs        # sample rate in Hz
src.n_ch      # number of channels
src.labels    # list of channel names (for the plot)
src.read()    # -> NumPy array (n_new_samples, n_ch) of everything since the last call; never blocks
```

Optionally `src.on_key(key, down)` receives key presses from the plot window.

### Pick a detection mode

| `--mode` | Use when your source gives… | What the detector does |
|---|---|---|
| `clench` (default) | Raw EEG or EMG in **microvolts**, sampled at ~200 Hz or faster | 50/60 Hz notch, 30–100 Hz band-pass on every channel, moving RMS. Triggers when it stays above the threshold for `hold_ms` |
| `blink` | Raw EEG with a **frontal** channel (Fz, AF7, Fp1…) | 0.5–8 Hz band-pass on `blink_channel`. Two peaks within 0.7 s trigger |
| `level` | A value that already means "how strong is the action": an EMG envelope, a pressure sensor, a key held down, a classifier's probability | No filtering. Averages the channels and triggers when the value stays above the threshold for `hold_ms`; it must drop below 70 % of the threshold before the next trigger |

Whatever the mode, press **K** to calibrate and **S** to save, exactly as in [calibration](calibration.md). In level mode the threshold is in your source's own units.

## Any LSL stream

[Lab Streaming Layer](https://labstreaminglayer.org/) is the common language of research biosignal devices. Dozens of devices and apps publish LSL streams (see the [LSL apps list](https://labstreaminglayer.readthedocs.io/info/supported_devices.html)). If yours does:

```bash
python neurogrip_bridge.py --list                              # find the stream's name
python neurogrip_bridge.py --stream "MyStreamName" --channels 4
```

Check the units. `clench` and `blink` assume microvolts. If your device streams volts, multiply in a tiny plug-in (or just calibrate: the threshold is learned from your data, so a consistent scale is all that matters, but the plot's ±50 µV view will look flat).

## OpenBCI

**Option 1, OpenBCI GUI → LSL (no code):**

1. Start a session in the OpenBCI GUI with your Cyton (8 ch, 250 Hz) or Ganglion (4 ch, 200 Hz).
2. Add the **Networking** widget, choose **LSL**, set Stream 1 to **TimeSeriesRaw** (or TimeSeriesFilt), and click **Start**.
3. Run:
   ```bash
   python neurogrip_bridge.py --list
   python neurogrip_bridge.py --stream obci_eeg1          # use the name --list shows
   ```
   For a Ganglion add `--channels 4`.

**Option 2, BrainFlow plug-in:** see [below](#brainflow-any-supported-board) with `NG_BF_BOARD=CYTON_BOARD` (or `GANGLION_BOARD`) and the dongle's serial port.

**Electrodes for a jaw clench:** any channel near the temples (T7/T8, F7/F8) picks it up strongly. For blinks, put one channel on Fp1 or Fp2 and set `blink_channel` to its index.

## Muse

The Muse 2 and Muse S have 4 EEG channels at 256 Hz: TP9, AF7, AF8, TP10. TP9 and TP10 sit behind the ears, right next to the jaw muscles, so jaw clenches show up very clearly.

**Option 1, LSL:**

- Mac / Linux: `pip install muselsl`, then `muselsl stream` (add `--name` or `--address` if you have several).
- Windows: [BlueMuse](https://github.com/kowalej/BlueMuse) streams to LSL.

```bash
python neurogrip_bridge.py --channels 4            # skip the 5th "Right AUX" channel
python neurogrip_bridge.py --channels 4 --mode blink
```

For blinks, set `"blink_channel": 1` (AF7) in `neurogrip_calibration.json`, because channel 0 (TP9) is behind the ear.

**Option 2, BrainFlow plug-in:** `NG_BF_BOARD=MUSE_2_BOARD` (or `MUSE_S_BOARD`). On some systems BrainFlow needs the Muse's BLE dongle or the `MUSE_2_BLED_BOARD` id. Check the BrainFlow board docs.

## BrainFlow (any supported board)

[BrainFlow](https://brainflow.org/) talks to many boards with one API: OpenBCI, Muse, Neurosity, g.tec Unicorn, BrainBit and more, plus a **synthetic board** for testing. The plug-in is [`software/sources/brainflow_source.py`](../software/sources/brainflow_source.py).

```bash
pip install brainflow
# test with the synthetic board (no hardware):
python neurogrip_bridge.py --source sources/brainflow_source.py --no-serial
```

Pick the board with environment variables:

```powershell
# Windows PowerShell
$env:NG_BF_BOARD="CYTON_BOARD"; $env:NG_BF_SERIAL="COM4"
python neurogrip_bridge.py --source sources/brainflow_source.py
```
```bash
# Mac / Linux
NG_BF_BOARD=MUSE_2_BOARD python neurogrip_bridge.py --source sources/brainflow_source.py --channels 4
```

| Variable | Meaning |
|---|---|
| `NG_BF_BOARD` | A name from BrainFlow's `BoardIds`, e.g. `SYNTHETIC_BOARD`, `CYTON_BOARD`, `GANGLION_BOARD`, `MUSE_2_BOARD`, `MUSE_S_BOARD`, `UNICORN_BOARD` |
| `NG_BF_SERIAL` | Serial port, for boards with a USB dongle |
| `NG_BF_MAC` | MAC address, for some Bluetooth boards |

BrainFlow returns EEG in microvolts, so `clench` and `blink` work unchanged. Using `UNICORN_BOARD` is also a way to run the g.tec headset **without** Unicorn Suite's LSL app.

## EMG (MyoWare 2.0)

A surface-EMG sensor on a muscle is the most practical cheap input, and it is what most real myoelectric prostheses use. The [MyoWare 2.0](https://myoware.com/) gives an **ENV** output (already rectified and smoothed) and a **RAW** output.

**Hardware:** wire the sensor to a **second** Arduino (the first one is busy driving the servo) and flash [`firmware/AnalogStreamer/AnalogStreamer.ino`](../firmware/AnalogStreamer/AnalogStreamer.ino). It prints one `analogRead` value per line at 200 Hz.

| MyoWare 2.0 | Second Arduino |
|---|---|
| ENV | A0 |
| + | 5V (3.3V on 3.3 V boards) |
| − | GND |

Put the two snap electrodes along the belly of a muscle you can contract on purpose (forearm flexors, biceps, or the masseter/temple for a clench) and the reference on a bony spot, as in the MyoWare guide.

**Software:**

```bash
python neurogrip_bridge.py --source sources/serial_analog_source.py --mode level
```

It asks which port is the sensor board (or set `NG_ANALOG_PORT=COM7` first). Press **K**, relax, then contract and hold. The threshold is in raw ADC counts.

- Using the **RAW** output instead? Raise `SAMPLE_HZ` to 500 in the sketch and `NG_ANALOG_FS=500`, then try `--mode clench`, which band-passes and RMS-es it like the EEG. The values are ADC counts rather than µV, so ignore the unit on the plot.
- The same sketch and plug-in work for **any analog sensor**: a force-sensitive resistor squeezed by the other hand, a flex sensor, a sip/puff pressure sensor, a potentiometer.

**Going laptop-free (contributions welcome):** for a wearable device you'd read the MyoWare ENV pin directly on the gripper's own Nano and threshold it there. In `firmware/NeuroGrip/NeuroGrip.ino`, that means an `analogRead(A0)` in `loop()`, a smoothed value, a threshold with a hold time and a re-arm level (the same logic as `Detector` in the bridge), calling `toggleGrip()`, and an extra `emgthr` serial command saved in the `Calibration` struct. This isn't written yet.

## Keyboard, buttons and switches

No sensor needed, and useful as accessibility inputs in their own right.

- **SPACE** in the plot window toggles the gripper in every mode. **O** / **C** force open / close.
- **The pushbutton on D2** toggles the gripper with no laptop at all. Any momentary switch between D2 and GND works the same way, including **assistive-technology switches with a 3.5 mm jack** (button switches, sip-and-puff switches, head switches): wire the jack's tip to D2 and its sleeve to GND.
- **Hold-to-act key:** [`sources/keyboard_source.py`](../software/sources/keyboard_source.py) turns holding **G** into a level signal, so `hold_ms` and `refractory_ms` apply like a real sensor:
  ```bash
  python neurogrip_bridge.py --source sources/keyboard_source.py --mode level --threshold 0.5
  ```
  Many USB foot pedals and big-button switches show up as a keyboard key. Change `KEY` at the top of the file to match.

## Simulator

```bash
python neurogrip_bridge.py --source sim --no-serial          # hold J = clench, B = blink
python neurogrip_bridge.py --source sim --mode blink --no-serial
```

Drop `--no-serial` to drive the real gripper from the simulator.

## Your own program or classifier

**Skip the bridge:** the Nano accepts plain-text commands at 115200 baud, so any language can drive it:

```python
import serial, time
nano = serial.Serial("COM5", 115200, timeout=0.1)   # or /dev/ttyACM0
time.sleep(1.5)                                     # the board resets when the port opens
nano.write(b"toggle\n")                             # or b"open\n" / b"close\n"
```

Commands: `open`, `close`, `toggle`, `status` (full list in [software setup](software-setup.md#serial-commands)).

**Keep the bridge's plot, calibration and debouncing:** publish your decision as a 1-channel LSL stream (for example the probability that the user wants to grip, from a motor-imagery or P300 classifier), then use level mode:

```python
from pylsl import StreamInfo, StreamOutlet
outlet = StreamOutlet(StreamInfo("MyIntent", "Control", 1, 50, "float32", "myintent1"))
while True:
    p = my_classifier()          # 0..1
    outlet.push_sample([p])
```

```bash
python neurogrip_bridge.py --stream MyIntent --mode level --threshold 0.7
```

## Writing a source plug-in

1. Copy [`software/sources/template_source.py`](../software/sources/template_source.py) to `software/sources/my_source.py`.
2. In `__init__`, open your device and set `fs`, `n_ch` and `labels`.
3. In `read()`, return every sample that arrived since the last call as an array of shape `(n_samples, n_ch)`, or `np.empty((0, n_ch))` when there's nothing new. Don't block or sleep: the plot calls `read()` 25 times a second.
4. Keep `make_source(args)` returning your object. `args` has every command-line option (`args.channels`, `args.port`…), so you can reuse them.
5. Run it: `python neurogrip_bridge.py --source sources/my_source.py --mode level` (or `clench` for raw µV signals).

If it's useful to others, open a pull request and add a row to the table at the top of this page.
