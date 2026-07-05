#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <ESPmDNS.h>
#include "Sensor.h"

const char* ssid = "TP-Link_509A";
const char* password = "84710574";
const int SDA_PIN = 15;
const int SCL_PIN = 14;
const char* mdnsName = "esp32_cam1";

int light_sensor_on = 0;
int co2_sensor_on = 0;

AsyncWebServer server(80);
String output;
JsonDocument doc;
BH1750 light_sensor(0x23);
SCD40 co2_sensor(0x62);
SemaphoreHandle_t mutex;


int connect_to_wifi() {
  int max_try = 20;
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED && max_try > 0) {
    delay(1000);
    max_try -= 1;
    Serial.println("WiFi connection unsuccessful, retrying...");
  }
  if (max_try == 0) return 0;
  Serial.println(WiFi.localIP());
  return 1;
}


void start_mdns() {
  if (!MDNS.begin(mdnsName)) {
    Serial.println("Error setting up MDNS responder!");
    while(1) delay(1000);
  }
  MDNS.addService("http", "tcp", 80);
  Serial.println("mDNS started: http://" + String(mdnsName) + ".local");
}


void update_sensor_data() {
  xSemaphoreTake(mutex, portMAX_DELAY);

  // BH1750
  JsonObject bh = doc["bh1750"].to<JsonObject>();
  if (light_sensor_on) {
    bh["status"] = "on";
    bh["error"] = "";
    bh["lux"] = light_sensor.getLux();
  } else {
    bh["status"] = "off";
    bh["error"] = "BH1750 not responding";
    bh["lux"] = 0;
  }

  // SCD40
  JsonObject scd = doc["scd40"].to<JsonObject>();
  if (co2_sensor_on) {
    scd["status"] = "on";
    scd["error"] = "";
    scd["co2"] = co2_sensor.getCO2();
    scd["temperature"] = co2_sensor.getTemperature();
    scd["humidity"] = co2_sensor.getHumidity();
  } else {
    scd["status"] = "off";
    scd["error"] = "SCD40 not responding";
    scd["co2"] = 0;
    scd["temperature"] = 0;
    scd["humidity"] = 0;
  }

  serializeJson(doc, output);
  xSemaphoreGive(mutex);
}


void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);
  mutex = xSemaphoreCreateMutex();

  if (connect_to_wifi()) {
    light_sensor_on = light_sensor.begin();
    co2_sensor_on = co2_sensor.begin();
    update_sensor_data();
    start_mdns();

    server.on("/sensors", HTTP_GET, [](AsyncWebServerRequest *request){
      xSemaphoreTake(mutex, portMAX_DELAY);
      if (light_sensor_on && co2_sensor_on)
        request->send(200, "application/json", output);
      else if (!light_sensor_on && !co2_sensor_on)
        request->send(500, "application/json", output);
      else
        request->send(206, "application/json", output);
      xSemaphoreGive(mutex);
    });

    server.begin();
    Serial.println("Server started.");
  }
}


void loop() {
  delay(10000);
  // if (light_sensor_on)
    light_sensor_on = light_sensor.read();

  // if (co2_sensor_on)
    co2_sensor_on = co2_sensor.read();

  update_sensor_data();
}
