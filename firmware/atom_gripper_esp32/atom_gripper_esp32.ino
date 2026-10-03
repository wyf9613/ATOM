// Sensor telemetry and gated STS position-mode commissioning.
#include <Wire.h>
#include <Adafruit_MLX90393.h>
#include "board_config.h"
#include "motor_control.h"

Adafruit_MLX90393 sensor;
bool ready = false;
bool initialisationAttempted = false;
uint32_t sequence = 0;
uint32_t lastSample = 0;
uint32_t lastRetry = 0;
AtomMotor motor;

void initialiseSensor() {
  // Installed Adafruit driver has a dangling-pointer bug on repeated begin_I2C.
  // Call it at most once per boot; wait for address ACK before the first call.
  if (initialisationAttempted) return;
  bool addressFound = false;
  uint8_t foundCount = 0;
  Serial.printf("# scan SDA=%d SCL=%d; line_levels=%d,%d\n",
                ATOM_SDA_PIN, ATOM_SCL_PIN,
                digitalRead(ATOM_SDA_PIN), digitalRead(ATOM_SCL_PIN));
  for (uint8_t address = 1; address < 127; ++address) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0) {
      ++foundCount;
      Serial.printf("# i2c_ack=0x%02X\n", address);
      if (address == ATOM_SENSOR_ADDRESS) addressFound = true;
    }
  }
  if (!addressFound) {
    Serial.printf("# expected_address=0x%02X missing; devices=%u; check wiring/address\n",
                  ATOM_SENSOR_ADDRESS, foundCount);
    return;
  }
  initialisationAttempted = true;
  ready = sensor.begin_I2C(ATOM_SENSOR_ADDRESS, &Wire);
  if (ready) {
    ready = sensor.setGain(MLX90393_GAIN_1X) &&
            sensor.setResolution(MLX90393_X, MLX90393_RES_16) &&
            sensor.setResolution(MLX90393_Y, MLX90393_RES_16) &&
            sensor.setResolution(MLX90393_Z, MLX90393_RES_16) &&
            sensor.setOversampling(MLX90393_OSR_3) &&
            sensor.setFilter(MLX90393_FILTER_5);
  }
  Serial.println(ready ? "# sensor_ready" : "# sensor_init_failed; press EN after checking hardware");
}

void setup() {
  Serial.begin(115200);
  // VIN is a physical power rail, not a GPIO; firmware cannot enable/test it.
  motor.begin();
  Wire.begin(ATOM_SDA_PIN, ATOM_SCL_PIN);
  Wire.setClock(100000);
  Wire.setTimeOut(50);
  Serial.println("# ATOM_MAG_V1 units=uT; motor_boot_disarmed");
  // Acknowledgement proves bus presence, not chip identity.
  initialiseSensor();
}

void loop() {
  motor.poll();
  const uint32_t now = millis();
  if (!ready && !initialisationAttempted && (uint32_t)(now - lastRetry) >= 2000) {
    lastRetry = now;
    initialiseSensor();
  }
  if ((uint32_t)(now - lastSample) < 100) return;
  lastSample = now;
  float x = 0, y = 0, z = 0;
  const bool valid = ready && sensor.readData(&x, &y, &z);
  motor.sensorSample(valid,x,y,z);
  // V1,sequence,device_ms,address,valid,Bx_uT,By_uT,Bz_uT
  if (motor.streamEnabled()) Serial.printf("V1,%lu,%lu,%u,%u,%.6f,%.6f,%.6f\n",
                (unsigned long)sequence, (unsigned long)millis(),
                ATOM_SENSOR_ADDRESS, valid ? 1 : 0, x, y, z);
  ++sequence;
  if (!valid && ready) {
    ready = false;
    Serial.println("# sensor_read_failed; press EN after checking hardware");
  }
}
