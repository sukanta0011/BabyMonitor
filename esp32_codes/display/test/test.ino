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
#define ORANGE  0xFD20
#define PURPLE  0x780F
#define PINK    0xF81F

// Pin Definitions for ESP32-S3
#define TFT_MOSI 17
#define TFT_SCLK 18
#define TFT_CS    3
#define TFT_DC   15
#define TFT_RST  16

Arduino_DataBus *bus = new Arduino_ESP32SPI(TFT_DC, TFT_CS, TFT_SCLK, TFT_MOSI, GFX_NOT_DEFINED);
Arduino_GFX *gfx = new Arduino_ILI9488_18bit(bus, TFT_RST, 1 /* rotation */, false /* IPS */);

unsigned long lastFaceChange = 0; 
const unsigned long faceInterval = 5000; // 5 seconds
int lastFace = -1; 

void clearFace() {
  // Completely clear the active bounds of the canvas
  gfx->fillRect(20, 20, 440, 280, BLACK); 
}

// ==================== FACES 1 - 10 ====================
void drawHappyFace() {
  gfx->fillRect(100, 70, 80, 80, YELLOW);  
  gfx->fillRect(300, 70, 80, 80, YELLOW);  
  gfx->fillRect(200, 220, 80, 15, YELLOW); 
}
void drawSurprisedFace() {
  gfx->fillCircle(140, 110, 45, CYAN);      
  gfx->fillCircle(340, 110, 45, CYAN);      
  gfx->fillCircle(240, 230, 30, CYAN);      
}
void drawSadFace() {
  gfx->fillRect(100, 110, 80, 50, BLUE);    
  gfx->fillRect(300, 110, 80, 50, BLUE);    
  gfx->fillRect(200, 230, 80, 15, BLUE);    
  gfx->fillRect(90, 70, 70, 12, BLUE);      
  gfx->fillRect(320, 70, 70, 12, BLUE);     
}
void drawAngryFace() {
  gfx->fillRect(100, 100, 80, 70, RED);     
  gfx->fillRect(300, 100, 80, 70, RED);     
  gfx->fillRect(215, 230, 50, 12, RED);     
  gfx->drawLine(80, 50, 190, 95, RED); gfx->drawLine(80, 51, 190, 96, RED);
  gfx->drawLine(400, 50, 290, 95, RED); gfx->drawLine(400, 51, 290, 96, RED);
}
void drawWinkFace() {
  gfx->fillRect(100, 70, 80, 80, MAGENTA);  
  gfx->fillRect(300, 105, 80, 15, MAGENTA); 
  gfx->fillRect(200, 210, 80, 15, MAGENTA); 
}
void drawSleepingFace() {
  gfx->fillRect(100, 105, 80, 15, BLUE);    
  gfx->fillRect(300, 105, 80, 15, BLUE);    
  gfx->fillCircle(240, 220, 18, BLUE);      
}
void drawNervousFace() {
  gfx->fillRect(110, 90, 60, 60, ORANGE);
  gfx->fillRect(310, 90, 60, 60, ORANGE);
  gfx->fillRect(170, 220, 140, 12, ORANGE); 
  gfx->fillTriangle(60, 50, 45, 80, 75, 80, CYAN); gfx->fillCircle(60, 80, 15, CYAN); // Sweat
}
void drawDeadFace() {
  gfx->drawLine(100, 70, 180, 150, WHITE); gfx->drawLine(180, 70, 100, 150, WHITE);
  gfx->drawLine(300, 70, 380, 150, WHITE); gfx->drawLine(380, 70, 300, 150, WHITE);
  gfx->fillRect(190, 230, 100, 12, WHITE);  
}
void drawDizzyFace() {
  gfx->drawRect(100, 70, 80, 80, PURPLE); gfx->drawRect(115, 85, 50, 50, PURPLE);
  gfx->drawRect(300, 70, 80, 80, PURPLE); gfx->drawRect(315, 85, 50, 50, PURPLE);
  gfx->fillCircle(240, 230, 22, PURPLE);     
}
void drawHypedFace() {
  gfx->fillRect(130, 60, 25, 100, GREEN); gfx->fillRect(95, 97, 95, 25, GREEN); // Star L
  gfx->fillRect(325, 60, 25, 100, GREEN); gfx->fillRect(290, 97, 95, 25, GREEN); // Star R
  gfx->fillRect(180, 210, 120, 35, GREEN);   
}

// ==================== FACES 11 - 20 ====================
void drawCoolFace() {
  gfx->fillRect(70, 85, 130, 55, WHITE); gfx->fillRect(280, 85, 130, 55, WHITE); gfx->fillRect(200, 85, 80, 20, WHITE); 
  gfx->fillRect(190, 225, 100, 15, WHITE);   
}
void drawSkepticalFace() {
  gfx->fillRect(100, 105, 80, 25, ORANGE);   
  gfx->fillRect(300, 75, 80, 65, ORANGE);    
  gfx->fillRect(285, 45, 110, 15, ORANGE);   
  gfx->fillRect(180, 220, 120, 12, ORANGE);  
}
void drawLoveFace() {
  gfx->fillCircle(120, 90, 25, RED); gfx->fillCircle(160, 90, 25, RED); gfx->fillTriangle(96, 102, 184, 102, 140, 155, RED); // Heart L
  gfx->fillCircle(320, 90, 25, RED); gfx->fillCircle(360, 90, 25, RED); gfx->fillTriangle(296, 102, 384, 102, 340, 155, RED); // Heart R
  gfx->fillTriangle(180, 210, 300, 210, 240, 260, RED);
}
void drawMoneyFace() {
  gfx->fillRect(130, 70, 25, 80, GREEN); gfx->fillRect(100, 90, 85, 15, GREEN); gfx->fillRect(100, 120, 85, 15, GREEN); // $ L
  gfx->fillRect(330, 70, 25, 80, GREEN); gfx->fillRect(300, 90, 85, 15, GREEN); gfx->fillRect(300, 120, 85, 15, GREEN); // $ R
  gfx->fillRect(210, 210, 60, 15, GREEN); gfx->fillRect(222, 225, 36, 40, GREEN); 
}
void drawCryingFace() {
  gfx->fillRect(100, 80, 80, 30, CYAN); gfx->fillRect(300, 80, 80, 30, CYAN);
  gfx->fillRect(125, 110, 30, 70, CYAN); gfx->fillRect(325, 110, 30, 70, CYAN); // Tears streams
  gfx->fillRect(200, 230, 80, 15, CYAN);
}
void drawEvilFace() {
  gfx->fillRect(100, 90, 80, 50, PURPLE); gfx->fillRect(300, 90, 80, 50, PURPLE);
  gfx->drawLine(90, 60, 190, 95, PURPLE); gfx->drawLine(390, 60, 290, 95, PURPLE); // Horn brows
  gfx->fillTriangle(190, 210, 290, 210, 240, 255, PURPLE); // Evil grin
}
void drawBoredFace() {
  gfx->fillRect(100, 100, 80, 20, WHITE); gfx->fillRect(300, 100, 80, 20, WHITE);
  gfx->fillRect(190, 220, 100, 12, WHITE); // Flat horizontal line expression
}
void drawBlushingFace() {
  gfx->fillRect(100, 70, 80, 80, PINK); gfx->fillRect(300, 70, 80, 80, PINK);
  gfx->fillRect(70, 160, 40, 20, RED);  gfx->fillRect(370, 160, 40, 20, RED); // Blush patches
  gfx->fillRect(210, 220, 60, 12, PINK);
}
void drawPirateFace() {
  gfx->fillRect(100, 70, 80, 80, YELLOW); // Left Eye
  gfx->fillRect(280, 60, 120, 100, RED);   // Big crimson Eyepatch over right eye
  gfx->drawLine(240, 50, 420, 130, WHITE); // Eyepatch strap
  gfx->fillRect(190, 230, 100, 15, YELLOW);
}
void drawMoustacheFace() {
  gfx->fillRect(110, 80, 60, 60, ORANGE); gfx->fillRect(310, 80, 60, 60, ORANGE);
  gfx->fillTriangle(150, 200, 240, 200, 170, 240, ORANGE); // Left handlebar
  gfx->fillTriangle(330, 200, 240, 200, 310, 240, ORANGE); // Right handlebar
}

// ==================== FACES 21 - 30 ====================
void drawNerdFace() {
  gfx->drawRect(90, 70, 90, 70, WHITE); gfx->drawRect(300, 70, 90, 70, WHITE); gfx->fillRect(180, 95, 120, 15, WHITE); // Glasses
  gfx->fillRect(210, 220, 20, 25, WHITE); gfx->fillRect(250, 220, 20, 25, WHITE); // Buck teeth
}
void drawCyclopsFace() {
  gfx->fillRect(200, 60, 80, 80, RED); // Single giant center eye
  gfx->fillRect(170, 220, 140, 16, RED);
}
void drawConfusedFace() {
  gfx->fillCircle(140, 110, 35, ORANGE); gfx->fillRect(300, 95, 80, 30, ORANGE); // Unequal size eyes
  gfx->drawLine(180, 240, 230, 210, ORANGE); gfx->drawLine(230, 210, 280, 240, ORANGE); // Zig-zag mouth
}
void drawMonocleFace() {
  gfx->fillRect(100, 70, 80, 80, YELLOW); // Normal left eye
  gfx->drawCircle(340, 110, 45, CYAN); gfx->fillCircle(340, 110, 25, CYAN); // Monocle frame + lens
  gfx->fillRect(190, 220, 100, 12, YELLOW);
}
void drawAlienFace() {
  gfx->fillTriangle(100, 60, 160, 60, 130, 140, GREEN); // Oval-angled alien eye L
  gfx->fillTriangle(320, 60, 380, 60, 350, 140, GREEN); // Oval-angled alien eye R
  gfx->fillCircle(240, 230, 15, GREEN);
}
void drawGhostFace() {
  gfx->fillCircle(140, 100, 25, WHITE); gfx->fillCircle(340, 100, 25, WHITE); // Small hollow eyes
  gfx->fillRect(215, 200, 50, 45, WHITE); // Long hollow mouth
}
void drawVampireFace() {
  gfx->fillRect(100, 90, 80, 50, RED); gfx->fillRect(300, 90, 80, 50, RED);
  gfx->fillRect(170, 210, 140, 12, RED); // Mouth line
  gfx->fillTriangle(190, 222, 210, 222, 200, 245, WHITE); // Left Fang
  gfx->fillTriangle(270, 222, 290, 222, 280, 245, WHITE); // Right Fang
}
void drawClownFace() {
  gfx->fillCircle(140, 100, 30, CYAN); gfx->fillCircle(340, 100, 30, CYAN);
  gfx->fillCircle(240, 145, 25, RED); // Red nose
  gfx->drawRect(160, 210, 160, 40, RED); // Large painted smile outline
}
void drawRobotGlanceFace() {
  // Mechanical scanning HUD style matrix
  gfx->drawRect(60, 80, 360, 60, GREEN);
  gfx->fillRect(90, 90, 40, 40, GREEN);  gfx->fillRect(350, 90, 40, 40, GREEN);
  gfx->fillRect(200, 230, 80, 10, GREEN);
}
void drawThinkingFace() {
  gfx->fillRect(100, 100, 80, 25, ORANGE); gfx->fillRect(300, 70, 80, 55, ORANGE); // Thinking brows
  gfx->fillRect(180, 230, 120, 12, ORANGE); // Flat thumb line resting near mouth
  gfx->fillRect(150, 242, 60, 12, ORANGE);  // Finger support asset
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  if (!gfx->begin()) { Serial.println("gfx->begin() failed!"); }
  gfx->fillScreen(BLACK);
  randomSeed(analogRead(0)); 
  drawHappyFace();
  lastFaceChange = millis();
}

void loop() {
  if (millis() - lastFaceChange >= faceInterval) {
    clearFace();
    
    int randomFace;
    do {
      randomFace = random(30); // 30 choices
    } while (randomFace == lastFace);
    
    lastFace = randomFace; 

    switch(randomFace) {
      case 0: drawHappyFace(); break;
      case 1: drawSurprisedFace(); break;
      case 2: drawSadFace(); break;
      case 3: drawAngryFace(); break;
      case 4: drawWinkFace(); break;
      case 5: drawSleepingFace(); break;
      case 6: drawNervousFace(); break;
      case 7: drawDeadFace(); break;
      case 8: drawDizzyFace(); break;
      case 9: drawHypedFace(); break;
      case 10: drawCoolFace(); break;
      case 11: drawSkepticalFace(); break;
      case 12: drawLoveFace(); break;
      case 13: drawMoneyFace(); break;
      case 14: drawCryingFace(); break;
      case 15: drawEvilFace(); break;
      case 16: drawBoredFace(); break;
      case 17: drawBlushingFace(); break;
      case 18: drawPirateFace(); break;
      case 19: drawMoustacheFace(); break;
      case 20: drawNerdFace(); break;
      case 21: drawCyclopsFace(); break;
      case 22: drawConfusedFace(); break;
      case 23: drawMonocleFace(); break;
      case 24: drawAlienFace(); break;
      case 25: drawGhostFace(); break;
      case 26: drawVampireFace(); break;
      case 27: drawClownFace(); break;
      case 28: drawRobotGlanceFace(); break;
      case 29: drawThinkingFace(); break;
    }
    
    lastFaceChange = millis();
  }
}
