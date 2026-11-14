# Wiring

![Wiring diagram](images/wiring_diagram.png)

| From | To | Why |
|---|---|---|
| Servo orange (signal) | Nano **D9** | Control pulses |
| Servo red (+) | **+** of the servo battery | The servo gets its own power |
| Servo brown (−) | **−** of the servo battery **and** a Nano **GND** pin | Common ground. Without this the servo twitches or does nothing |
| 470–1000 µF capacitor | Across servo + and −, close to the servo | Absorbs current spikes so the Nano doesn't reset. The stripe on the can marks the − leg |
| Pushbutton | One leg to **D2**, the other to **GND** | Backup trigger. No resistor needed (the internal pull-up is used) |
| Nano USB | Laptop | Powers the Nano and carries the commands |

## Servo power

- Use **4× AA NiMH** cells (4.8 V) or a **5 V USB power bank** (cut a spare USB cable and use the red and black wires).
- **Don't** power the servo from the Nano's 5V pin. A stalled SG90 can pull more current than the USB port and the Nano's regulator like, and the board will brown out and reset.
- **Don't** use 4× alkaline AAs. Fresh ones give 6 V or more, which is above the SG90's rating.

## Pins at a glance

| Pin | Use | Change it in |
|---|---|---|
| D9 | Servo signal | `SERVO_PIN` in `firmware/NeuroGrip/NeuroGrip.ino` |
| D2 | Pushbutton to GND | `BUTTON_PIN` |
| Built-in LED | On while the gripper is closed | `LED_PIN` |

## Optional: EMG sensor on a second board

To use a MyoWare 2.0 muscle sensor instead of (or as well as) the EEG headset, wire it to a **second** Arduino and flash [`firmware/AnalogStreamer`](../firmware/AnalogStreamer/AnalogStreamer.ino):

| MyoWare 2.0 | Second Arduino |
|---|---|
| ENV | A0 |
| + | 5V (or 3.3V on a 3.3 V board) |
| − | GND |

Both boards plug into the laptop over USB. See [alternative inputs](alternative-inputs.md#emg-myoware-20).

Next: [software setup](software-setup.md).
