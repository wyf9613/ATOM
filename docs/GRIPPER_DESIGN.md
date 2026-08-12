# Inherited Gripper Design

## Reported configuration

- Two-finger parallel gripper with rack-and-pinion transmission.
- FeeTech STS3215 servo and STM32 Nucleo controller.
- Shore 20A silicone pads with embedded magnets and magnetic sensing.
- ROS-to-STM32 serial communication.
- Buckle-style quick-disconnect.
- Reported envelope: 225 x 105 x 131 mm.
- Reported total mass including STM32: 580 g.
- Reported production cost: under AUD 200.

These values come from the previous report and require measurement on the inherited physical unit.

## Previous experiment

- Platform: university UR3e, not the proposed future commercial arm.
- Workcell: two simplified cuvette holders secured on a table.
- Motion: manually tuned fixed waypoints.
- Result: 49/50 complete cycles; the failed trial followed incorrect manual cuvette placement.
- One-cycle time: 25.3 s.
- Real-instrument insertion and grip force were not verified.

## Reported tuning values

| Parameter | Reported final value | Confidence |
|---|---:|---|
| Waypoint wait time | 5 s | Table value |
| Drop speed | 50 | Table value; device units not documented here |
| Magnetic-field threshold | 500 | Table value; sensor units not documented here |
| Load-detection delay | 500 ms | Table value |
| Load threshold | 240 | Table value; device units not documented here |
| Gripper speed | 200 in Table 2; 180 in surrounding text | Conflict - confirm from firmware |

Do not copy these values into production configuration until the original firmware and servo conventions are recovered.

## Known design risks

- No timeout or maximum travel limit; an empty grasp can close until the silicone pads compress together.
- Magnetic threshold is not a calibrated force measurement.
- High silicone friction can make the cuvette stick during release; tape was used as a temporary workaround.
- Transient high load at speed can occur before braking and trigger the software stop.
- Debug serial printing added control-loop latency.
- STM32 holder extends below the gripper and can reduce table clearance.
- Bonded silicone pads and magnets may detach or shift with repeated use.
- Printed buckle surfaces can wear and reduce mount repeatability.
- Steel shafts add avoidable mass.

## Required initial tests

1. Photograph and identify the actual as-received configuration.
2. Measure envelope, mass, finger range, mounting transform and candidate TCP.
3. Recover firmware and map all servo/sensor units.
4. Test calibration repeatability and hard/soft travel limits at reduced speed.
5. Calibrate magnetic readings against an independent force reference.
6. Characterise object-present, empty-grasp, slip and release detection.
7. Quantify quick-disconnect translational and angular repeatability.

