// Baud: 115200  8N1

#include <Arduino.h>

static const uint8_t OUT_PINS[8] = {30,31,32,33,34,35,36,37};
static const uint8_t IN_PINS[8]  = {22,23,24,25,26,27,28,29};

static volatile uint16_t g_pulse_ms = 5;   // pulses duration

//Helpers binary reading
int readU8Blocking() {
  while (Serial.available() < 1) { /* wait */ }
  return Serial.read() & 0xFF;
}

uint16_t readU16LEBlocking() {
  int lo = readU8Blocking();
  int hi = readU8Blocking();
  return (uint16_t)(lo | (hi << 8));
}

// === Output ===
void applyMaskHigh(uint8_t mask) {
  for (uint8_t i=0;i<8;i++) {
    if (mask & (1<<i)) digitalWrite(OUT_PINS[i], HIGH);
  }
}

void applyMaskLow(uint8_t mask) {
  for (uint8_t i=0;i<8;i++) {
    if (mask & (1<<i)) digitalWrite(OUT_PINS[i], LOW);
  }
}

void pulseMask(uint8_t mask, uint16_t width_ms) {
  for (uint8_t i=0;i<8;i++) {
    if (mask & (1<<i)) digitalWrite(OUT_PINS[i], HIGH);
  }
  delay(width_ms);
  for (uint8_t i=0;i<8;i++) {
    if (mask & (1<<i)) digitalWrite(OUT_PINS[i], LOW);
  }
}

// === Input ===
// 'invert' value to adapt depending on button polarity
uint8_t readButtons(bool invert=false) {
  uint8_t m = 0;
  for (uint8_t i=0;i<8;i++) {
    int v = digitalRead(IN_PINS[i]);
    if (invert) v = !v;
    if (v) m |= (1<<i);
  }
  return m;
}

void setup() {
  Serial.begin(115200);

  for (uint8_t i=0;i<8;i++) pinMode(OUT_PINS[i], OUTPUT);
  for (uint8_t i=0;i<8;i++) {
    pinMode(IN_PINS[i], INPUT_PULLUP); //most response boxes need pullup
  }

  // Every line to LOW when starting
  applyMaskLow(0xFF);
}

void loop() {
  if (Serial.available() < 1) return;
  int opcode = readU8Blocking();

  switch (opcode) {
    case 10: { // set_trigger_duration [u16 ms]
      uint16_t ms = readU16LEBlocking();
      g_pulse_ms = ms;
      break;
    }
    case 11: { // send_trigger_mask [u8 mask]
      uint8_t mask = (uint8_t)readU8Blocking();
      pulseMask(mask, g_pulse_ms);
      break;
    }
    case 12: { // send_trigger_on_line [u8 line 0..7]
      uint8_t line = (uint8_t)readU8Blocking();
      if (line < 8) pulseMask((uint8_t)(1<<line), g_pulse_ms);
      break;
    }
    case 13: { // set_high_mask [u8 mask]
      uint8_t mask = (uint8_t)readU8Blocking();
      applyMaskHigh(mask);
      break;
    }
    case 14: { // set_low_mask [u8 mask]
      uint8_t mask = (uint8_t)readU8Blocking();
      applyMaskLow(mask);
      break;
    }
    case 15: { // set_high_on_line [u8 line]
      uint8_t line = (uint8_t)readU8Blocking();
      if (line < 8) digitalWrite(OUT_PINS[line], HIGH);
      break;
    }
    case 16: { // set_low_on_line [u8 line]
      uint8_t line = (uint8_t)readU8Blocking();
      if (line < 8) digitalWrite(OUT_PINS[line], LOW);
      break;
    }
    case 20: { // get_response_button_mask -> write [u8 mask]
      // Become 'true' if input are active when LOW
      uint8_t mask = readButtons(/*invert=*/true);
      Serial.write(mask);
      break;
    }
    default:
      // opcode unknown: ignore
      break;
  }
}
