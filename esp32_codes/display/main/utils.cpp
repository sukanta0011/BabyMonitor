#include "utils.hpp"


int     connect_to_wifi()
{
    const char* ssid = "TP-Link_509A";
    const char* password = "84710574";

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


void    print_raw_bites(uint8_t *data, const uint32_t size)
{
    for (uint32_t i=0; i<size; i++)
    {
        Serial.print(char(data[i]));
    }
    Serial.println();
    Serial.println(size);
    for (uint32_t i=0; i<1000; i++)
    {
        Serial.print("-");
    }
    Serial.println();
}


void    display_gaps_between_frames(WiFiClient *stream)
{
    std::string marker = "--frame\r\n";
    std::string window = "";
    uint32_t bytes_read = 0;
    uint8_t val;
    uint32_t last_marker_at = 0;

    while (stream->available())
    {
        val = stream->read();
        if (val != -1)
        {
            bytes_read++;
            window += (char)val;
            if (window.size() > marker.size()) {
                window.erase(0, 1);  // keep only the last 9 bytes
            }
            if (window == marker) {
                Serial.print("Bytes since last full marker: ");
                Serial.println(bytes_read - last_marker_at);
                last_marker_at = bytes_read;
            }
        }
    }
}
