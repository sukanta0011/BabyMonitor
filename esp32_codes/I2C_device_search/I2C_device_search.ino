#include <Wire.h>

void setup() {
    Serial.begin(115200);
    Wire.begin(15, 14);
    delay(1000);
    Serial.println("Scanning I2C bus...\n");
    
    for (byte address = 1; address < 127; address++) {
        Wire.beginTransmission(address);
        byte error = Wire.endTransmission();
        if (error == 0) {
            Serial.print("Device found at 0x");
            Serial.println(address, HEX);
        }
    }
    Serial.println("Scan complete.\n");
}

void loop() {}