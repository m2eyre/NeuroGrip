# Software setup

This takes you from a blank laptop to a Nano that answers commands and a bridge that shows a live plot. Each part ends with a check so you know it worked before moving on.

```
Unicorn headset --Bluetooth--> Unicorn Suite (LSL app) --LSL--> neurogrip_bridge.py --USB--> Nano --> SG90 servo
                                                                        ^                       ^
                                                           SPACE key = backup trigger   pushbutton = backup trigger
```

**Operating system:** the g.tec Unicorn software runs on **Windows**. The Arduino and Python parts also work on Mac and Linux, so you can develop and test anywhere with `--source sim`. Other headsets (OpenBCI, Muse) work on all three, see [alternative inputs](alternative-inputs.md).

## 1. Get the code

Either download the ZIP from the GitHub page (**Code → Download ZIP**) and unzip it, or:

```bash
git clone https://github.com/m2eyre/neurogrip.git
```

## 2. Arduino IDE

1. Install **Arduino IDE 2.x** from https://www.arduino.cc/en/software with the default options. On Windows, say **Yes** to the USB drivers.
2. Open **Tools → Board → Boards Manager…**.
3. Install the core for your board:
   - **Arduino Nano R4** (what we used): search *Nano R4* and install the package it shows (the *Arduino UNO R4 Boards* package covers it).
   - **Classic Nano or a Nano clone:** *Arduino AVR Boards* is already installed. Clones often need the **CH340** USB driver.
4. `Servo` and `EEPROM` come with the board packages. Nothing else to install.

**Check:** **Tools → Board** lists your board.

## 3. Flash the Nano

1. **File → Open…** → `firmware/NeuroGrip/NeuroGrip.ino`. The folder and the `.ino` must keep the same name.
2. **Tools → Board** → your board (for example *Arduino UNO R4 Boards → Arduino Nano R4*, or *Arduino AVR Boards → Arduino Nano*).
3. Plug in the Nano. **Tools → Port** → the one that names your board (Windows `COM3`, `COM5`…; Mac `/dev/cu.usbmodem…`; Linux `/dev/ttyACM0`).
   - Classic Nano clones: if upload fails, try **Tools → Processor → ATmega328P (Old Bootloader)**.
4. Click **Upload** (→). Wait for *Done uploading*.
   - Nano R4: if the port vanishes or upload fails, **double-tap reset** to enter the bootloader, re-select the port and upload again.
5. **Tools → Serial Monitor**, set **Newline** and **115200 baud** at the bottom.

**Check:** the monitor prints `NeuroGrip ready.` and a `STATE OPEN …` line. Type `help` for the command list.

> Only one program can use the serial port at a time. **Close the Serial Monitor before running the Python bridge.**

### Serial commands

The Nano speaks plain text, one command per line, so you can drive it from the Serial Monitor, the bridge, or any program of your own.

| Command | Does |
|---|---|
| `o` / `open`, `c` / `close`, `t` / `toggle` | Move the gripper |
| `s` / `status` | Print `STATE OPEN angle=… open=… closed=… relax=… speed=…` |
| `a <deg>`, `+`, `-` | Jog the servo (calibration) |
| `setopen [deg]`, `setclosed [deg]` | Store the current (or given) angle |
| `relax <deg>` | Degrees to back off after closing (0–10, default 2) |
| `speed <ms>` | Milliseconds per degree while moving (1–50, default 6) |
| `save`, `defaults`, `help` | EEPROM save, factory reset (unsaved), list commands |

## 4. Python

1. Install **Python 3.11 or 3.12** from https://www.python.org/downloads/. On Windows, tick **"Add python.exe to PATH"** on the first screen.
2. Optional but nice: **VS Code** with Microsoft's **Python** extension.
3. Open a terminal in the `software` folder and create a virtual environment:

   **Windows (PowerShell)**
   ```powershell
   cd neurogrip\software
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
   If PowerShell says scripts are disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

   **Mac / Linux**
   ```bash
   cd neurogrip/software
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. In VS Code: **Ctrl+Shift+P → Python: Select Interpreter** → the one in `.venv`.

**Check (no hardware needed):**
```
python neurogrip_bridge.py --source sim --no-serial
```
A window with two plots opens. Click it, then **hold J**: the blue line jumps over the red dashed line, a ▼ appears and the terminal prints `TRIGGER`. Press **Q** to quit.

> On a Mac, if `pylsl` can't find `liblsl`, run `brew install labstreaminglayer/tap/lsl`. Sim mode doesn't need LSL.

## 5. Headset: Unicorn Suite and LSL

1. Install **Unicorn Suite Hybrid Black** (from the USB stick that comes with the headset, or g.tec's download page).
2. Turn the headset on, open Unicorn Suite and connect it from **Devices** (Bluetooth, through the supplied dongle).
3. In Unicorn Suite open **Apps** and install **Unicorn LSL**. It publishes the headset data as a Lab Streaming Layer stream.
4. Open Unicorn LSL, pick your headset, click **Open** and then **Start** (names vary slightly by version).

**Check:**
```
python neurogrip_bridge.py --list
```
You should see a stream under **LSL streams**, usually named like `UN-2023.xx.xx`, with 17 channels at 250 Hz. The first 8 are EEG (Fz, C3, Cz, C4, Pz, PO7, Oz, PO8). The rest (motion, battery, counter) are ignored.

## 6. Run it

```
python neurogrip_bridge.py
```

It finds the LSL stream and the Nano by itself. If it can't find the Nano, add `--port COM5` (or the port `--list` shows). Then go to [calibration](calibration.md).

### All command-line options

| Option | Default | What it does |
|---|---|---|
| `--source lsl` / `sim` / `path/to/plugin.py` | lsl | Where the signal comes from ([alternative inputs](alternative-inputs.md)) |
| `--stream NAME` | first EEG-like stream | Pick an LSL stream by exact name |
| `--channels N` | 8 | Use only the first N channels (4 for a Muse) |
| `--mode clench` / `blink` / `level` | clench | What to detect |
| `--threshold X` | from calibration | Force a threshold |
| `--hold-ms 150` | 150 | How long the signal must stay above the threshold |
| `--refractory-ms 1200` | 1200 | Dead time after a trigger |
| `--mains 60` | 60 | Power-line notch filter. 60 Hz in the Americas, 50 Hz in Europe and most of Asia |
| `--port COM5` | auto | Serial port of the Nano |
| `--baud 115200` | 115200 | Serial speed |
| `--no-serial` | off | Run without the Nano |
| `--list` | | List serial ports and LSL streams, then exit |

### Keys in the plot window

Click the plot first so it receives key presses.

| Key | Action |
|---|---|
| SPACE | Toggle the gripper (manual fallback) |
| O / C | Force open / close |
| K | Guided calibration |
| ↑ / ↓ | Threshold +10 % / −10 % |
| S | Save settings to `neurogrip_calibration.json` |
| J (hold) / B | Simulated clench / blink (sim source only) |
| Q / Esc | Quit |
