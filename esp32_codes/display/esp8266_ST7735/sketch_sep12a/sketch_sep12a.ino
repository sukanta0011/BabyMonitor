#include <Adafruit_GFX.h>    
#include <Adafruit_ST7735.h> 
#include <SPI.h>

#define TFT_CS   15  
#define TFT_DC   0   
#define TFT_RST  2  
// SDA/MOSI D7
// SCL/SCK D5
// CS D8 

Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);

int tftWidth = 0;
int tftHeight = 0;

// State tracking
unsigned long nextActionTime = 0;
int currentExpression = 0; // 0=Normal, 1=Happy, 2=Angry

void setup() {
  tft.initR(INITR_BLACKTAB); 
  tft.setRotation(1); // Landscape mode
  
  tftWidth = tft.width();
  tftHeight = tft.height();
  
  tft.fillScreen(ST7735_BLACK);
  
  drawFace(0); // Start with normal expression
  nextActionTime = millis() + random(2000, 4000); 
}

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis >= nextActionTime) {
    if (random(0, 100) < 40) {
      // 40% chance to just blink out of the current expression
      drawFace(-1); // -1 triggers Blink state
      delay(150);
      drawFace(currentExpression); // Return to current background mood
      nextActionTime = currentMillis + random(1000, 2500);
    } else {
      // 60% chance to shift to a brand new structural facial mood
      currentExpression = random(0, 3); // Picks 0 (Normal), 1 (Happy), or 2 (Angry)
      drawFace(currentExpression);
      nextActionTime = currentMillis + random(3000, 6000);
    }
  }
}

// Single function managing all geometric block rendering states
void drawFace(int expression) {
  int eyeSize = 30; 
  int eyeSpacing = tftWidth / 4; 
  
  int leftEyeX = (tftWidth / 2) - eyeSpacing - (eyeSize / 2);
  int rightEyeX = (tftWidth / 2) + eyeSpacing - (eyeSize / 2);
  int eyeY = (tftHeight / 2) - (eyeSize / 2);

  // Always clear the eye canvas boxes entirely before redrawing
  tft.fillRect(leftEyeX, eyeY - 5, eyeSize, eyeSize + 10, ST7735_BLACK);
  tft.fillRect(rightEyeX, eyeY - 5, eyeSize, eyeSize + 10, ST7735_BLACK);

  switch (expression) {
    case -1: // BLINKING SLIT
      {
        int blinkY = (tftHeight / 2) - 2;
        tft.fillRect(leftEyeX, blinkY, eyeSize, 4, ST7735_WHITE);
        tft.fillRect(rightEyeX, blinkY, eyeSize, 4, ST7735_WHITE);
      }
      break;

    case 0: // NORMAL SOLID BLOCKS
      tft.fillRect(leftEyeX, eyeY, eyeSize, eyeSize, ST7735_WHITE);
      tft.fillRect(rightEyeX, eyeY, eyeSize, eyeSize, ST7735_WHITE);
      break;

    case 1: // HAPPY CHEVRONS (^ ^) using solid native triangles
      // Left eye arrow shape (Outer triangle minus inner cut triangle)
      tft.fillTriangle(leftEyeX, eyeY + eyeSize, leftEyeX + (eyeSize / 2), eyeY, leftEyeX + eyeSize, eyeY + eyeSize, ST7735_WHITE);
      tft.fillTriangle(leftEyeX + 4, eyeY + eyeSize + 1, leftEyeX + (eyeSize / 2), eyeY + 6, leftEyeX + eyeSize - 4, eyeY + eyeSize + 1, ST7735_BLACK);
      
      // Right eye arrow shape
      tft.fillTriangle(rightEyeX, eyeY + eyeSize, rightEyeX + (eyeSize / 2), eyeY, rightEyeX + eyeSize, eyeY + eyeSize, ST7735_WHITE);
      tft.fillTriangle(rightEyeX + 4, eyeY + eyeSize + 1, rightEyeX + (eyeSize / 2), eyeY + 6, rightEyeX + eyeSize - 4, eyeY + eyeSize + 1, ST7735_BLACK);
      break;

    case 2: // ANGRY SLANTED BLOCKS (\ /)
      // Left eye block with top-left corner shaved off
      tft.fillRect(leftEyeX, eyeY, eyeSize, eyeSize, ST7735_WHITE);
      for(int i=0; i<15; i++) {
        tft.drawFastHLine(leftEyeX, eyeY + i, i + 5, ST7735_BLACK);
      }
      // Right eye block with top-right corner shaved off
      tft.fillRect(rightEyeX, eyeY, eyeSize, eyeSize, ST7735_WHITE);
      for(int i=0; i<15; i++) {
        tft.drawFastHLine(rightEyeX + eyeSize - (i + 5), eyeY + i, i + 5, ST7735_BLACK);
      }
      break;
  }
}
