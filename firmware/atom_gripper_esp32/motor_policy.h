#pragma once
#include <stdint.h>
namespace atom {
inline bool limitsValid(int low, int high) {
  return low >= 0 && low < high && high <= 4095;
}
inline bool targetAllowed(int position, int target, int low, int high) {
  return limitsValid(low, high) && position >= low && position <= high &&
         target >= low && target <= high;
}
inline bool timedOut(uint32_t now, uint32_t last, uint32_t limit) {
  return (uint32_t)(now - last) > limit;
}
inline bool jogTarget(int position, int delta, int low, int high, int &target) {
  if (delta == 0 || delta < -100 || delta > 100) return false;
  target = position + delta;
  return targetAllowed(position, target, low, high);
}
}
