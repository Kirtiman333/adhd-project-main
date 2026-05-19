#include <Arduino.h>

const int btns[] = {2, 3, 4, 5}; 
const char* colorNames[] = {"RED", "GREEN", "BLUE", "YELLOW"};

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 4; i++) {
    pinMode(btns[i], INPUT_PULLUP);
  }
}

void loop() {
  for (int i = 0; i < 4; i++) {
    if (digitalRead(btns[i]) == LOW) {
      Serial.println(colorNames[i]);
      delay(300); 
      break; 
    }
  }
}