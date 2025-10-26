#include <Arduino.h>

const uint8_t RESP_PINS[8] = {22, 23, 24, 25, 26, 27, 28, 29}; // response lines -> mask bits 0..7
const uint8_t TRIGGER_PIN  = 30;       // TTL trigger output
const unsigned long PULSE_MS = 5;      // trigger pulse width (ms)

// Anti-double press: rearm only if mask==0 has remained stable for X ms
const unsigned long RELEASE_STABLE_MS = 20;

// Input polarity
// true  -> ACTIVE LOW (idle=HIGH, pressed=LOW) with INPUT_PULLUP
// false -> ACTIVE HIGH (idle=LOW,  pressed=HIGH) with INPUT
const bool ACTIVE_LOW = true;

bool armed = true;                      // ready to trigger?
unsigned long zero_since_ms = 0;        // timer for stability of mask==0

// ====== Helpers ======
inline void setup_inputs() {
  for (uint8_t i = 0; i < 8; ++i) {
    if (ACTIVE_LOW) pinMode(RESP_PINS[i], INPUT_PULLUP);
    else            pinMode(RESP_PINS[i], INPUT);
  }
}

inline uint8_t read_mask() {
  uint8_t m = 0;
  for (uint8_t b = 0; b < 8; ++b) {
    int v = digitalRead(RESP_PINS[b]);
    bool pressed = ACTIVE_LOW ? (v == LOW) : (v == HIGH);
    if (pressed) m |= (1u << b);
  }
  return m;
}

inline void fire_trigger() {
  digitalWrite(TRIGGER_PIN, HIGH);
  delay(PULSE_MS);
  digitalWrite(TRIGGER_PIN, LOW);
  Serial.println(F("Trigger sent"));
}

void setup() {
  Serial.begin(115200);
  setup_inputs();
  pinMode(TRIGGER_PIN, OUTPUT);
  digitalWrite(TRIGGER_PIN, LOW);

  Serial.println(F("Ready (one press -> one trigger)"));
  Serial.print(F("Polarity: ")); Serial.println(ACTIVE_LOW ? F("ACTIVE_LOW (INPUT_PULLUP)") : F("ACTIVE_HIGH (INPUT)"));
}

void loop() {
  // Read current state of the 8 input lines
  uint8_t mask = read_mask();

  if (armed) {
    // Like in Python: trigger as soon as mask != 0
    if (mask != 0) {
      fire_trigger();
      armed = false;            // disarm until stable release
      zero_since_ms = 0;        // will rearm once mask returns to 0
    }
  } else {
    // Not armed: wait for a stable release (mask==0 for RELEASE_STABLE_MS)
    if (mask == 0) {
      if (zero_since_ms == 0) {
        zero_since_ms = millis();        // start of stable 0 period
      } else if (millis() - zero_since_ms >= RELEASE_STABLE_MS) {
        armed = true;                    // rearmed: ready for next press
        // Serial.println(F("Re-armed"));
      }
    } else {
      // Reset timer if there’s movement (not yet properly released)
      zero_since_ms = 0;
    }
  }
}
