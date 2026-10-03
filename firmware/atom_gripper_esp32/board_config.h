#pragma once
// User photographs, 2026-10-02: ESP32 DEVKIT V1, classic ESP32, CP2102.
#define ATOM_SDA_PIN 21
#define ATOM_SCL_PIN 22
// User serial screenshot, 2026-10-02: repeated I2C ACK at 0x14.
// Initialization and valid samples observed; chip identity remains provisional.
#define ATOM_SENSOR_ADDRESS 0x14

// Migrated wiring. UART remains disabled until interface voltage is verified.
#define ATOM_SERVO_RX_PIN 16
#define ATOM_SERVO_TX_PIN 17
// Motor enable/baud/limits are managed separately in motor_config.h.
