#include "../motor_policy.h"
#include <assert.h>
int main() {
  int target;
  assert(!atom::limitsValid(-1,-1));
  assert(!atom::limitsValid(0,4096));
  assert(atom::jogTarget(100,20,90,130,target) && target==120);
  assert(!atom::jogTarget(100,-20,90,130,target));
  assert(atom::jogTarget(200,100,0,4095,target) && target==300);
  assert(atom::jogTarget(200,-100,0,4095,target) && target==100);
  assert(!atom::jogTarget(200,101,0,4095,target));
  assert(!atom::jogTarget(200,-101,0,4095,target));
  assert(!atom::jogTarget(2600,100,1937,2668,target));
  assert(!atom::jogTarget(100,0,0,4095,target));
  assert(!atom::targetAllowed(89,100,90,130));
  assert(atom::timedOut(100,0xfffffff0U,100));
  assert(!atom::timedOut(50,0xfffffff0U,100));
}
