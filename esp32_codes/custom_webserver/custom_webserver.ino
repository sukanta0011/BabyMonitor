#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <ESPmDNS.h>

// const char *ssid = "ufch";
// const char *password = "0090271BEB73";

const char* ssid = "moto g54 5G";
const char* password = "sukanta00";
const char* mdnsName = "esp32_cam1";

AsyncWebServer server(80);
String output;
JsonDocument doc;
SemaphoreHandle_t mutex;

typedef struct s_sensor
{
  float temperature;
  int   co2;
}       t_sensor;

t_sensor sensors;


int connect_to_wifi() {
  int max_try = 20;

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED && max_try > 0) {
    delay(1000);
    max_try -= 1;
    Serial.println("WiFi connection unsuccessful, retrying...");
  }
  if(max_try == 0)
    return (0);
  Serial.println(WiFi.localIP());
  return (1);
}

void start_mdns()
{
  if (!MDNS.begin(mdnsName)) {
    Serial.println("Error setting up MDNS responder!");
    while(1) {
      delay(1000);
    }
  }
  MDNS.addService("http", "tcp", 80);
  Serial.println("mDNS responder started. Access your ESP32 at http://" + String(mdnsName) + ".local");
}

void  update_sensor_data()
{
  xSemaphoreTake(mutex, portMAX_DELAY);
  doc["temperature"] = sensors.temperature;
  doc["co2"] = sensors.co2;
  serializeJson(doc, output);
  xSemaphoreGive(mutex);
}

int get_data_from_temperatue_sensor()
{
  sensors.temperature = random(100, 300) / 10.0;
  return (1);
}

int get_data_from_co2_sensor()
{
  sensors.co2 = random(500, 800) ;
  return (1);
}


void setup() {
  Serial.begin(115200);
  mutex = xSemaphoreCreateMutex();

  if(connect_to_wifi()){
    doc["temperature"] = 0.0;
    doc["co2"] = 0;
    serializeJson(doc, output);

    start_mdns();

    server.on("/sensors", HTTP_GET, [](AsyncWebServerRequest *request){
      Serial.println("Request received!");
      xSemaphoreTake(mutex, portMAX_DELAY);
      request->send(200, "application/json", output);
      xSemaphoreGive(mutex);
    });
    server.begin();
    Serial.println("Server started.");
  }
}

void loop() {
  get_data_from_temperatue_sensor();
  get_data_from_co2_sensor();
  update_sensor_data();
  Serial.printf("temperature: %f, CO2: %d\n", sensors.temperature, sensors.co2);
  delay(5000);
}
