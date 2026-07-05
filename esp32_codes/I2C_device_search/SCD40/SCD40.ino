#include <Wire.h>

const int sda = 15;
const int scl = 14;
const byte SCD40 = 0x62;
const uint16_t PERIODIC_MEASUREMENT = 0x21b1;
const uint16_t READ_MEASUREMENT = 0xec05;

void setup() {
    Serial.begin(115200);
    Wire.begin(sda, scl);
    delay(1000);
    Wire.beginTransmission(SCD40);
    byte error = Wire.endTransmission();
    if (error == 0) {
        Serial.println("Device found at 0x62");
    }

    Wire.beginTransmission(SCD40);
    Wire.write((PERIODIC_MEASUREMENT >> 8) & 0xFF);
    Wire.write(PERIODIC_MEASUREMENT & 0xFF);
    Wire.endTransmission();
    delay(1000);
}

void loop() {
    Wire.beginTransmission(SCD40);
    Wire.write((READ_MEASUREMENT >> 8) & 0xFF);
    Wire.write(READ_MEASUREMENT & 0xFF);
    Wire.endTransmission();
    delay(1);

    byte bytesReceived = Wire.requestFrom(SCD40, 9);
    if (bytesReceived == 9) {
        byte msb = Wire.read();
        byte lsb = Wire.read();
        byte crc = Wire.read();
        int co2 = msb << 8 | lsb;
        Serial.print("CO2: ");
        Serial.print(co2);
        Serial.print(" ppm, ");

        msb = Wire.read();
        lsb = Wire.read();
        crc = Wire.read();
        float temp = -45 + 175 * (msb << 8 | lsb) / 65535.0;
        Serial.print("T: ");
        Serial.print(temp);
        Serial.print("C, ");

        msb = Wire.read();
        lsb = Wire.read();
        crc = Wire.read();
        float humidity = 100 * (msb << 8 | lsb) / 65535.0;
        Serial.print("H: ");
        Serial.println(humidity);
    }
    delay(5000);
}