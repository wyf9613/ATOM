#include <cassert>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <string>
#include <stdint.h>
static uint32_t clockMs=0;
uint32_t millis() { return clockMs; }
struct SerialMock {
  std::string input,output;
  int available() { return input.size(); }
  char read() { char c=input[0]; input.erase(0,1); return c; }
  void println(const char *s) { output+=s; output+='\n'; }
  template<class... A> void printf(const char *s,A... args) {
    char b[512]; snprintf(b,sizeof(b),s,args...); output+=b;
  }
} Serial;
struct HardwareSerial { HardwareSerial(int) {} void begin(int,int,int,int) {} };
#define SERIAL_8N1 0
#define ATOM_SERVO_RX_PIN 16
#define ATOM_SERVO_TX_PIN 17
#define ATOM_MOTOR_ENABLED 1
#define ATOM_MOTOR_JOG_ONLY 0
#define ATOM_MOTOR_HARDWARE_CONFIRMED 1
#ifndef ATOM_MOTOR_MIN_POSITION
#define ATOM_MOTOR_MIN_POSITION 100
#endif
#ifndef ATOM_MOTOR_MAX_POSITION
#define ATOM_MOTOR_MAX_POSITION 1000
#endif
#ifndef ATOM_MOTOR_OPEN_POSITION
#define ATOM_MOTOR_OPEN_POSITION 200
#endif
#ifndef ATOM_MOTOR_CLOSED_POSITION
#define ATOM_MOTOR_CLOSED_POSITION 900
#endif
#define ATOM_MOTOR_MAX_LOAD 100
#define ATOM_MOTOR_MIN_VOLTAGE 60
#define ATOM_MOTOR_MAX_VOLTAGE 84
#define ATOM_GRIP_DELTA_UT 50.0f
#include "../motor_control.h"
int SMS_STS::position=500; int SMS_STS::torque=0; int SMS_STS::writes=0; int SMS_STS::rawLoad=10; bool SMS_STS::fail=false;
void command(AtomMotor &m,const char *s) { Serial.input=std::string(s)+"\n"; m.poll(); }
bool printed(const char *s) { return Serial.output.find(s)!=std::string::npos; }
int main() {
  AtomMotor m; m.begin(); assert(SMS_STS::writes==0); // No servo boot packets.
  assert(!m.streamEnabled()); command(m,"STREAM ON"); assert(m.streamEnabled());
  command(m,"STREAM OFF"); assert(!m.streamEnabled()); assert(SMS_STS::writes==0);
  command(m,"OPEN"); assert(SMS_STS::writes==0);
  command(m,"ARM"); assert(SMS_STS::writes==0); // No sensor.
  m.sensorSample(true,0,0,0); command(m,"ARM"); assert(printed("ARM_OK"));
  int before=SMS_STS::writes;
  command(m,"JOG 101"); assert(SMS_STS::writes==before);
  command(m,"CLOSE"); assert(SMS_STS::writes==before+1); // Position close needs no force baseline.
  command(m,"STOP"); before=SMS_STS::writes;
  command(m,"JOG 5"); assert(SMS_STS::writes==before+1);
  clockMs=800; m.sensorSample(true,0,0,0); m.poll(); assert(printed("host_timeout"));
  before=SMS_STS::writes; command(m,"ARM"); assert(SMS_STS::writes==before); // Latched.
  command(m,"DISARM"); command(m,"RESET"); assert(printed("RESET_OK"));
  command(m,"ZERO"); m.sensorSample(false,0,0,0);
  Serial.output.clear(); for(int i=0;i<20;++i) m.sensorSample(true,0,0,0);
  assert(!printed("ZERO_OK")); // Failed sample cancels incomplete calibration.
  command(m,"ZERO"); for(int i=0;i<20;++i) m.sensorSample(true,0,0,0);
  assert(printed("ZERO_OK")); command(m,"ARM"); command(m,"CLOSE");
  clockMs=910; m.sensorSample(true,100,0,0); command(m,"KEEPALIVE"); m.poll();
  command(m,"STOP");
  assert(printed("STOP position_hold"));
  SMS_STS::fail=true; command(m,"OPEN"); assert(printed("move_feedback_or_limit"));
  assert(printed("hold_unconfirmed_external_stop_required"));
  assert(printed("FEEDBACK_ERROR result=-1 sdk_error=1"));
  SMS_STS::fail=false; SMS_STS::torque=0; Serial.output.clear();
  AtomMotor limits; limits.begin(); limits.sensorSample(true,0,0,0); command(limits,"ARM");
  command(limits,"JOG 50");
  SMS_STS::rawLoad=-101; clockMs+=110; limits.sensorSample(true,0,0,0); command(limits,"KEEPALIVE");
  assert(printed("LIMIT_ERROR")); assert(printed("flags_pos_load_voltage_temp=0,1,0,0"));
  assert(printed("FAULT_TRIGGER reason=servo_limit_exceeded"));
  assert(printed("load_raw=-101"));
  assert(printed("MOTION_SUMMARY result=servo_limit_exceeded"));
  assert(printed("peak_abs_load=101 peak_signed_load=-101"));
  SMS_STS::torque=0; SMS_STS::rawLoad=10; SMS_STS::position=500; Serial.output.clear();
  AtomMotor arrival; arrival.begin(); arrival.sensorSample(true,0,0,0); command(arrival,"ARM"); command(arrival,"JOG 50");
  clockMs+=110; SMS_STS::position=546; arrival.sensorSample(true,0,0,0); command(arrival,"KEEPALIVE");
  assert(!printed("MOVE_DONE"));
  clockMs+=110; SMS_STS::position=548; arrival.sensorSample(true,0,0,0); command(arrival,"KEEPALIVE");
  assert(printed("MOVE_DONE target=550 pos=548"));
  puts("motor state regression passed");
  return 0;
}
