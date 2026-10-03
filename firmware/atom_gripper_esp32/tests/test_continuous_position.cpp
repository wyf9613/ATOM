#define ATOM_MOTOR_MIN_POSITION 1937
#define ATOM_MOTOR_MAX_POSITION 2668
#define ATOM_MOTOR_OPEN_POSITION 2600
#define ATOM_MOTOR_CLOSED_POSITION 2000
#define main legacy_motor_tests
#include "test_motor_control.cpp"
#undef main

int main() {
  SMS_STS::position=2300; SMS_STS::torque=0; SMS_STS::fail=false;
  SMS_STS::rawLoad=10; Serial.output.clear(); clockMs=0;
  AtomMotor motor; motor.begin(); motor.sensorSample(true,0,0,0);
  command(motor,"ARM"); int before=SMS_STS::writes;
  command(motor,"MOVE 1999"); command(motor,"MOVE 2601");
  assert(SMS_STS::writes==before);
  command(motor,"MOVE 2600");
  assert(SMS_STS::writes==before+1); assert(SMS_STS::lastTarget()==2600);
  // Full moves must survive the former 7-second jog timeout, while the
  // independent heartbeat and sensor gates remain actively serviced.
  for (int i=0;i<90;++i) {
    clockMs+=100; motor.sensorSample(true,0,0,0); command(motor,"KEEPALIVE");
  }
  assert(!printed("motion_timeout")); assert(!printed("FAULT"));
  SMS_STS::position=2400; command(motor,"STOP");
  assert(SMS_STS::lastTarget()==2400); Serial.output.clear();
  command(motor,"CLOSE"); assert(SMS_STS::lastTarget()==2000);
  assert(printed("MOVE_START")); assert(!printed("FAULT"));
  assert(!printed("ARM_OK")); assert(SMS_STS::torque==1);
  SMS_STS::position=2002; clockMs+=110;
  motor.sensorSample(true,0,0,0); command(motor,"KEEPALIVE");
  assert(printed("MOVE_DONE target=2000 pos=2002"));
  command(motor,"OPEN"); assert(SMS_STS::lastTarget()==2600);
  puts("continuous position/stop/resume regression passed");
}
