#include <Wire.h>

const int sda = 15;
const int scl = 14;
const byte BM1750 = 0x23;
const byte CONTINUOUS_H_RES_MODE = 0x10;


void setup() {
    Serial.begin(115200);
    Wire.begin(sda, scl);
    delay(1000);
    Wire.beginTransmission(BM1750);
    byte error = Wire.endTransmission();
    if (error == 0) {
        Serial.println("Device found at 0x23");
    }

    Wire.beginTransmission(BM1750);
    Wire.write(CONTINUOUS_H_RES_MODE);
    Wire.endTransmission();
    delay(1000);
}

void loop() {
    
    byte bytesReceived = Wire.requestFrom(BM1750, 2);
    if (bytesReceived == 2) {
        byte highByte = Wire.read(); // Read the first incoming byte
        byte lowByte = Wire.read();  // Read the second incoming byte
        
        // Combine bytes if dealing with 16-bit sensor data
        int value = (highByte << 8) | lowByte; 
        
        Serial.print("LUX: ");
        Serial.println(value / 1.2);
    }
    delay(5000);
}
