#include <ArduinoJson.h>
#include <ESP8266WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ESP8266mDNS.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include "Sensor.h"

// --- Wi-Fi Credentials ---
const char* ssid = "TP-Link_509A";
const char* password = "84710574";
const char* mdnsName = "esp8266_sensor1";

// --- Pin Setup ---
const int SDA_PIN = 4; // GPIO 4 (D2)
const int SCL_PIN = 5; // GPIO 5 (D1)

#define TFT_CS   15    // GPIO 15 (D8)
#define TFT_DC   0     // GPIO 0  (D3)
#define TFT_RST  2     // GPIO 2  (D4)

// --- Colors (RGB565) ---
#define COLOR_BG        ST7735_BLACK
#define COLOR_GRID      0x39E7         // Slate Gray
#define COLOR_LABEL     ST7735_CYAN
#define COLOR_VAL_CO2   ST7735_YELLOW
#define COLOR_VAL_TEMP  ST7735_RED
#define COLOR_VAL_HUM   ST7735_GREEN
#define COLOR_VAL_LUX   ST7735_WHITE
#define COLOR_OUTDOOR   0xFD00         // Orange / Amber

// --- Peripherals & Globals ---
Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);
AsyncWebServer server(80);
BH1750 light_sensor(0x23);
SCD40 co2_sensor(0x62);

int light_sensor_on = 0;
int co2_sensor_on = 0;
String output;

// --- Outdoor Weather State ---
float lat = 50.08;
float lon = 14.43;
String city = "Prague";
float out_temp = 0.0;
float out_hum = 0.0;
bool weather_valid = false;

// --- Timing Control ---
unsigned long lastSensorUpdate = 0;
const unsigned long SENSOR_INTERVAL = 10000;     // 10 seconds refresh rate

unsigned long lastWeatherUpdate = 0;
const unsigned long WEATHER_INTERVAL = 600000;   // 10 minutes

// -------------------------------------------------------------
// WEATHER & LOCATION FETCHERS
// -------------------------------------------------------------
void fetchLocation() {
  WiFiClient client;
  HTTPClient http;

  if (http.begin(client, "http://ip-api.com/json/")) {
    int httpCode = http.GET();
    if (httpCode == HTTP_CODE_OK) {
      String payload = http.getString();
      JsonDocument doc;
      DeserializationError error = deserializeJson(doc, payload);

      if (!error && doc["status"] == "success") {
        lat = doc["lat"];
        lon = doc["lon"];
        city = doc["city"].as<String>();
      }
    }
    http.end();
  }
}

void fetchWeather() {
  WiFiClient client;
  HTTPClient http;

  String url = "http://api.open-meteo.com/v1/forecast?latitude=" + String(lat, 2) +
               "&longitude=" + String(lon, 2) +
               "&current=temperature_2m,relative_humidity_2m";

  if (http.begin(client, url)) {
    int httpCode = http.GET();
    if (httpCode == HTTP_CODE_OK) {
      String payload = http.getString();
      JsonDocument doc;
      DeserializationError error = deserializeJson(doc, payload);

      if (!error) {
        out_temp = doc["current"]["temperature_2m"];
        out_hum  = doc["current"]["relative_humidity_2m"];
        weather_valid = true;
      }
    }
    http.end();
  }
}

// -------------------------------------------------------------
// DISPLAY INTERFACE
// -------------------------------------------------------------
void drawStaticGrid() {
  tft.fillScreen(COLOR_BG);

  // Top section: 4 Indoor Quadrants (Y: 0 to 88)
  tft.drawFastHLine(0, 44, 160, COLOR_GRID); // Mid-horizontal divider
  tft.drawFastVLine(80, 0, 88, COLOR_GRID);  // Mid-vertical divider

  // Border separating indoor sensors from outdoor weather section
  tft.drawFastHLine(0, 88, 160, COLOR_LABEL);
  tft.drawFastHLine(0, 89, 160, COLOR_LABEL);

  tft.setTextSize(1);
  tft.setTextColor(COLOR_LABEL);

  // Quadrant 1: Top-Left
  tft.setCursor(6, 4);
  tft.print("CO2 (ppm)");

  // Quadrant 2: Top-Right
  tft.setCursor(86, 4);
  tft.print("IN TEMP (C)");

  // Quadrant 3: Mid-Left
  tft.setCursor(6, 48);
  tft.print("IN HUMID (%)");

  // Quadrant 4: Mid-Right
  tft.setCursor(86, 48);
  tft.print("LIGHT (lx)");
}

void updateGridValues(uint16_t co2, float temp, float hum, float lux) {
  tft.setTextSize(2);

  // 1. CO2
  tft.fillRect(6, 18, 70, 18, COLOR_BG);
  tft.setCursor(6, 18);
  tft.setTextColor(COLOR_VAL_CO2);
  if (co2_sensor_on) tft.print(co2);
  else tft.print("ERR");

  // 2. In Temperature
  tft.fillRect(86, 18, 70, 18, COLOR_BG);
  tft.setCursor(86, 18);
  tft.setTextColor(COLOR_VAL_TEMP);
  if (co2_sensor_on) tft.print(temp, 1);
  else tft.print("ERR");

  // 3. In Humidity
  tft.fillRect(6, 62, 70, 18, COLOR_BG);
  tft.setCursor(6, 62);
  tft.setTextColor(COLOR_VAL_HUM);
  if (co2_sensor_on) tft.print(hum, 1);
  else tft.print("ERR");

  // 4. In Lux
  tft.fillRect(86, 62, 70, 18, COLOR_BG);
  tft.setCursor(86, 62);
  tft.setTextColor(COLOR_VAL_LUX);
  if (light_sensor_on) tft.print((int)lux);
  else tft.print("ERR");
}

void updateWeatherSection() {
  // Clear bottom weather section (Y: 91 to 127)
  tft.fillRect(0, 91, 160, 37, COLOR_BG);

  // Header Line: City + IP Address
  tft.setTextSize(1);
  tft.setTextColor(COLOR_LABEL);
  tft.setCursor(6, 94);
  tft.print(city.substring(0, 7)); // e.g. "Prague"

  tft.setTextColor(ST7735_WHITE);
  tft.setCursor(55, 94);
  tft.print(WiFi.localIP().toString()); // Shows local IP (e.g. 192.168.1.120)

  if (weather_valid) {
    // Prominent Outdoor Temperature (Size 2)
    tft.setTextSize(2);
    tft.setTextColor(COLOR_OUTDOOR);
    tft.setCursor(6, 108);
    tft.printf("%4.1fC", out_temp);

    // Outdoor Humidity (Size 1)
    tft.setTextSize(1);
    tft.setTextColor(COLOR_VAL_HUM);
    tft.setCursor(102, 108);
    tft.print("HUMID:");

    tft.setTextColor(ST7735_WHITE);
    tft.setCursor(102, 118);
    tft.printf("%.0f %%", out_hum);
  } else {
    tft.setTextSize(1);
    tft.setTextColor(COLOR_GRID);
    tft.setCursor(6, 110);
    tft.print("Updating weather...");
  }
}

// -------------------------------------------------------------
// JSON & SENSOR STATE
// -------------------------------------------------------------
void update_sensor_data() {
  uint16_t co2 = 0;
  float temp = 0.0;
  float hum = 0.0;
  float lux = 0.0;

  if (co2_sensor_on) {
    co2 = co2_sensor.getCO2();
    temp = co2_sensor.getTemperature();
    hum = co2_sensor.getHumidity();
  }

  if (light_sensor_on) {
    lux = light_sensor.getLux();
  }

  updateGridValues(co2, temp, hum, lux);

  JsonDocument doc;
  
  JsonObject bh = doc["bh1750"].to<JsonObject>();
  bh["status"] = light_sensor_on ? "on" : "off";
  bh["lux"]    = lux;

  JsonObject scd = doc["scd40"].to<JsonObject>();
  scd["status"]      = co2_sensor_on ? "on" : "off";
  scd["co2"]         = co2;
  scd["temperature"] = temp;
  scd["humidity"]    = hum;

  JsonObject out = doc["outdoor"].to<JsonObject>();
  out["city"]        = city;
  out["temperature"] = out_temp;
  out["humidity"]    = out_hum;
  out["valid"]       = weather_valid;

  doc["ip"] = WiFi.localIP().toString();

  output = "";
  serializeJson(doc, output);
}

int connect_to_wifi() {
  int max_try = 20;
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED && max_try > 0) {
    delay(500);
    max_try -= 1;
    Serial.println("WiFi connecting...");
  }
  return WiFi.status() == WL_CONNECTED;
}

void start_mdns() {
  if (MDNS.begin(mdnsName)) {
    MDNS.addService("http", "tcp", 80);
    Serial.printf("mDNS ready: http://%s.local\n", mdnsName);
  }
}

// -------------------------------------------------------------
// SETUP & LOOP
// -------------------------------------------------------------
void setup() {
  Serial.begin(115200);

  // 1. Initialize LCD
  tft.initR(INITR_BLACKTAB);
  tft.setRotation(1); // Landscape 160x128
  tft.fillScreen(COLOR_BG);
  tft.setTextSize(1);
  tft.setTextColor(COLOR_LABEL);
  tft.setCursor(10, 10);
  tft.print("Booting node...");

  // 2. Start I2C bus
  Wire.begin(SDA_PIN, SCL_PIN);

  // 3. Connect Network
  if (connect_to_wifi()) {
    tft.setCursor(10, 25);
    tft.print("WiFi Connected");
    start_mdns();

    // 4. Fetch initial location & weather
    tft.setCursor(10, 40);
    tft.print("Fetching weather...");
    fetchLocation();
    fetchWeather();

    // 5. Initialize Sensor hardware
    light_sensor_on = light_sensor.begin();
    co2_sensor_on   = co2_sensor.begin();

    // 6. Draw Dashboard layout
    drawStaticGrid();
    updateWeatherSection();

    // Initial sensor sample & display push
    if (light_sensor_on) light_sensor.read();
    if (co2_sensor_on)   co2_sensor.read();
    update_sensor_data();

    // 7. Start Web Server
    server.on("/sensors", HTTP_GET, [](AsyncWebServerRequest *request) {
      request->send(200, "application/json", output);
    });

    server.begin();
    Serial.println("System operational.");
  } else {
    tft.setTextColor(COLOR_VAL_TEMP);
    tft.setCursor(10, 25);
    tft.print("WiFi Failed!");
  }
}

void loop() {
  unsigned long now = millis();

  // Polling loop 1: Local Sensors (Every 10 seconds)
  if (now - lastSensorUpdate >= SENSOR_INTERVAL) {
    lastSensorUpdate = now;

    light_sensor_on = light_sensor.read();
    co2_sensor_on   = co2_sensor.read();
    update_sensor_data();
  }

  // Polling loop 2: Outdoor Weather (Every 10 minutes)
  if (now - lastWeatherUpdate >= WEATHER_INTERVAL) {
    lastWeatherUpdate = now;

    fetchWeather();
    updateWeatherSection();
  }

  MDNS.update();
}