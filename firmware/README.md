# Firmware

| Sketch | Board | What it does |
|---|---|---|
| `NeuroGrip/` | The gripper's Arduino (we used a Nano R4) | Servo on D9, pushbutton on D2, text commands over USB serial at 115200 baud, calibration in EEPROM |
| `AnalogStreamer/` | Optional second Arduino | Streams `analogRead` values (MyoWare EMG or any analog sensor) to `software/sources/serial_analog_source.py` |

Open the `.ino` in Arduino IDE 2.x, pick your board and port, and upload. Full steps and the command list: [docs/software-setup.md](../docs/software-setup.md). Servo calibration: [docs/calibration.md](../docs/calibration.md).
