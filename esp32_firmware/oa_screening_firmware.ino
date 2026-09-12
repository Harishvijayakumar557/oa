/*
  OA Screening Firmware for ESP32 + 2x MPU6050
  Reads thigh and lower-leg sensors at 50 Hz, formats CSV output, and
  transmits sensor samples to a Python host over Serial.

  Output format:
  ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2

  Disclaimer: ⚠️ For screening only, not medical diagnosis.
*/

#include <Wire.h>

#define SDA_PIN 21
#define SCL_PIN 22
#define MPU_ADDR_1 0x68
#define MPU_ADDR_2 0x69
#define REPORT_INTERVAL_MS 20  // 50 Hz

TwoWire I2C_0 = Wire;

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

  // Skip bad or hung reads gracefully.
  I2C_0.beginTransmission(addr);
  I2C_0.write(0x3B);
  uint8_t transmissionStatus = I2C_0.endTransmission(false);
  if (transmissionStatus != 0) {
    Serial.println("I2C transmit error");
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
  I2C_0.write(0x00);
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

void setup() {
  Serial.begin(115200);
  I2C_0.begin(SDA_PIN, SCL_PIN);
  I2C_0.setTimeOut(50);

  configureMPU(MPU_ADDR_1);
  configureMPU(MPU_ADDR_2);

  delay(200);
  Serial.println("READY");
  Serial.flush();
}

void loop() {
  SensorData s1 = readSensorData(MPU_ADDR_1);
  SensorData s2 = readSensorData(MPU_ADDR_2);

  // Skip malformed readings without blocking the stream.
  if (!s1.ok || !s2.ok) {
    delay(REPORT_INTERVAL_MS);
    return;
  }

  Serial.print(s1.ax, 6);
  Serial.print(",");
  Serial.print(s1.ay, 6);
  Serial.print(",");
  Serial.print(s1.az, 6);
  Serial.print(",");
  Serial.print(s1.gx, 6);
  Serial.print(",");
  Serial.print(s1.gy, 6);
  Serial.print(",");
  Serial.print(s1.gz, 6);
  Serial.print(",");

  Serial.print(s2.ax, 6);
  Serial.print(",");
  Serial.print(s2.ay, 6);
  Serial.print(",");
  Serial.print(s2.az, 6);
  Serial.print(",");
  Serial.print(s2.gx, 6);
  Serial.print(",");
  Serial.print(s2.gy, 6);
  Serial.print(",");
  Serial.print(s2.gz, 6);
  Serial.println();

  delay(REPORT_INTERVAL_MS);
}
