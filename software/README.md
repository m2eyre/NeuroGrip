# Software: the signal-to-gripper bridge

`neurogrip_bridge.py` reads a signal, detects a jaw clench, double blink or level crossing, and sends `toggle` to the gripper's Arduino. It shows a live plot and has a guided calibration (press K).

```bash
pip install -r requirements.txt
python neurogrip_bridge.py --source sim --no-serial     # try it with no hardware (hold J)
python neurogrip_bridge.py --list                       # see serial ports and LSL streams
python neurogrip_bridge.py                              # g.tec Unicorn via LSL + the Nano
```

`sources/` holds input plug-ins (`--source sources/<file>.py`):

| File | Input |
|---|---|
| `template_source.py` | Start here to write your own |
| `keyboard_source.py` | Hold a key (G) as the "action" |
| `brainflow_source.py` | OpenBCI, Muse, Unicorn and other BrainFlow boards, or a synthetic board |
| `serial_analog_source.py` | MyoWare EMG or any analog sensor on a second Arduino |

Guides: [setup](../docs/software-setup.md) · [calibration](../docs/calibration.md) · [alternative inputs](../docs/alternative-inputs.md)
