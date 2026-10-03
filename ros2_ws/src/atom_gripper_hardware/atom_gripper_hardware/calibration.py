"""Force-estimation extension point. Raw servo load is never converted to newtons."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ForceEstimate:
    force_n: Optional[float]
    calibrated: bool
    uncertainty_n: Optional[float]
    reason: str


class UncalibratedForceModel:
    def estimate(self, magnetic_uT, position):
        # //TODO G01: fit and independently validate Bx/By/Bz + geometry/position → contact force.
        # Record sensor/magnet identity, force direction, calibration range, hysteresis and uncertainty.
        return ForceEstimate(None, False, None, 'Fingertip force calibration pending')
