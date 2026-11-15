# g.Pype version: real g.tec data, headset or simulator → gripper

This folder runs NeuroGrip's signal chain in **g.Pype**, g.tec's Python BCI framework. One window shows the brain waves, the detector score against its threshold, and the gripper state. Triggers go to the UNO Q at 9600 baud (`firmware/GripTest`).

```bash
pip install -r requirements.txt            # Python 3.10-3.14 (on Windows: py -3.13 -m pip ...)
python neurogrip_live.py --muscle --no-board    # REAL g.tec recording: SPACE = replay a muscle burst
python neurogrip_live.py --dataset --no-board   # REAL g.tec SSVEP: hold SPACE = look at the 12 Hz LED
python neurogrip_live.py --sim --no-board       # synthetic headset: hold SPACE = jaw clench
python neurogrip_live.py --calibrate            # real Unicorn: 24 s guided calibration
python neurogrip_live.py                        # real Unicorn + gripper
```

Drop `--no-board` to drive the gripper. The board is found automatically, or you can name it with `--serial COM5`.

**Where the data comes from and what it shows:** [docs/gtec-data.md](../../docs/gtec-data.md).

## Keys

| Key | What it does |
|---|---|
| SPACE | `--muscle`: replay one real burst · `--dataset`: hold to replay the "looking at the LED" trials · `--sim`: hold = clench · headset: manual toggle |
| 1 / 2 / 3 / 4 | `--dataset`: which LED's trials SPACE plays (9 / 10 / 12 / 15 Hz) |
| B | `--sim`: blink (tap twice = double blink) |
| J / T, O, C | manual toggle, open, close |
| UP / DOWN | threshold |
| Q | quit |

## Files

| File | What it is |
|---|---|
| `neurogrip_live.py` | The window. Starts the g.Pype pipeline, runs the trigger logic and talks to the board |
| `gpype_pipeline.py` | The g.Pype pipeline: Unicorn / BCI Core-8, the replay source nodes, filters, FFT, BandPower, UDP out |
| `gpype_trigger.py` | Jaw-clench and double-blink trigger rules (threshold, hold, re-arm, cooldown). Also runs on its own |
| `dataset_replay.py` | Loads the g.tec `.mat` files, builds the replay tracks and finds the muscle bursts |
| `dataset_window.py` | The SSVEP window and CCA detector |
| `fake_eeg.py` | The synthetic headset for `--sim` |
| `simulate_gpype.py` | Looping test stream for `gpype_trigger.py --dry-run` |
| `data/` | Put the g.tec recordings here (see [data/README.md](data/README.md)) |

UDP ports (localhost): 56010 blink, 56011 jaw power, 56012 wide-band view, 56013 key control, 56014 spectrum.

g.Pype licence: free for educational use when run from source. It only supports g.tec amplifiers. Other headsets use `../neurogrip_bridge.py`.
