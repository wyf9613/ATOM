#pragma once
// Native test double only; not a device protocol implementation.
struct SMS_STS {
  void *pSerial=nullptr; int IOTimeOut=0;
  static int position, torque, writes, rawLoad; static bool fail;
  int FeedBack(int) { return fail ? -1 : 15; }
  int getLastError() { return fail; }
  int getState() { return 0; }
  int ReadPos(int) { return position; }
  int ReadLoad(int) { return rawLoad; }
  int ReadVoltage(int) { return 74; }
  int ReadTemper(int) { return 25; }
  int Ping(int id) { return id; }
  int readByte(int,int reg) { return reg==40 ? torque : 0; }
  static int &lastTarget() { static int target=-1; return target; }
  int WritePosEx(int,int target,int,int) { ++writes; lastTarget()=target; return !fail; }
  int EnableTorque(int,int value) { torque=value; ++writes; return !fail; }
};
#define SMS_STS_MODE 33
#define SMS_STS_TORQUE_ENABLE 40
