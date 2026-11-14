/*
  NeuroGrip gripper firmware  (Arduino Nano R4, SG90 servo)
  ---------------------------------------------------------
  - Listens on USB serial (115200 baud) for commands from neurogrip_bridge.py
  - Pushbutton on D2 toggles the grip (backup if the EEG side fails)
  - Moves the servo smoothly between a calibrated OPEN and CLOSED angle
  - After closing, backs off a couple of degrees so the SG90 is not stalled
  - Calibration is saved in EEPROM, so it survives power cycles

  Wiring (see GUIDE.md for the diagram):
    Servo signal (orange)  -> D9
    Servo +   (red)        -> + of the separate 5-6 V servo supply
    Servo -   (brown)      -> - of the servo supply AND a Nano GND pin
    Pushbutton             -> between D2 and GND (internal pull-up is used)
    470-1000 uF capacitor  -> across the servo supply, close to the servo

  Serial commands (type in Serial Monitor, "Newline" line ending):
    o / open        open the gripper
    c / close       close the gripper
    t / toggle      toggle open <-> closed
    s / status      print the current state
    a <deg>         jog the servo to a raw angle (calibration only)
    + / -           jog 1 degree up / down from the current angle
    setopen         store the CURRENT angle as the open angle
    setclosed       store the CURRENT angle as the closed angle
    setopen <deg>   / setclosed <deg>   store a specific angle
    relax <deg>     degrees to back off after closing (0 = hold hard)
    speed <ms>      milliseconds per degree while moving (1 = fastest)
    save            write calibration to EEPROM
    defaults        restore factory calibration (not saved until "save")
    help            print this list
*/

#include <Servo.h>
#include <EEPROM.h>

// ---------------- pins ----------------
const uint8_t SERVO_PIN  = 9;
const uint8_t BUTTON_PIN = 2;
const uint8_t LED_PIN    = LED_BUILTIN;

// ---------------- calibration ----------------
// Defaults match the CAD: assemble the horn with the servo at 90 deg and the
// jaws closed, then about 30 deg of travel opens the jaws to ~53 mm.
// If your gripper opens the other way, use OPEN 60 / CLOSED 90 instead.
struct Calibration {
  uint16_t magic;
  uint8_t  openDeg;
  uint8_t  closedDeg;
  uint8_t  relaxDeg;   // back-off after closing to avoid stalling the SG90
  uint8_t  msPerDeg;   // movement speed
};
const uint16_t CAL_MAGIC = 0x4E47;   // "NG"
const Calibration CAL_DEFAULT = { CAL_MAGIC, 120, 92, 2, 6 };
const uint8_t MAX_TRAVEL = 40;       // CAD limit is 35 deg; refuse anything wilder
Calibration cal;

// ---------------- state ----------------
Servo servo;
bool    isClosed      = false;
float   currentDeg    = 0;     // where the servo is now (float for smooth ramps)
int     targetDeg     = 0;     // where it is heading
int     afterArrival  = -1;    // relax target queued after a close finishes
unsigned long lastStepMs = 0;
unsigned long arrivedMs  = 0;

// button debounce
bool lastButtonReading = HIGH;
bool buttonState       = HIGH;
unsigned long buttonChangedMs = 0;
const unsigned long DEBOUNCE_MS = 30;

String line;

// ------------------------------------------------------------------
void loadCalibration() {
  EEPROM.get(0, cal);
  bool sane = cal.magic == CAL_MAGIC && cal.openDeg <= 180 && cal.closedDeg <= 180 &&
              abs((int)cal.openDeg - (int)cal.closedDeg) <= MAX_TRAVEL && cal.msPerDeg >= 1;
  if (!sane) cal = CAL_DEFAULT;
}

void saveCalibration() {
  cal.magic = CAL_MAGIC;
  EEPROM.put(0, cal);
  Serial.println(F("OK saved to EEPROM"));
}

void printStatus() {
  Serial.print(F("STATE "));
  Serial.print(isClosed ? F("CLOSED") : F("OPEN"));
  Serial.print(F(" angle="));   Serial.print((int)round(currentDeg));
  Serial.print(F(" open="));    Serial.print(cal.openDeg);
  Serial.print(F(" closed="));  Serial.print(cal.closedDeg);
  Serial.print(F(" relax="));   Serial.print(cal.relaxDeg);
  Serial.print(F(" speed="));   Serial.println(cal.msPerDeg);
}

void printHelp() {
  Serial.println(F("Commands: o|open  c|close  t|toggle  s|status  a <deg>  + -"));
  Serial.println(F("          setopen [deg]  setclosed [deg]  relax <deg>  speed <ms>"));
  Serial.println(F("          save  defaults  help"));
}

int clampDeg(int d) { return constrain(d, 0, 180); }

void moveTo(int deg) {
  targetDeg = clampDeg(deg);
  afterArrival = -1;
}

int relaxedClosedDeg() {
  // back off from the closed angle towards the open angle
  int dir = (cal.openDeg > cal.closedDeg) ? 1 : -1;
  return clampDeg(cal.closedDeg + dir * cal.relaxDeg);
}

void openGrip() {
  isClosed = false;
  moveTo(cal.openDeg);
  digitalWrite(LED_PIN, LOW);
  printStatus();
}

void closeGrip() {
  isClosed = true;
  moveTo(cal.closedDeg);
  if (cal.relaxDeg > 0) afterArrival = relaxedClosedDeg();
  digitalWrite(LED_PIN, HIGH);
  printStatus();
}

void toggleGrip() {
  if (isClosed) openGrip(); else closeGrip();
}

bool checkTravel(int openDeg, int closedDeg) {
  if (abs(openDeg - closedDeg) > MAX_TRAVEL) {
    Serial.print(F("ERR open and closed must be within "));
    Serial.print(MAX_TRAVEL);
    Serial.println(F(" deg of each other (CAD limit). Not changed."));
    return false;
  }
  return true;
}

// ------------------------------------------------------------------
void handleCommand(String cmd) {
  cmd.trim();
  cmd.toLowerCase();
  if (cmd.length() == 0) return;

  int space = cmd.indexOf(' ');
  String word = (space < 0) ? cmd : cmd.substring(0, space);
  String arg  = (space < 0) ? ""  : cmd.substring(space + 1);
  arg.trim();
  bool hasArg = arg.length() > 0;
  int  val    = arg.toInt();

  if (word == "o" || word == "open")        openGrip();
  else if (word == "c" || word == "close")  closeGrip();
  else if (word == "t" || word == "toggle") toggleGrip();
  else if (word == "s" || word == "status") printStatus();
  else if (word == "help" || word == "h" || word == "?") printHelp();
  else if (word == "a" || word == "angle") {
    if (!hasArg) { Serial.println(F("ERR usage: a <deg>")); return; }
    moveTo(val);
    Serial.print(F("OK jog to ")); Serial.println(targetDeg);
  }
  else if (word == "+") { moveTo(targetDeg + 1); Serial.print(F("OK jog to ")); Serial.println(targetDeg); }
  else if (word == "-") { moveTo(targetDeg - 1); Serial.print(F("OK jog to ")); Serial.println(targetDeg); }
  else if (word == "setopen") {
    int d = hasArg ? clampDeg(val) : targetDeg;
    if (checkTravel(d, cal.closedDeg)) { cal.openDeg = d; Serial.print(F("OK open=")); Serial.println(d); }
  }
  else if (word == "setclosed") {
    int d = hasArg ? clampDeg(val) : targetDeg;
    if (checkTravel(cal.openDeg, d)) { cal.closedDeg = d; Serial.print(F("OK closed=")); Serial.println(d); }
  }
  else if (word == "relax") {
    cal.relaxDeg = constrain(val, 0, 10);
    Serial.print(F("OK relax=")); Serial.println(cal.relaxDeg);
  }
  else if (word == "speed") {
    cal.msPerDeg = constrain(val, 1, 50);
    Serial.print(F("OK speed=")); Serial.println(cal.msPerDeg);
  }
  else if (word == "save")     saveCalibration();
  else if (word == "defaults") { cal = CAL_DEFAULT; Serial.println(F("OK defaults loaded (type save to keep)")); }
  else { Serial.print(F("ERR unknown command: ")); Serial.println(cmd); }
}

void readSerial() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (line.length()) handleCommand(line);
      line = "";
    } else if (line.length() < 40) {
      line += ch;
    }
  }
}

void readButton() {
  bool reading = digitalRead(BUTTON_PIN);
  if (reading != lastButtonReading) buttonChangedMs = millis();
  lastButtonReading = reading;
  if (millis() - buttonChangedMs > DEBOUNCE_MS && reading != buttonState) {
    buttonState = reading;
    if (buttonState == LOW) {          // pressed (pull-up, so pressed = LOW)
      Serial.println(F("EVENT button"));
      toggleGrip();
    }
  }
}

void updateServo() {
  unsigned long now = millis();
  if ((int)round(currentDeg) == targetDeg) {
    if (afterArrival >= 0 && now - arrivedMs > 300) {   // let it seat, then relax
      targetDeg = afterArrival;
      afterArrival = -1;
    }
    return;
  }
  if (now - lastStepMs < cal.msPerDeg) return;
  lastStepMs = now;
  currentDeg += (targetDeg > currentDeg) ? 1 : -1;
  servo.write((int)round(currentDeg));
  if ((int)round(currentDeg) == targetDeg) arrivedMs = now;
}

// ------------------------------------------------------------------
void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(115200);

  loadCalibration();
  currentDeg = cal.openDeg;
  targetDeg  = cal.openDeg;
  servo.attach(SERVO_PIN);        // default 544-2400 us pulse range
  servo.write(cal.openDeg);       // start open

  unsigned long t0 = millis();
  while (!Serial && millis() - t0 < 1500) { }   // give USB a moment, don't block forever
  Serial.println(F("NeuroGrip ready. Type help for commands."));
  printStatus();
}

void loop() {
  readSerial();
  readButton();
  updateServo();
}
