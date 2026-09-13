/*
  OA Screening Firmware for ESP32 + 2x MPU6050 (Wi-Fi + Serial)
  
  Reads thigh (0x68) and lower-leg (0x69) MPU6050 sensors at 50 Hz.
  Transmits real-time kinematic gait telemetry to the Flask Web Application
  over Wi-Fi (UDP port 5005 or HTTP POST port 5000) and USB Serial (115200 baud).

  Output format:
  ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2

  Disclaimer: ⚠️ For screening only, not medical diagnosis.
*/

#include <Wire.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <HTTPClient.h>

// ==========================================
// --- WI-FI CONFIGURATION (EDIT HERE) ---
// ==========================================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";         // Enter your Wi-Fi SSID
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";     // Enter your Wi-Fi password

// IP address of the computer running the Flask web application
// (Check your PC's Wi-Fi IP address e.g. 192.168.1.100)
const char* SERVER_IP     = "192.168.1.100";
const uint16_t UDP_PORT   = 5005;                     // Fast UDP streaming port
const uint16_t HTTP_PORT  = 5000;                     // Flask HTTP port

// Choose streaming method:
// 1 = UDP Stream (Recommended: ultra-low latency, smooth 50Hz live chart)
// 2 = HTTP POST (Batched HTTP requests to /api/esp32/stream)
#define STREAM_MODE 1

// ==========================================
// --- HARDWARE PINOUT & ADDRESSES ---
// ==========================================
#define SDA_PIN 21
#define SCL_PIN 22
#define MPU_ADDR_1 0x68   // Thigh IMU (AD0 -> GND)
#define MPU_ADDR_2 0x69   // Lower-leg IMU (AD0 -> 3.3V)
#define REPORT_INTERVAL_MS 20  // 50 Hz (every 20ms)

TwoWire I2C_0 = Wire;
WiFiUDP udpClient;

struct SensorData {
  float ax;
  float ay;
  float az;
  float gx;
  float gy;
  float gz;
  bool ok;
};

SensorData readSensorData(uint8_t addr) {
  SensorData data = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, false};

  I2C_0.beginTransmission(addr);
  I2C_0.write(0x3B);
  uint8_t transmissionStatus = I2C_0.endTransmission(false);
  if (transmissionStatus != 0) {
    return data;
  }

  I2C_0.requestFrom(addr, (uint8_t)14, (uint8_t)true);
  if (I2C_0.available() < 14) {
    return data;
  }

  int16_t ax_raw = (int16_t)((I2C_0.read() << 8) | I2C_0.read());
  int16_t ay_raw = (int16_t)((I2C_0.read() << 8) | I2C_0.read());
  int16_t az_raw = (int16_t)((I2C_0.read() << 8) | I2C_0.read());
  int16_t tmp_raw = (int16_t)((I2C_0.read() << 8) | I2C_0.read());
  int16_t gx_raw = (int16_t)((I2C_0.read() << 8) | I2C_0.read());
  int16_t gy_raw = (int16_t)((I2C_0.read() << 8) | I2C_0.read());
  int16_t gz_raw = (int16_t)((I2C_0.read() << 8) | I2C_0.read());

  (void)tmp_raw;

  // Conversion: ±2g scale (16384 LSB/g), ±250 deg/s scale (131 LSB/(deg/s))
  data.ax = ax_raw / 16384.0f;
  data.ay = ay_raw / 16384.0f;
  data.az = az_raw / 16384.0f;
  data.gx = gx_raw / 131.0f;
  data.gy = gy_raw / 131.0f;
  data.gz = gz_raw / 131.0f;
  data.ok = true;
  return data;
}

void configureMPU(uint8_t addr) {
  I2C_0.beginTransmission(addr);
  I2C_0.write(0x6B);
  I2C_0.write(0x00);  // Wake up MPU
  I2C_0.endTransmission(true);

  I2C_0.beginTransmission(addr);
  I2C_0.write(0x1C);
  I2C_0.write(0x00);  // ±2g
  I2C_0.endTransmission(true);

  I2C_0.beginTransmission(addr);
  I2C_0.write(0x1B);
  I2C_0.write(0x00);  // ±250 deg/s
  I2C_0.endTransmission(true);
}

void connectToWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.println();
  Serial.print("Connecting to Wi-Fi SSID: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println(">>> Wi-Fi Connected Successfully! <<<");
    Serial.print("ESP32 IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Target Flask Server: ");
    Serial.print(SERVER_IP);
    Serial.print(":");
    Serial.println(UDP_PORT);
  } else {
    Serial.println("\n[!] Wi-Fi connection timed out. Will stream via Serial and retry Wi-Fi.");
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n==========================================");
  Serial.println("  OA Screening ESP32 Wi-Fi Firmware");
  Serial.println("==========================================");

  I2C_0.begin(SDA_PIN, SCL_PIN);
  I2C_0.setTimeOut(50);

  Serial.println("Configuring MPU6050 (0x68 - Thigh)...");
  configureMPU(MPU_ADDR_1);

  Serial.println("Configuring MPU6050 (0x69 - Lower-leg)...");
  configureMPU(MPU_ADDR_2);

  connectToWiFi();

  Serial.println("READY - Streaming started.");
  Serial.flush();
}

unsigned long lastReport = 0;
unsigned long lastWiFiCheck = 0;

void loop() {
  unsigned long now = millis();

  // Periodic Wi-Fi reconnection check every 10s if disconnected
  if (now - lastWiFiCheck > 10000) {
    lastWiFiCheck = now;
    if (WiFi.status() != WL_CONNECTED) {
      WiFi.reconnect();
    }
  }

  if (now - lastReport < REPORT_INTERVAL_MS) {
    return;
  }
  lastReport = now;

  SensorData s1 = readSensorData(MPU_ADDR_1);
  SensorData s2 = readSensorData(MPU_ADDR_2);

  if (!s1.ok || !s2.ok) {
    return;
  }

  // Format CSV packet
  char buffer[160];
  snprintf(buffer, sizeof(buffer),
    "%.4f,%.4f,%.4f,%.2f,%.2f,%.2f,%.4f,%.4f,%.4f,%.2f,%.2f,%.2f",
    s1.ax, s1.ay, s1.az, s1.gx, s1.gy, s1.gz,
    s2.ax, s2.ay, s2.az, s2.gx, s2.gy, s2.gz
  );

  // 1. Output to Serial (USB cable debugging)
  Serial.println(buffer);

  // 2. Transmit over Wi-Fi to Flask Web Server
  if (WiFi.status() == WL_CONNECTED) {
#if STREAM_MODE == 1
    // UDP Streaming (Zero latency)
    udpClient.beginPacket(SERVER_IP, UDP_PORT);
    udpClient.write((const uint8_t*)buffer, strlen(buffer));
    udpClient.endPacket();
#else
    // HTTP POST streaming (Fallback)
    static int httpThrottle = 0;
    if (++httpThrottle >= 3) { // Send every ~60ms
      httpThrottle = 0;
      HTTPClient http;
      String url = String("http://") + SERVER_IP + ":" + String(HTTP_PORT) + "/api/esp32/stream";
      http.begin(url);
      http.addHeader("Content-Type", "text/plain");
      http.POST(buffer);
      http.end();
    }
#endif
  }
}
