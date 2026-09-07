#include <string>
#include <algorithm>
#include <HTTPClient.h>
#include <WiFi.h>
#include <string>
#include <TJpg_Decoder.h>
#include <Arduino_GFX_Library.h>
#include "ringBuffer.hpp"


// Pin Definitions for ESP32-S3
#define TFT_MOSI 17
#define TFT_SCLK 18
#define TFT_CS    3
#define TFT_DC   15
#define TFT_RST  16

const char* ssid = "TP-Link_509A";
const char* password = "84710574";

HTTPClient  http;
WiFiClient* stream;
int httpCode;
Arduino_DataBus *bus = new Arduino_ESP32SPI(TFT_DC, TFT_CS, TFT_SCLK, TFT_MOSI, GFX_NOT_DEFINED);
Arduino_GFX *gfx = new Arduino_ILI9488_18bit(bus, TFT_RST, 1 /* rotation */, false /* IPS */);
const uint32_t                      buffer_size = 35000;
RingBuffer<uint8_t, buffer_size>    buffer;
uint8_t                             buffer_cpy[buffer_size];
uint32_t                            start = 0, end = 0;


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

// void read_from_stream(uint32_t max_read = buffer_size)
// {
//     uint32_t bytes_read = 0;
//     uint8_t temp[512];

//     while (stream->available() && bytes_read < max_read)
//     {
//         size_t n = stream->readBytes(temp, min((size_t)stream->available(), sizeof(temp)));
//         for (size_t i = 0; i < n; i++)
//         {
//             buffer.push(temp[i]);
//             bytes_read += 1;
//         }

//         // check for a complete frame after every chunk, not just once at the end
//         buffer.copy_data(buffer_cpy);
//         if (extract_frame(buffer_cpy, buffer_size, start, end))
//         {
//             decode_and_display(buffer_cpy + start, (end - start));
//         }
//     }
// }

void    read_from_stream(uint32_t max_read=buffer_size)
{
    uint32_t    bytes_read = 0;
    uint8_t     temp[512];
    // uint8_t     val;
    while (stream->available() && bytes_read < max_read)
    {
        size_t n = stream->readBytes(temp, min((size_t)stream->available(), sizeof(temp)));
        for (size_t i = 0; i < n; i++)
        {
            buffer.push(temp[i]);
            bytes_read += 1;
        }
        // val = stream->read();
        // if (val != -1) 
        // {
        //     buffer.push(val);
        //     bytes_read += 1;
        // }
    }
    // Serial.print("Buffer read: ");
    // Serial.println(bytes_read);
}

bool jpeg_output_callback(int16_t x, int16_t y, uint16_t w, uint16_t h, uint16_t* bitmap)
{
    gfx->draw16bitRGBBitmap(x, y, bitmap, w, h);
    return true;  // true = keep decoding, false = abort
}
// unsigned long draw_time_accumulator = 0;
// bool jpeg_output_callback(int16_t x, int16_t y, uint16_t w, uint16_t h, uint16_t* bitmap)
// {
//     unsigned long start = micros();
//     gfx->draw16bitRGBBitmap(x, y, bitmap, w, h);
//     draw_time_accumulator += micros() - start;
//     return true;
// }

void setup_decoder()
{
    TJpgDec.setJpgScale(2);  // decode at 1/2 scale
    TJpgDec.setCallback(jpeg_output_callback);
}

void decode_and_display(uint8_t *frame, uint32_t frame_size)
{
    // if (frame_size < 1000)
    // {
    TJpgDec.drawJpg(0, 0, frame, frame_size);
    // }
}

// void decode_and_display(uint8_t *frame, uint32_t frame_size)
// {
//     if (frame_size < 10000)
//     {
//         draw_time_accumulator = 0;
//         unsigned long t0 = micros();
//         TJpgDec.drawJpg(0, 0, frame, frame_size);
//         unsigned long total = micros() - t0;

//         Serial.print("total decode+draw: ");
//         Serial.print(total);
//         Serial.print("us | draw-only (sum of callback calls): ");
//         Serial.print(draw_time_accumulator);
//         Serial.print("us | decode-only (inferred): ");
//         Serial.println(total - draw_time_accumulator);
//     }
// }

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

void    display_gaps_between_frames()
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


bool    extract_frame(uint8_t *data, const uint32_t size, uint32_t &start, uint32_t &end)
{
    
    std::string marker = "--frame\r\n";
    // print_raw_bites(data, size);
    auto    it = std::search(data, data + size, marker.begin(), marker.end());
    if (it == (data + size)) {
        // Serial.println("boundaries found: 0");
        return false;
    }
    start = std::distance(data, it + marker.size());

    auto    end_it = std::search(it + marker.size(), data + size, marker.begin(), marker.end());
    if (end_it == data + size) {
        // Serial.println("boundaries found: 1");
        return false;
    }
    // Serial.println("boundaries found: 2 (or more)");
    end = std::distance(data, end_it);

    return true;
}


void setup()
{
    Serial.begin(115200);
    // buffer_cpy = buffer.get_data();


    if (connect_to_wifi())
    {
        http.begin("http://sukantapc.local:8000/video/cam2");
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
    if (!gfx->begin()) { Serial.println("gfx->begin() failed!"); }
    setup_decoder();
}

// void    loop()
// {
//     read_from_stream();
//     buffer.copy_data(buffer_cpy);
//     if (extract_frame(buffer_cpy, buffer_size, start, end))
//     {
//         Serial.print("frame size: ");
//         Serial.println(end - start);
//         decode_and_display(buffer_cpy + start, (end - start));
//     }
//     // display_gaps_between_frames();
//     delay(100);
// }


void    loop()
{
    unsigned long t0 = micros();
    read_from_stream();
    unsigned long t1 = micros();

    buffer.copy_data(buffer_cpy);
    unsigned long t2 = micros();

    bool found = extract_frame(buffer_cpy, buffer_size, start, end);
    unsigned long t3 = micros();

    if (found)
    {
        decode_and_display(buffer_cpy + start, (end - start));
    }
    unsigned long t4 = micros();

    Serial.print("read: ");
    Serial.print(t1 - t0);
    Serial.print("us | copy: ");
    Serial.print(t2 - t1);
    Serial.print("us | search: ");
    Serial.print(t3 - t2);
    Serial.print("us | decode+draw: ");
    Serial.print(t4 - t3);
    Serial.print("us | found: ");
    Serial.println(found);

    delay(200);
}