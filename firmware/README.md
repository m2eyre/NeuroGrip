# Firmware

| Sketch | Board | What it does |
|---|---|---|
| `NeuroGrip/` | The gripper's Arduino (we used a Nano R4) | Servo on D9, pushbutton on D2, text commands over USB serial at 115200 baud, calibration in EEPROM |
| `GripTest/` | Arduino UNO Q (or any Arduino) | Quick servo test with no laptop software: type `o`, `c`, `t` or an angle in the Serial Monitor at 9600 baud. Detaches the servo when idle so it doesn't jitter |
| `AnalogStreamer/` | Optional second Arduino | Streams `analogRead` values (MyoWare EMG or any analog sensor) to `software/sources/serial_analog_source.py` |

Open the `.ino` in Arduino IDE 2.x, pick your board and port, and upload. Full steps and the command list: [docs/software-setup.md](../docs/software-setup.md). Servo calibration: [docs/calibration.md](../docs/calibration.md).
