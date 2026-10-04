#ifndef BME280_SENSOR_H
#define BME280_SENSOR_H

#include "Sensor.h"
#include <Adafruit_BME280.h>

class BME280Sensor : public I2CSensor {
public:
    BME280Sensor(uint8_t address)
        : I2CSensor(address), _temperature(0.0), _humidity(0.0), _pressure(0.0) {}

    bool begin() override {
        uint8_t id = readChipId();
        Serial.printf("Env sensor chip ID: 0x%02X\n", id);
        if (id == 0) {
            Serial.println("BME280: no I2C response (wiring? try 0x77)");
            return false;
        }
        if (id != 0x60) {
            Serial.println("Not a BME280. An ID of 0x58 means it's a BMP280 (no humidity).");
            return false;
        }
        if (!_bme.begin(_address)) {
            Serial.println("BME280: library init failed");
            return false;
        }
        // Datasheet "weather monitoring" profile: forced mode, 1x oversampling,
        // no filter. It gives minimal self-heating, ample for 10 s readings.
        _bme.setSampling(Adafruit_BME280::MODE_FORCED,
                         Adafruit_BME280::SAMPLING_X1,   // temperature
                         Adafruit_BME280::SAMPLING_X1,   // pressure
                         Adafruit_BME280::SAMPLING_X1,   // humidity
                         Adafruit_BME280::FILTER_OFF);
        Serial.println("BME280 successfully started");
        return true;
    }

    bool read() override {
        if (!_bme.takeForcedMeasurement()) return false;
        float t = _bme.readTemperature();
        float h = _bme.readHumidity();
        float p = _bme.readPressure();           // Pa
        if (isnan(t) || isnan(h) || isnan(p)) return false;
        _temperature = t;
        _humidity = h;
        _pressure = p / 100.0;                   // store as hPa
        return true;
    }

    float getTemperature() { return _temperature; }
    float getHumidity()    { return _humidity; }
    float getPressure()    { return _pressure; }

private:
    uint8_t readChipId() {
        Wire.beginTransmission(_address);
        Wire.write(0xD0);                        // chip-ID register
        if (Wire.endTransmission() != 0) return 0;
        if (Wire.requestFrom(_address, (uint8_t)1) != 1) return 0;
        return Wire.read();
    }

    Adafruit_BME280 _bme;
    float _temperature, _humidity, _pressure;
};

#endif