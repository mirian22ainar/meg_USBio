#include <Arduino.h>

const uint8_t RESP_PINS[8] = {22, 23, 24, 25, 26, 27, 28, 29}; // lignes de réponse -> mask bits 0..7
const uint8_t TRIGGER_PIN  = 30;       // sortie trigger TTL
const unsigned long PULSE_MS = 5;      // largeur du trigger (ms)

// Anti-doubles: on ne réarme que si mask==0 est resté stable X ms
const unsigned long RELEASE_STABLE_MS = 20;

// Polarité des entrées
// true  -> ACTIVE BAS (repos=HIGH, appui=LOW) avec INPUT_PULLUP
// false -> ACTIVE HAUT (repos=LOW,  appui=HIGH) avec INPUT
const bool ACTIVE_LOW = true;

bool armed = true;                      // prêt à déclencher ?
unsigned long zero_since_ms = 0;        // chrono stabilité du mask==0

// Helpers
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

  Serial.println(F("Ready (one-press -> one-trigger)"));
  Serial.print(F("Polarity: ")); Serial.println(ACTIVE_LOW ? F("ACTIVE_LOW (INPUT_PULLUP)") : F("ACTIVE_HIGH (INPUT)"));
}

void loop() {
  // Lire l'état courant des 8 lignes
  uint8_t mask = read_mask();

  if (armed) {
    // on déclenche dès le premier mask != 0
    if (mask != 0) {
      fire_trigger();
      armed = false;            // désarme jusqu'au relâchement stable
      zero_since_ms = 0;        // on repartira une fois revenu à 0
    }
  } else {
    // Non armé: on attend le relâchement stable (mask==0 pendant RELEASE_STABLE_MS)
    if (mask == 0) {
      if (zero_since_ms == 0) {
        zero_since_ms = millis();        // début de la stabilité à 0
      } else if (millis() - zero_since_ms >= RELEASE_STABLE_MS) {
        armed = true;                    // réarmé: prêt pour un nouvel appui
        // Serial.println(F("Re-armed"));
      }
    } else {
      // Repart à zéro si ça bouge (pas encore relâché proprement)
      zero_since_ms = 0;
    }
  }
}
