/*
  AnalogStreamer: send analog readings to the NeuroGrip bridge over USB serial.

  Use it on a SECOND board (any Arduino) for an EMG sensor such as the
  MyoWare 2.0, a force sensor, a potentiometer, or anything else analog.
  Pair it with software/sources/serial_analog_source.py.

  Wiring (MyoWare 2.0):  ENV -> A0,  + -> 5V (or 3.3V on 3.3 V boards),  - -> GND
  Electrodes: two on the muscle belly (e.g. forearm flexors or the jaw/temple
  for a clench), reference on a bony spot. Follow the MyoWare guide.

  Output: one line per sample, comma-separated if NUM_CH > 1, e.g. "512\n".
*/

const uint8_t  PINS[]    = { A0 };   // add A1, A2 ... for more channels
const uint8_t  NUM_CH    = sizeof(PINS) / sizeof(PINS[0]);
const uint16_t SAMPLE_HZ = 200;      // must match NG_ANALOG_FS / FS in the Python source

unsigned long nextUs;

void setup() {
  Serial.begin(115200);
  nextUs = micros();
}

void loop() {
  if ((long)(micros() - nextUs) < 0) return;
  nextUs += 1000000UL / SAMPLE_HZ;
  for (uint8_t i = 0; i < NUM_CH; i++) {
    if (i) Serial.print(',');
    Serial.print(analogRead(PINS[i]));
  }
  Serial.println();
}
