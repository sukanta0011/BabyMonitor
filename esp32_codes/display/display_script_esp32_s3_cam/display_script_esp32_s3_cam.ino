#include <Arduino_GFX_Library.h>

// Standard 16-bit RGB565 Color Definitions
#define BLACK   0x0000
#define BLUE    0x001F
#define RED     0xF800
#define GREEN   0x07E0
#define CYAN    0x07FF
#define MAGENTA 0xF81F
#define YELLOW  0xFFE0
#define WHITE   0xFFFF

// Pin Definitions for your ESP32-S3
#define TFT_MOSI 17
#define TFT_SCLK 18
#define TFT_CS    3
#define TFT_DC   15
#define TFT_RST  16

Arduino_DataBus *bus = new Arduino_ESP32SPI(TFT_DC, TFT_CS, TFT_SCLK, TFT_MOSI, GFX_NOT_DEFINED);
Arduino_GFX *gfx = new Arduino_ILI9488_18bit(bus, TFT_RST, 1 /* rotation */, false /* IPS */);

void  blink()
{
  // gfx->fillRect(100, 100, 30, 30, WHITE);
  // gfx->fillRect(100, 200, 30, 30, WHITE);
  for (int i=60; i>0; i -= 4)
  {
    gfx->fillRect(100, 100 + i - 4, 60, 4, BLACK);
    gfx->fillRect(250, 100 + i - 4, 60, 4, BLACK);
    delay(50);
  }
  for (int i=0; i<60; i += 4)
  {
    gfx->fillRect(100, 100 + i, 60, 4, BLUE);
    gfx->fillRect(250, 100 + i, 60, 4, BLUE);
    delay(50);
  }
}


void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Initializing ILI9488 with Arduino_GFX...");

  if (!gfx->begin()) {
    Serial.println("gfx->begin() failed!");
  }

  gfx->fillScreen(BLACK);
  // gfx->setTextColor(WHITE);
  // gfx->setTextSize(3);
  // gfx->setCursor(20, 40);
  // gfx->println("ESP32-S3 Active!");

  // gfx->setTextColor(YELLOW);
  // gfx->setTextSize(2);
  // gfx->setCursor(20, 90);
  // gfx->println("Arduino_GFX Running.");
  gfx->fillRect(100, 100, 60, 60, BLUE);
  gfx->fillRect(250, 100, 60, 60, BLUE);
  gfx->fillRect(180, 220, 50, 10, BLUE);

  // delay(1000);
  // blink();
}

void loop() {
  // gfx->fillRect(20, 140, 300, 30, BLACK);
  // gfx->setTextColor(GREEN);
  // gfx->setTextSize(2);
  // gfx->setCursor(20, 140);
  // gfx->printf("Uptime (s): %lu", millis() / 1000);
  if (millis() % 10000 == 0)
  {
    blink();
  }
  // timer += millis();
  // gfx->printf("%lu", millis() / 1000);
  // delay(1000);
  // blink();
}