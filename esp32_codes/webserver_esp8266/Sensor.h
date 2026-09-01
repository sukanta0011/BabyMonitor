#ifndef SENSOR_H
#define SENSOR_H

#include <Wire.h>

// Abstract base class
class Sensor {
public:
    virtual bool begin() = 0;
    virtual bool read() = 0;
};

// Intermediate I2C class
class I2CSensor : public Sensor {
public:
    I2CSensor(uint8_t address)
        : _address(address) {}

protected:
    uint8_t _address;
};

// BH1750 light sensor
class BH1750 : public I2CSensor {
public:
    BH1750(uint8_t address)
        : I2CSensor(address), _lux(0.0) {}

    bool begin() override {
        int retries = 3;
        while (retries > 0) {
            Wire.beginTransmission(_address);
            if (Wire.endTransmission() == 0) break;
            retries--;
            delay(500);
        }
        if (retries == 0) {
            Serial.println("BH1750 not found");
            return false;
        }

        Wire.beginTransmission(_address);
        Wire.write(0x10); //0x10 start high resolution continuous reading
        Wire.endTransmission();
        delay(200);
        Serial.println("BH1750 successfully started");
        return true;
    }

    bool read() override {
        byte bytesReceived = Wire.requestFrom(_address, (uint8_t)2);
        if (bytesReceived != 2) return false;

        byte highByte = Wire.read();
        byte lowByte = Wire.read();
        _lux = ((highByte << 8) | lowByte) / 1.2;
        return true;
    }

    float getLux() { return _lux; }

private:
    float _lux;
};

// SCD40 CO2/temperature/humidity sensor
class SCD40 : public I2CSensor {
public:
    SCD40(uint8_t address)
        : I2CSensor(address), _co2(0), _temperature(0.0), _humidity(0.0) {}

    bool begin() override {
        int retries = 3;
        while (retries > 0) {
            Wire.beginTransmission(_address);
            if (Wire.endTransmission() == 0) break;
            retries--;
            delay(500);
        }
        if (retries == 0) {
            Serial.println("SCD40 not found");
            return false;
        }

        Wire.beginTransmission(_address);
        Wire.write(0x21); // MSB for reading initialization
        Wire.write(0xb1); // LSB for reading initialization
        Wire.endTransmission();
        delay(1000);
        Serial.println("SCD40 successfully started");
        return true;
    }

    bool read() override {
        Wire.beginTransmission(_address);
        Wire.write(0xec);
        Wire.write(0x05);
        Wire.endTransmission();
        delay(1);

        byte bytesReceived = Wire.requestFrom(_address, (uint8_t)9);
        if (bytesReceived != 9) return false;

        byte msb = Wire.read(); byte lsb = Wire.read(); Wire.read();
        _co2 = (msb << 8) | lsb;

        msb = Wire.read(); lsb = Wire.read(); Wire.read();
        _temperature = -45 + 175 * ((msb << 8) | lsb) / 65535.0;

        msb = Wire.read(); lsb = Wire.read(); Wire.read();
        _humidity = 100 * ((msb << 8) | lsb) / 65535.0;

        return true;
    }

    int getCO2()          { return _co2; }
    float getTemperature() { return _temperature; }
    float getHumidity()    { return _humidity; }

private:
    int _co2;
    float _temperature;
    float _humidity;
};

#endif