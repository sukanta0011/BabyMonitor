#include <algorithm>
#include <HTTPClient.h>
#include <TJpg_Decoder.h>
#include <Arduino_GFX_Library.h>
#include <ArduinoJson.h>
#include "utils.hpp"
#include "ringBuffer.hpp"


// Pin Definitions for ESP32-S3-CAM
#define TFT_MOSI 17
#define TFT_SCLK 18
#define TFT_CS    3
#define TFT_DC   15
#define TFT_RST  16

// // Pin Definitions for ESP32-S3-dev-kit
// #define TFT_MOSI 17
// #define TFT_SCLK 18
// #define TFT_CS    3
// #define TFT_DC   15
// #define TFT_RST  16

// Interrupt Button
#define BUTTON_PIN 9

// Colour
#define COLOR_TEMP   0xFBE0  // orange
#define COLOR_HUM    0x07FF  // cyan
#define COLOR_CO2    0xF800  // red
#define COLOR_LUX    0xFFE0  // yellow
#define COLOR_BG     0x0000  // black
#define COLOR_LABEL  0x8410  // grey
#define COLOR_WHT    0xFFFF  // grey


const uint32_t                      buffer_size = 102400;
uint32_t                            start = 0, end = 0;
std::string                         marker = "--frame\r\n";
HTTPClient                          http;
WiFiClient                          *stream;
int                                 httpCode;
RingBuffer<uint8_t, buffer_size>    buffer;
uint8_t                             *buffer_cpy = (uint8_t*)ps_malloc(buffer_size);
Arduino_DataBus                     *bus = new Arduino_ESP32SPI(
    TFT_DC, TFT_CS, TFT_SCLK, TFT_MOSI, GFX_NOT_DEFINED);
Arduino_GFX                         *gfx = new Arduino_ILI9488_18bit(
    bus, TFT_RST, 1 /* rotation */, false /* IPS */);
TaskHandle_t    readTaskHandle, extractAndDisplayTask, sensorTaskHandler;


float                               lux_val = 0, temp_val = 0, humidity_val = 0;
int                                 co2_val = 0;
bool                                sensors_valid = false;
SemaphoreHandle_t                   sensor_mutex = xSemaphoreCreateMutex();
volatile bool                       button_released = false;
volatile uint32_t                   last_interrupt_time = 0;
char outdoor_city[24] = "";
float outdoor_temp = 0, outdoor_humidity = 0;
bool outdoor_valid = false;


enum     DisplayMode { CAM1, CAM2, SENSORS, MODE_COUNT };
volatile DisplayMode requested_mode = CAM1;
volatile DisplayMode current_mode = CAM1;

struct  task_status 
{
    bool    read_task = false;
    bool    display_task = false;
    bool    sensor_task = false;
};

task_status taskStatus;

void    IRAM_ATTR button_isr()
{
    uint32_t    now = millis();
    if (now - last_interrupt_time > 50)
    {
        requested_mode = (DisplayMode)((requested_mode + 1) % MODE_COUNT);
        last_interrupt_time = now;
    }
}


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
    }
}

bool jpeg_output_callback(
    int16_t x, int16_t y, uint16_t w, uint16_t h, uint16_t* bitmap)
{
    gfx->draw16bitRGBBitmap(x, y, bitmap, w, h);
    return true;  // true = keep decoding, false = abort
}

void setup_decoder()
{
    TJpgDec.setJpgScale(2);  // decode at 1/2 scale
    TJpgDec.setCallback(jpeg_output_callback);
}


void decode_and_display(uint8_t *frame, uint32_t frame_size)
{
    if (frame_size < buffer_size)
    {
        TJpgDec.drawJpg(0, 0, frame, frame_size);
    }
}


bool    extract_frame(
    uint8_t *data, const uint32_t size, uint32_t &start, uint32_t &end)
{
    
    auto    it = std::search(data, data + size, marker.begin(), marker.end());
    if (it == (data + size)) { return false;}
    start = std::distance(data, it + marker.size());
    auto    end_it = std::search(
        it + marker.size(), data + size, marker.begin(), marker.end());
    if (end_it == data + size) { return false; }
    end = std::distance(data, end_it);
    return true;
}


void draw_sensor_panel()
{
    int screen_w = 480;
    int screen_h = 320;
    int strip_h = 50;
    int grid_top = strip_h;
    int grid_h = screen_h - strip_h;
    int cell_w = screen_w / 2;
    int cell_h = grid_h / 2;

    gfx->fillScreen(COLOR_BG);

    xSemaphoreTake(sensor_mutex, portMAX_DELAY);
    float local_lux = lux_val, local_temp = temp_val, local_humidity = humidity_val;
    int local_co2 = co2_val;
    bool local_valid = sensors_valid;
    char local_city[24];
    strncpy(local_city, outdoor_city, sizeof(local_city));
    float local_out_temp = outdoor_temp, local_out_hum = outdoor_humidity;
    bool local_out_valid = outdoor_valid;
    xSemaphoreGive(sensor_mutex);

    if (!local_valid)
    {
        gfx->setTextColor(COLOR_LABEL);
        gfx->setTextSize(2);
        gfx->setCursor(30, screen_h / 2 - 10);
        gfx->println("Sensors: waiting...");
        return;
    }

    // outdoor strip
    gfx->fillRect(0, 0, screen_w, strip_h, COLOR_WHT);
    gfx->setTextColor(COLOR_BG);
    gfx->setTextSize(3);
    gfx->setCursor(10, 15);
    if (local_out_valid)
    {
        char outdoor_str[48];
        snprintf(outdoor_str, sizeof(outdoor_str), "%s  T: %.1fC  H: %.0f%%",
                 local_city, local_out_temp, local_out_hum);
        gfx->println(outdoor_str);
    }
    else
    {
        gfx->println("Outdoor: unavailable");
    }

    // indoor 2x2 grid, unchanged logic, shifted down by grid_top
    struct Cell {
        int row, col;
        uint16_t color;
        const char* label;
        char value[16];
    };

    char temp_str[16], hum_str[16], co2_str[16], lux_str[16];
    snprintf(temp_str, sizeof(temp_str), "%.1f C", local_temp);
    snprintf(hum_str, sizeof(hum_str), "%.1f %%", local_humidity);
    snprintf(co2_str, sizeof(co2_str), "%d ppm", local_co2);
    snprintf(lux_str, sizeof(lux_str), "%.1f lux", local_lux);

    Cell cells[4] = {
        {0, 0, COLOR_TEMP, "TEMP", ""},
        {0, 1, COLOR_HUM,  "HUMIDITY", ""},
        {1, 0, COLOR_CO2,  "CO2", ""},
        {1, 1, COLOR_LUX,  "LIGHT", ""},
    };
    strncpy(cells[0].value, temp_str, sizeof(cells[0].value));
    strncpy(cells[1].value, hum_str,  sizeof(cells[1].value));
    strncpy(cells[2].value, co2_str,  sizeof(cells[2].value));
    strncpy(cells[3].value, lux_str,  sizeof(cells[3].value));

    for (int i = 0; i < 4; i++)
    {
        int x = cells[i].col * cell_w;
        int y = grid_top + cells[i].row * cell_h;

        gfx->fillRect(x + 4, y + 4, cell_w - 8, cell_h - 8, cells[i].color);

        gfx->setTextColor(COLOR_BG);
        gfx->setTextSize(2);
        gfx->setCursor(x + 20, y + 25);
        gfx->println(cells[i].label);

        gfx->setTextSize(4);
        gfx->setCursor(x + 20, y + cell_h / 2);
        gfx->println(cells[i].value);
    }
}

void    read_task(void *parameter)
{
    // Serial.print("read_task running on core: ");
    // Serial.println(xPortGetCoreID());
    while (true)
    {
        read_from_stream();
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}


void    extract_and_display_task(void *parameter)
{
    // Serial.print("extract_and_display_task running on core: ");
    // Serial.println(xPortGetCoreID());

    setup_decoder();
    while (true)
    {
        buffer.copy_data(buffer_cpy);
        bool found = extract_frame(buffer_cpy, buffer_size, start, end);
        if (found)
        {
            decode_and_display(buffer_cpy + start, (end - start));
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void sensor_task(void *parameter)
{
    // Serial.print("sensor_task running on core: ");
    // Serial.println(xPortGetCoreID());

    while (true)
    {
        fetch_sensors();
        vTaskDelay(pdMS_TO_TICKS(10000));  // 10 second interval
    }
}


void    start_live_stream()
{

    // http.begin("http://pi5.local:8000/video/cam1");
    // httpCode = http.GET();
    // if (httpCode == 200)
    // {
    //     stream = http.getStreamPtr();
    // }
    // else
    // {
    //     Serial.println("Unable to connect to Pi5");
    // }

    
    if (!taskStatus.read_task)
    {
        xTaskCreate(read_task, "ReadTask", 8192, NULL, 1, &readTaskHandle);
        taskStatus.read_task = true;
    }
    else {vTaskResume(readTaskHandle);}
    if (!taskStatus.display_task)
    {
        xTaskCreate(
            extract_and_display_task, "ExtractAndDispay",
            8192, NULL, 1, &extractAndDisplayTask);
        taskStatus.display_task = true;
    }
    else { vTaskResume(extractAndDisplayTask); }
}

void    stop_live_stream()
{
    if (taskStatus.display_task)
    { vTaskSuspend(extractAndDisplayTask); }
    if (taskStatus.read_task)
    { vTaskSuspend(readTaskHandle);}
    http.end();
}


void fetch_sensors()
{
    // Serial.println("sensor task running...");
    http.begin("http://pi5.local:8000/sensors");
    httpCode = http.GET();
    // Serial.println(httpCode);

    if (httpCode == 200)
    {
        String                  payload = http.getString();
        JsonDocument            doc;
        DeserializationError    err = deserializeJson(doc, payload);

        if (!err)
        {
            xSemaphoreTake(sensor_mutex, portMAX_DELAY);
            lux_val = doc["bh1750"]["lux"] | 0.0;
            co2_val = doc["scd40"]["co2"] | 0;
            temp_val = doc["scd40"]["temperature"] | 0.0;
            humidity_val = doc["scd40"]["humidity"] | 0.0;

            const char* city = doc["outdoor"]["city"] | "";
            strncpy(outdoor_city, city, sizeof(outdoor_city) - 1);
            outdoor_city[sizeof(outdoor_city) - 1] = '\0';
            outdoor_temp = doc["outdoor"]["temperature"] | 0.0;
            outdoor_humidity = doc["outdoor"]["humidity"] | 0.0;
            outdoor_valid = doc["outdoor"]["valid"] | false;

            sensors_valid = true;
            xSemaphoreGive(sensor_mutex);
            // Serial.print("co2_val: ");
            // Serial.println(co2_val);

            draw_sensor_panel();
        }
        else
        {
            Serial.println("JSON parse error....");
        }
    }
    else
    {
        Serial.print("HTTP GET failed, code: ");
        Serial.println(httpCode);
    }

    http.end();
}


void    start_sensor_stream()
{
    if (!taskStatus.sensor_task)
    {
        xTaskCreate(sensor_task, "SensorTask", 8192, NULL, 0, &sensorTaskHandler);
        taskStatus.sensor_task = true;
    }
    else { vTaskResume(sensorTaskHandler); }
}

void    stop_sensor_stream()
{
    vTaskSuspend(sensorTaskHandler);
}

void switch_to_mode(DisplayMode mode)
{
    if (mode == SENSORS)
    {
        stop_live_stream();
        current_mode = mode;
        start_sensor_stream();
    }
    else
    {
        if (taskStatus.sensor_task)
        { stop_sensor_stream(); }
        http.begin(mode == CAM1 ? "http://pi5.local:8000/video/cam1"
                                  : "http://pi5.local:8000/video/cam2");
        httpCode = http.GET();
        if (httpCode == 200)
        { stream = http.getStreamPtr(); }
        else
        {
            Serial.println("Unable to connect to Pi5");
            return;
        }
        current_mode = mode;
        start_live_stream();
    }
}



void setup()
{
    Serial.begin(115200);
    // start_sensor_stream();
    // start_live_stream();
    pinMode(BUTTON_PIN, INPUT);
    attachInterrupt(digitalPinToInterrupt(BUTTON_PIN), button_isr, FALLING);
    if (!connect_to_wifi()) { return; }
    if (!gfx->begin()) { Serial.println("gfx->begin() failed!"); }
    else { gfx->fillScreen(0); }

    switch_to_mode(requested_mode);
}


void    loop()
{
    // unsigned long t0 = micros();
    // read_from_stream();
    // unsigned long t1 = micros();

    // buffer.copy_data(buffer_cpy);
    // unsigned long t2 = micros();

    // bool found = extract_frame(buffer_cpy, buffer_size, start, end);
    // unsigned long t3 = micros();

    // if (found)
    // {
    //     decode_and_display(buffer_cpy + start, (end - start));
    // }
    // unsigned long t4 = micros();

    // Serial.print("read: ");
    // Serial.print(t1 - t0);
    // Serial.print("us | copy: ");
    // Serial.print(t2 - t1);
    // Serial.print("us | search: ");
    // Serial.print(t3 - t2);
    // Serial.print("us | decode+draw: ");
    // Serial.print(t4 - t3);
    // Serial.print("us | found: ");
    // Serial.print(found);
    // Serial.print(" | Size: ");
    // Serial.println(end - start);

    if (current_mode != requested_mode)
    {
        switch_to_mode(requested_mode);
        Serial.println(requested_mode);
    }
    delay(100);
}