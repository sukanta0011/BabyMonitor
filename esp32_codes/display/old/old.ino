#include <HTTPClient.h>
#include <WiFi.h>
#include <string>
#include <algorithm>
#include <TJpg_Decoder.h>
#include <Arduino_GFX_Library.h>

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
std::vector<uint8_t> buffer;
std::vector<uint8_t> frame;
Arduino_DataBus *bus = new Arduino_ESP32SPI(TFT_DC, TFT_CS, TFT_SCLK, TFT_MOSI, GFX_NOT_DEFINED);
Arduino_GFX *gfx = new Arduino_ILI9488_18bit(bus, TFT_RST, 1 /* rotation */, false /* IPS */);

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

void read_into_buffer(std::vector<uint8_t>& buffer)
{
    int val;
    uint32_t  bytes_read = 0;
    while (stream->available() && bytes_read < 10000)
    {
        val = stream->read();
        if (val != -1)
        {
            buffer.push_back((uint8_t)val);
            bytes_read++;
        }
    }
    // uint32_t    bytes_read = 0;
    // uint8_t     temp[512];
    // // uint8_t     val;
    // while (stream->available() && bytes_read < 10000)
    // {
    //     size_t n = stream->readBytes(temp, min((size_t)stream->available(), sizeof(temp)));
    //     for (size_t i = 0; i < n; i++)
    //     {
    //         buffer.push_back(temp[i]);
    //         bytes_read += 1;
    //     }
    // }
}

int find_boundary(std::vector<uint8_t>& buffer)
{
    std::string identifier = "--frame\r\n";
    auto it = std::search(
        buffer.begin(), buffer.end(),
        identifier.begin(), identifier.end()
    );

    if (it == buffer.end()) {
        Serial.print("--frame not found in bytes: ");
        Serial.println(buffer.size());
        return -1;  // not found yet
    }
    return std::distance(buffer.begin(), it) + 9;
}

int find_last_complete_frame(std::vector<uint8_t>& buffer, uint32_t& frame_start, uint32_t& frame_end)
{
    std::string identifier = "--frame\r\n";

    auto rit1 = std::search(
        buffer.rbegin(), buffer.rend(),
        identifier.rbegin(), identifier.rend()
    );
    if (rit1 == buffer.rend()) return -1;  // no boundary found at all

    auto rit2 = std::search(
        rit1 + identifier.size(), buffer.rend(),
        identifier.rbegin(), identifier.rend()
    );
    if (rit2 == buffer.rend()) return -1;  // only one boundary found, no complete frame yet

    // rit1/rit2 are reverse iterators — convert to normal (forward) positions
    auto last_boundary_start = rit1.base() - identifier.size();
    auto second_last_boundary_end = rit2.base();

    frame_start = std::distance(buffer.begin(), second_last_boundary_end);
    frame_end = std::distance(buffer.begin(), last_boundary_start);

    return 0;
}

bool jpeg_output_callback(int16_t x, int16_t y, uint16_t w, uint16_t h, uint16_t* bitmap)
{
    gfx->draw16bitRGBBitmap(x, y, bitmap, w, h);
    return true;  // true = keep decoding, false = abort
}

void setup_decoder()
{
    TJpgDec.setJpgScale(2);  // decode at 1/2 scale
    TJpgDec.setCallback(jpeg_output_callback);
}

void decode_and_display(std::vector<uint8_t>& frame)
{
    TJpgDec.drawJpg(0, 0, frame.data(), frame.size());
}

// std::vector<uint8_t>  get_frame(std::vector<uint8_t>& buffer, uint32_t size)
// {
//   std::vector<uint8_t> frame;
//   for (uint32_t i=0; i < size; i++)
//   {
//     frame.push_back(buffer[i]);
//   }
//   buffer.erase(buffer.begin(), buffer.begin() + size);
//   Serial.println("Buffer erased");
//   return frame;
// }

void  setup()
{
  Serial.begin(115200);
  if (connect_to_wifi())
  {
    http.begin("http://pi5.local:8000/video/cam2");
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

// void loop()
// {
//   int bytes = 0;
//   read_into_buffer(buffer);
//   bytes = find_boundary(buffer);
//   Serial.print("bytes: ");
//   Serial.println(bytes);
//   if (bytes > 0)
//   {
//     frame = get_frame(buffer, bytes);
//     Serial.print("frame size: ");
//     Serial.println(frame.size());
//   }
//   // Serial.println(buffer.size());
//   // delay(100);
// }

// void loop()
// {
//   while (stream->available())
//   {
//     int val = stream->read();
//     if (val != -1)
//     {
//       Serial.write((char)val);
//     }
//   }
// }

void loop()
{
  int bytes = 0;
  std::string identifier = "--frame\r\n";
  read_into_buffer(buffer);

  // Diagnostic: print buffer size and first N bytes as raw numbers
  // Serial.print("buffer size: ");
  // Serial.println(buffer.size());

  // int preview_len = min((int)buffer.size(), 20);
  // Serial.print("first bytes: ");
  // for (int i = 0; i < preview_len; i++)
  // {
  //   Serial.print(buffer[i]);
  //   Serial.print(" ");
  // }
  // Serial.println();

  // bytes = find_boundary(buffer);
  // Serial.print("bytes: ");
  // Serial.println(bytes);

  uint32_t frame_start, frame_end;
  if (find_last_complete_frame(buffer, frame_start, frame_end) == 0)
  {
      // Serial.print("buffer size before: ");
      // Serial.println(buffer.size());
      frame.assign(buffer.begin() + frame_start, buffer.begin() + frame_end);
      buffer.erase(buffer.begin(), buffer.begin() + frame_end + identifier.size());
      decode_and_display(frame);
      Serial.print("frame size: ");
      Serial.println(frame.size());
      // Serial.print("buffer size after: ");
      // Serial.println(buffer.size());
  }

  delay(100);
}