#include <HTTPClient.h>
#include <WiFi.h>

const char* ssid = "TP-Link_509A";
const char* password = "84710574";
HTTPClient  http;
WiFiClient* stream;
int httpCode;


int connect_to_wifi() {
  int max_try = 20;
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED && max_try > 0) {
    delay(1000);
    max_try -= 1;
    Serial.println("WiFi connection unsuccessful, retrying...");
  }
  if (max_try == 0) return 0;
  Serial.print("ip: 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' connected");
  return 1;
}

void  setup()
{
  Serial.begin(115200);
  if (connect_to_wifi())
  {
    http.begin("http://pi5.local:8000/video");
    httpCode = http.GET();
    if (httpCode == 200)
    {
      stream = http.getStreamPtr();
    }
    else
    {
      Serial.println("Unable to connect to Pi5");
    }
  }
}

void loop()
{
  int bytes = 0;
  while(stream->available() && bytes < 1000)
  {
    stream->read();
    bytes += 1;
  }
  Serial.println(bytes);
  delay(1000);

}