// NeuroGrip quick test sketch for Arduino UNO Q + SG90 (servo signal on D9)
// Serial Monitor at 9600 baud. Type o (open), c (close), t (toggle),
// or a number 0-180 for a raw angle, then press Enter.
// Anti-jitter: the servo is only driven while it moves, then detached,
// so it sits silent when idle.

#include <Servo.h>

const int SERVO_PIN    = 9;
const int OPEN_ANGLE   = 180;
const int CLOSED_ANGLE = 125;
const int SETTLE_MS    = 500;   // time to reach the target before detaching
const bool HOLD_WHEN_CLOSED = false;  // set true if the closed grip slips

Servo grip;
bool isClosed = false;

void moveTo(int deg) {
  deg = constrain(deg, 0, 180);
  grip.attach(SERVO_PIN);
  grip.write(deg);
  delay(SETTLE_MS);
  bool hold = HOLD_WHEN_CLOSED && deg == CLOSED_ANGLE;
  if (!hold) grip.detach();     // no pulses = no idle jitter
  Serial.print("Angle: ");
  Serial.println(deg);
}

void setup() {
  Serial.begin(9600);
  grip.write(OPEN_ANGLE);       // set the first pulse before attaching
  moveTo(OPEN_ANGLE);
  Serial.println("Ready: o = open, c = close, t = toggle, or type an angle");
}

void loop() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd == "o") { moveTo(OPEN_ANGLE); isClosed = false; }
  else if (cmd == "c") { moveTo(CLOSED_ANGLE); isClosed = true; }
  else if (cmd == "t") {
    isClosed = !isClosed;
    moveTo(isClosed ? CLOSED_ANGLE : OPEN_ANGLE);
  }
  else if (isDigit(cmd.charAt(0))) moveTo(cmd.toInt());
  else Serial.println("Unknown command. Use o, c, t or an angle 0-180.");
}
