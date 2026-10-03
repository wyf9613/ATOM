#pragma once
#include "motor_config.h"
#include "motor_policy.h"
#if ATOM_MOTOR_ENABLED
#include <SCServo.h>
#endif
#include <math.h>

// STS position-mode commissioning only. No wheel-mode or EEPROM writes.
class AtomMotor {
public:
  bool streamEnabled() const { return stream; }
  void begin() {
#if ATOM_MOTOR_ENABLED
    uart.begin(ATOM_MOTOR_BAUD, SERIAL_8N1, ATOM_SERVO_RX_PIN, ATOM_SERVO_TX_PIN);
    servo.pSerial = &uart;
    servo.IOTimeOut = 15;
#endif
    Serial.println("# motor commands: STATUS PING ARM DISARM RESET STOP KEEPALIVE ZERO JOG <counts> MOVE <position> OPEN CLOSE STREAM ON/OFF");
    status();
  }
  void sensorSample(bool valid, float x, float y, float z) {
    //TODO G01: validate force model and temperature/hysteresis compensation; ZERO only removes magnetic baseline.
    sensorOK = valid;
    if (!valid) { zeroCount=0; baselineOK=false; if (armed) fault("sensor_invalid"); return; }
    sensorTime = millis();
    bx = x; by = y; bz = z;
    if (zeroCount > 0) {
      zeroX += x; zeroY += y; zeroZ += z;
      if (--zeroCount == 0) {
        zeroX /= 20; zeroY /= 20; zeroZ /= 20;
        baselineOK = true;
        Serial.println("# ZERO_OK magnetic_baseline_only_not_force");
      }
    }
  }
  void poll() {
    //TODO G05: physically measure watchdog/fault hold behavior and power-loss behavior with an object.
    // USB parser is bounded. No arbitrary pass-through to servo UART.
    for (int n=0; n<64 && Serial.available(); ++n) {
      char c = Serial.read();
      if (c == '\r') continue;
      if (c == '\n') {
        if (!overflow) { command[length] = 0; execute(command); }
        else { Serial.println("# ERR command_overflow"); if (armed) fault("command_overflow"); }
        length = 0; overflow = false;
      } else if (length < sizeof(command)-1 && !overflow) command[length++] = c;
      else overflow = true;
    }
    const uint32_t now = millis();
    if (armed && atom::timedOut(now, heartbeat, 750)) fault("host_timeout");
    if (armed && (!sensorOK || atom::timedOut(now, sensorTime, 350))) fault("sensor_stale");
#if ATOM_MOTOR_ENABLED
    if (armed && atom::timedOut(now, lastFeedback, 100)) {
      lastFeedback = now;
      if (!feedback()) fault("servo_feedback_failed");
      else { if (moving) traceSample(); if (!healthOK()) fault("servo_limit_exceeded"); }
      if (moving && armed) {
        if (closing && baselineOK && magneticDelta() >= ATOM_GRIP_DELTA_UT) stopMotion();
        else if (abs(position-target) <= ATOM_MOTOR_POSITION_TOLERANCE) { traceEnd("done"); moving=false; closing=false; Serial.printf("# MOVE_DONE target=%d pos=%d load_raw=%d voltage_raw=%d temp_raw=%d\n",target,position,load,voltage,temperature); }
        else if (atom::timedOut(now, motionStart, ATOM_MOTOR_MOTION_TIMEOUT_MS)) fault("motion_timeout");
      }
    }
#endif
  }
private:
  bool stream=!ATOM_MOTOR_ENABLED; // Quiet motor commissioning; sensor-only build streams.
  bool armed=false, moving=false, closing=false, latched=false, sensorOK=false;
  bool baselineOK=false, overflow=false;
  char command[64]; unsigned length=0;
  int position=-1, load=0, voltage=0, temperature=0, mode=-1, target=-1;
  int zeroCount=0;
  bool traceActive=false;
  int startPosition=0, peakAbsLoad=0, peakSignedLoad=0;
  unsigned motionSamples=0;
  float bx=0, by=0, bz=0, zeroX=0, zeroY=0, zeroZ=0;
  uint32_t sensorTime=0, heartbeat=0, lastFeedback=0, motionStart=0;
#if ATOM_MOTOR_ENABLED
  HardwareSerial uart{2}; SMS_STS servo;
  bool feedback() {
    int result=servo.FeedBack(ATOM_MOTOR_ID);
    int error=servo.getLastError(), state=servo.getState();
    if (result < 0 || error || state) {
      Serial.printf("# FEEDBACK_ERROR result=%d sdk_error=%d servo_state=%d previous_values_stale=1\n",result,error,state);
      return false;
    }
    position = servo.ReadPos(-1); load=servo.ReadLoad(-1);
    voltage=servo.ReadVoltage(-1); temperature=servo.ReadTemper(-1);
    return true;
  }
  bool ack(int result) { return result > 0 && !servo.getLastError() && !servo.getState(); }
  bool healthOK() {
    bool posOK=atom::targetAllowed(position,position,ATOM_MOTOR_MIN_POSITION,ATOM_MOTOR_MAX_POSITION);
    bool loadOK=abs(load)<=ATOM_MOTOR_MAX_LOAD;
    bool voltageOK=voltage>=ATOM_MOTOR_MIN_VOLTAGE && voltage<=ATOM_MOTOR_MAX_VOLTAGE;
    bool tempOK=temperature<=ATOM_MOTOR_MAX_TEMPERATURE;
    if (!posOK || !loadOK || !voltageOK || !tempOK)
      Serial.printf("# LIMIT_ERROR pos=%d range=%d..%d load_raw=%d max_abs=%d voltage_raw=%d range=%d..%d temp_raw=%d max=%d flags_pos_load_voltage_temp=%d,%d,%d,%d\n",
        position,ATOM_MOTOR_MIN_POSITION,ATOM_MOTOR_MAX_POSITION,load,ATOM_MOTOR_MAX_LOAD,
        voltage,ATOM_MOTOR_MIN_VOLTAGE,ATOM_MOTOR_MAX_VOLTAGE,temperature,ATOM_MOTOR_MAX_TEMPERATURE,
        !posOK,!loadOK,!voltageOK,!tempOK);
    return posOK && loadOK && voltageOK && tempOK;
  }
#endif
  bool configurationOK() {
    return ATOM_MOTOR_HARDWARE_CONFIRMED && ATOM_MOTOR_ID > 0 && ATOM_MOTOR_ID < 254 &&
           atom::limitsValid(ATOM_MOTOR_MIN_POSITION,ATOM_MOTOR_MAX_POSITION) &&
           ATOM_MOTOR_SPEED > 0 && ATOM_MOTOR_SPEED <= 100 &&
           ATOM_MOTOR_MAX_LOAD > 0 && ATOM_MOTOR_MIN_VOLTAGE > 0 &&
           ATOM_MOTOR_MAX_VOLTAGE > ATOM_MOTOR_MIN_VOLTAGE;
  }
  float magneticDelta() { return sqrtf((bx-zeroX)*(bx-zeroX)+(by-zeroY)*(by-zeroY)+(bz-zeroZ)*(bz-zeroZ)); }
  void traceSample() {
    ++motionSamples;
    if (abs(load)>peakAbsLoad) { peakAbsLoad=abs(load); peakSignedLoad=load; }
    Serial.printf("# MOTION ms=%lu elapsed_ms=%lu start=%d target=%d pos=%d load_raw=%d voltage_raw=%d temp_raw=%d\n",
      (unsigned long)millis(),(unsigned long)(millis()-motionStart),startPosition,target,position,load,voltage,temperature);
  }
  void traceEnd(const char *result) {
    if (!traceActive) return;
    Serial.printf("# MOTION_SUMMARY result=%s start=%d target=%d last_pos=%d samples=%u peak_abs_load=%d peak_signed_load=%d elapsed_ms=%lu\n",
      result,startPosition,target,position,motionSamples,peakAbsLoad,peakSignedLoad,(unsigned long)(millis()-motionStart));
    traceActive=false;
  }
  void status() {
    Serial.printf("# MOTOR enabled=%d configured=%d armed=%d moving=%d fault=%d id=%d baud=%lu pos=%d load_raw=%d voltage_raw=%d temp_raw=%d continuous_position=%d\n",
      ATOM_MOTOR_ENABLED,configurationOK(),armed,moving,latched,ATOM_MOTOR_ID,
      (unsigned long)ATOM_MOTOR_BAUD,position,load,voltage,temperature,!ATOM_MOTOR_JOG_ONLY);
  }
  void stopMotion() {
    traceEnd("stop_requested");
#if ATOM_MOTOR_ENABLED
    // Best-effort position hold, NOT power cut or hardware emergency stop.
    if (armed) {
      if (!feedback() || !ack(servo.WritePosEx(ATOM_MOTOR_ID,position,ATOM_MOTOR_SPEED,ATOM_MOTOR_ACCELERATION))) {
        latched=true; armed=false; Serial.println("# FAULT hold_unconfirmed_external_stop_required");
      }
    }
#endif
    moving=false; closing=false;
    Serial.println("# STOP position_hold_requested_not_estop");
  }
  void fault(const char *reason) {
    if (latched) return;
    latched=true;
    Serial.printf("# FAULT_TRIGGER reason=%s target=%d\n",reason,target);
    traceEnd(reason);
    status(); // Capture trigger values BEFORE stopMotion reads feedback again.
    stopMotion(); armed=false; zeroCount=0;
    Serial.printf("# FAULT %s latched; torque_may_remain_enabled\n",reason);
  }
  void moveTo(int requested, bool grip) {
#if ATOM_MOTOR_ENABLED
    if (!armed || latched || moving) { Serial.println("# ERR move_gate"); return; }
    if (!feedback() || !healthOK()) { fault("move_feedback_or_limit"); return; }
    if (!atom::targetAllowed(position,requested,ATOM_MOTOR_MIN_POSITION,ATOM_MOTOR_MAX_POSITION)) {
      Serial.println("# ERR move_gate"); return;
    }
    if (grip && (!baselineOK || zeroCount || ATOM_GRIP_DELTA_UT <= 0)) { Serial.println("# ERR magnetic_threshold_unconfigured"); return; }
    if (!ack(servo.WritePosEx(ATOM_MOTOR_ID,requested,ATOM_MOTOR_SPEED,ATOM_MOTOR_ACCELERATION))) {
      fault("move_ack_failed"); return;
    }
    target=requested; moving=true; closing=grip; motionStart=millis();
    startPosition=position; peakAbsLoad=0; peakSignedLoad=0; motionSamples=0; traceActive=true;
    Serial.printf("# MOVE_START start=%d target=%d delta=%d speed=%d\n",startPosition,target,target-startPosition,ATOM_MOTOR_SPEED);
    traceSample();
#endif
  }
  void execute(const char *text) {
    if (!strcmp(text,"STREAM ON")) { stream=true; Serial.println("# STREAM ON"); return; }
    if (!strcmp(text,"STREAM OFF")) { stream=false; Serial.println("# STREAM OFF sampling_continues"); return; }
    if (!strcmp(text,"STATUS")) { status(); return; }
    if (!strcmp(text,"KEEPALIVE")) { heartbeat=millis(); return; }
    if (!strcmp(text,"STOP")) { stopMotion(); return; }
#if ATOM_MOTOR_ENABLED
    if (ATOM_MOTOR_ID < 1 || ATOM_MOTOR_ID >= 254) { Serial.println("# ERR invalid_id"); return; }
    if (!strcmp(text,"PING")) {
      if (armed) { Serial.println("# ERR disarm_before_ping"); return; }
      bool ok=servo.Ping(ATOM_MOTOR_ID)==ATOM_MOTOR_ID && !servo.getState() && !servo.getLastError();
      mode=servo.readByte(ATOM_MOTOR_ID,SMS_STS_MODE);
      bool readOK=!servo.getState() && !servo.getLastError();
      Serial.printf("# PING ok=%d mode=%d mode_read_ok=%d feedback_ok=%d\n",ok,mode,readOK,feedback()); status(); return;
    }
    if (!strcmp(text,"DISARM")) {
      traceEnd("disarm_requested");
      // Explicit operator release; can drop an object. Never called automatically.
      bool ok=ack(servo.EnableTorque(ATOM_MOTOR_ID,0));
      armed=false; moving=false; closing=false;
      if (!ok) { latched=true; Serial.println("# FAULT torque_off_unconfirmed"); }
      else Serial.println("# DISARM_OK torque_off"); return;
    }
    if (!strcmp(text,"RESET")) {
      if (armed || moving) { Serial.println("# ERR disarm_first"); return; }
      if (configurationOK() && feedback() && healthOK()) { latched=false; baselineOK=false; Serial.println("# RESET_OK"); }
      else Serial.println("# ERR reset_gate"); return;
    }
    if (!strcmp(text,"ARM")) {
      mode=servo.readByte(ATOM_MOTOR_ID,SMS_STS_MODE);
      bool modeOK=mode==0 && !servo.getState() && !servo.getLastError();
      if (latched || armed || !configurationOK() || !sensorOK ||
          atom::timedOut(millis(),sensorTime,350) || !modeOK || !feedback() || !healthOK()) {
        Serial.println("# ERR arm_gate_requires_verified_position_mode_config_sensor_feedback"); return;
      }
      // Refuse existing torque-on state: do not overwrite an unknown active goal.
      int torque=servo.readByte(ATOM_MOTOR_ID,SMS_STS_TORQUE_ENABLE);
      if (torque!=0 || servo.getState() || servo.getLastError()) { Serial.println("# ERR disarm_and_inspect_before_arm"); return; }
      if (!ack(servo.WritePosEx(ATOM_MOTOR_ID,position,ATOM_MOTOR_SPEED,ATOM_MOTOR_ACCELERATION)) ||
          !ack(servo.EnableTorque(ATOM_MOTOR_ID,1))) { latched=true; Serial.println("# FAULT arm_ack_failed_torque_state_unknown"); return; }
      armed=true; heartbeat=millis(); lastFeedback=millis(); Serial.println("# ARM_OK"); return;
    }
    if (!strcmp(text,"ZERO")) {
      if (armed || moving || !sensorOK) { Serial.println("# ERR zero_requires_disarmed_stationary_sensor"); return; }
      zeroCount=20; baselineOK=false; zeroX=zeroY=zeroZ=0; return;
    }
    int delta; char extra;
    int absolute;
    if (sscanf(text,"MOVE %d %c",&absolute,&extra)==1) {
      if (ATOM_MOTOR_JOG_ONLY || absolute < 2000 || absolute > 2600) {
        Serial.println("# ERR continuous_position_limit_or_disabled"); return;
      }
      moveTo(absolute,false); return;
    }
    if (sscanf(text,"JOG %d %c",&delta,&extra)==1) {
      int requested;
      if (!feedback() || !atom::jogTarget(position,delta,ATOM_MOTOR_MIN_POSITION,ATOM_MOTOR_MAX_POSITION,requested)) { Serial.println("# ERR jog_limit"); return; }
      moveTo(requested,false); return;
    }
    if (!strcmp(text,"OPEN")) { if (ATOM_MOTOR_JOG_ONLY) Serial.println("# ERR first_test_jog_only"); else moveTo(ATOM_MOTOR_OPEN_POSITION,false); return; }
    // Position-only closure. No contact/force/grasp success is implied.
    if (!strcmp(text,"CLOSE")) { if (ATOM_MOTOR_JOG_ONLY) Serial.println("# ERR first_test_jog_only"); else moveTo(ATOM_MOTOR_CLOSED_POSITION,false); return; }
#endif
    Serial.println("# ERR command_unknown_or_motor_disabled");
  }
};
