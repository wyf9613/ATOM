#pragma once
// Must confirm actual STS3215/URT-1, 3.3V UART compatibility and servo power.
// UART enabled for commissioning; explicit ARM and configured feedback gates still apply.
#ifndef ATOM_MOTOR_ENABLED
#define ATOM_MOTOR_ENABLED 1
#endif
#ifndef ATOM_MOTOR_HARDWARE_CONFIRMED
#define ATOM_MOTOR_HARDWARE_CONFIRMED 1 // User STS3215; successful mode/feedback query, 2026-10-03.
#endif
#ifndef ATOM_MOTOR_ID
#define ATOM_MOTOR_ID 1       // Confirmed PING. Never broadcast.
#endif
#ifndef ATOM_MOTOR_BAUD
#define ATOM_MOTOR_BAUD 1000000 // Confirmed PING.
#endif
#ifndef ATOM_MOTOR_MIN_POSITION
//TODO G02: repeat endpoint measurements under load; map encoder counts to measured jaw opening (mm).
#define ATOM_MOTOR_MIN_POSITION 1937 // Observed tight=1917; provisional inward margin=20.
#endif
#ifndef ATOM_MOTOR_MAX_POSITION
#define ATOM_MOTOR_MAX_POSITION 2668 // Observed open=2688; provisional inward margin=20.
#endif
#ifndef ATOM_MOTOR_OPEN_POSITION
#define ATOM_MOTOR_OPEN_POSITION 2668
#endif
#ifndef ATOM_MOTOR_CLOSED_POSITION
#define ATOM_MOTOR_CLOSED_POSITION 1937
#endif
#ifndef ATOM_MOTOR_SPEED
//TODO G03: verify speed/acceleration register units and measure stopping distance/latency.
#define ATOM_MOTOR_SPEED 20   // SDK speed register value; physical units unverified (~100counts/2.1s observed).
#endif
#ifndef ATOM_MOTOR_ACCELERATION
#define ATOM_MOTOR_ACCELERATION 10
#endif
#ifndef ATOM_MOTOR_MAX_LOAD
//TODO G03: validate load/voltage/temperature limits for this exact servo and duty cycle; raw load is not N.
#define ATOM_MOTOR_MAX_LOAD 80 // Provisional post-lubrication test threshold; prior50 tripped at52. NOT calibrated force protection.
#endif
#ifndef ATOM_MOTOR_MIN_VOLTAGE
#define ATOM_MOTOR_MIN_VOLTAGE 72 // Provisional narrow range around observed 76/77; raw units.
#endif
#ifndef ATOM_MOTOR_MAX_VOLTAGE
#define ATOM_MOTOR_MAX_VOLTAGE 82
#endif
#ifndef ATOM_MOTOR_MAX_TEMPERATURE
#define ATOM_MOTOR_MAX_TEMPERATURE 40 // Provisional first-test abort threshold.
#endif
#ifndef ATOM_GRIP_DELTA_UT
//TODO G01/G04: calibrate fingertip force and implement bounded local force feedback before enabling force close.
#define ATOM_GRIP_DELTA_UT -1.0f // Magnetic change threshold needs calibration.
#endif
#ifndef ATOM_MOTOR_JOG_ONLY
#define ATOM_MOTOR_JOG_ONLY 1 // Manual +/-100 counts only; no full opening/closing.
#endif
#ifndef ATOM_MOTOR_MOTION_TIMEOUT_MS
#define ATOM_MOTOR_MOTION_TIMEOUT_MS 7000UL // Provisional bound; measured100count moves ~2.1s, not stop-latency guarantee.
#endif
#ifndef ATOM_MOTOR_POSITION_TOLERANCE
#define ATOM_MOTOR_POSITION_TOLERANCE 3 // Observed stable 2-count residual; encoder tolerance, not physical accuracy.
#endif
