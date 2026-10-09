# Intel RealSense D435i: model, simulation and camera-only commissioning

2026-10-07. User confirms physical model D435i. Serial, firmware, USB mode,
actual bracket/screw transform, payload and hand-eye calibration are unresolved.

## Dependency choice and model

Reuse D-007 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic. Install official ROS
repository releases in the project Docker image:

- realsense2_description 4.58.4-1noble.20260921.000124
- realsense2_camera 4.58.4-1noble.20260920.235447
- librealsense2 2.58.4-1noble.20260831.015923
- camera_calibration 5.0.13-1noble.20260912.164100

Model is imported from the installed official package, not copied or reconstructed.
Upstream: https://github.com/realsenseai/realsense-ros ; D435i uses the D435 case
mesh and adds IMU frames. ATOM package `atom_camera_description` wraps this model.
No ATOM camera node was added: use the vendor camera runtime boundary and existing
perception/GUI modules. Camera-only check scripts are thin read-only acceptance.

`uf850_atom.urdf.xacro camera_enabled:=true` mounts it to tool_flange. Default
mount xyz [0,-0.075,0.140] m, rpy [pi/2,-pi/2,0] rad means **bottom screw frame**,
not optical centre. This carries forward the reserved simulation position and
is not a measured bracket fit. Official offsets place depth/color/IMU frames.
The -90 degree tool clocking applies to camera and bracket together. Mount and
camera aim require physical confirmation before arm motion. The upstream box is
used for collision; its supplied inertial values are explicitly unreliable in
upstream source and must not configure physical payload.

Sim: camera_nominal_extrinsics:=true. Hardware: leave this false, so robot TF
publishes mount/body only and the driver owns calibrated internal camera TF.
Do not publish nominal and hardware extrinsics simultaneously. Camera support
currently uses unprefixed wrist_camera names: one mounted camera per ROS graph.

## Simulation

```bash
./scripts/atom.sh sim --camera depth --recipe visual_observe --gui --restart
python3 tests/operator_gui/tube_workflow_check.py --require-success
```

Gazebo Harmonic native RGB-D sensor + ros_gz bridge are the simulation stack,
not a librealsense device emulator. The virtual sensor sits at official color
frame, with the compatibility wrist_camera_optical_frame alias. Existing 640x480,
10 Hz, 60 degree horizontal FOV and 0.08–2 m clip are experiment settings, not
measured D435i intrinsics/range. Registered depth shares the color optical pose;
this does not model native stereo depth, projector, IR images, SDK alignment
error, transparent-object failures, IMU output or noise. IMU links exist, but no
simulated IMU samples are claimed. No Gazebo Classic plugin is installed.

## Camera-only physical bringup

Build image once (`docker compose -f docker-compose.jazzy.yaml build atom-jazzy`).
Connect USB3. Commands run on domain 43 by default; no arm launch or motion.

```bash
tools/camera/d435i.sh enumerate
tools/camera/d435i.sh start CAMERA_SERIAL
# second terminal
tools/camera/d435i.sh check
# third terminal: Ctrl+C finishes bag
tools/camera/d435i.sh record
```

The USB operations use a root container with USB bus access, not --privileged,
no host package/udev/kernel/firmware modification. They expose attached USB devices
to this camera container. Pass the confirmed serial to select the device. Check
USB access on host if enumeration fails; do not change firmware automatically.
Driver streams 640x480 at 30 Hz color/depth, aligned depth-to-color, gyro/accel
and interpolated IMU; verify actual supported profiles from enumeration. SDK
and ROS wrapper are distinct from ROS bag record/playback.

Topics under /atom/wrist_camera: color/image_raw, color/camera_info,
aligned_depth_to_color/image_raw, aligned_depth_to_color/camera_info, imu.
The checker requires these streams, matching frames/resolutions, positive camera
intrinsics and finite depth; records counts and timestamp residuals. Its 50 ms
nearest-color gate is provisional, not measured hardware tolerance. Report is
`tmp/camera_calibration/d435i_check.json`. Failure is not converted to success.
Native raw depth is also recorded; do not pass it as registered color depth.
Physical aligned depth commonly uses 16UC1 millimetres, unlike the simulation's
32FC1 metres. The visual task observer currently accepts 32FC1 only: an explicit,
validated unit/encoding adaptation and hardware task/safety bringup are still
required before using physical data for arm motion. GUI preview supports both.

## Calibration and staged acceptance

1. Record camera serial, firmware, wrapper/SDK versions, USB2/USB3, negotiated
   profiles, exposure/lighting, warm-up duration, mounting photo and cable route.
   Measure screw insertion depth, rigidity, clearance and camera/body payload.
2. Save factory color/depth CameraInfo and driver extrinsics from the bag. Keep
   them as baseline. Verify color intrinsics using a measured checkerboard;
   record inner-corner dimensions, square size in metres, image resolution and
   independent held-out reprojection errors. Do not overwrite device factory
   calibration or run device self-calibration automatically.
   Example inside the camera domain (replace SIZE and SQUARE_M with measurements):
   `ros2 run camera_calibration cameracalibrator --size SIZE --square SQUARE_M
   --no-service-check --ros-args -r image:=/atom/wrist_camera/color/image_raw
   -r camera:=/atom/wrist_camera/color`.
3. Test opaque planar targets at measured distances/angles over the intended
   workspace. Record conditions, independent reference uncertainty, >=30 frames
   per condition, valid-pixel fraction, bias, RMSE, spread, timestamp alignment
   and stationary IMU gravity/gyro bias. Repeat with lighting/reflective and
   transparent labware; transparent depth is not accepted as ground truth.
4. Eye-in-hand calibration: rigid measured target, stationary captured robot
   joint/TF and synchronized images over diverse rotations/translations. Collect
   manually supervised poses only after arm commissioning. Solve camera-to-eef
   using OpenCV calibrateHandEye from measured pairs; reject stale TF/frames.
   Save algorithm, transform direction, units, samples and version. Validate on
   held-out poses against measured target location; report translation and
   angular residuals and uncertainty. Nominal CAD is not a substitute.
5. Replace camera_mount_xyz/rpy with measured screw/body mounting, preserving
   calibrated driver internal frames. Check no duplicate TF parents. Revalidate
   known collision rejection and all planned paths with camera/cable envelope.
   Only then enable the separately commissioned hardware task/motion boundary.

Prepared commands and procedures are not physical calibration results.

Offline solver: `tools/camera/calibrate_hand_eye.py measured_pairs.json --output
calibration_result.json` in the ROS image/Python with OpenCV and numpy. Input
JSON `samples` contains 4x4 `base_from_eef` and `camera_from_target` matrices
(column vectors, translations in metres), plus explicit `holdout_indices`.
At least eight training poses and diverse rotations are required. Output is
`eef_from_camera`, held-out stationary-target consistency residuals and software
version. It never marks hardware accepted or installs a transform automatically.
Residuals use the first training target as reference; independent measured
reference validation and uncertainty assessment remain necessary.

The hardware wrapper also maps existing Intel USB-associated video/HID nodes
for SDKs using the native V4L2 backend. Recreate the container after USB reconnect
if device node names change. It does not install host udev rules or force a
kernel/firmware update.

## Verification on 2026-10-07

Image build completed. Four ATOM packages built; nine tests passed (four D435i
model/TF/sensor/collision regressions, two synthetic hand-eye cases, three
existing arm description checks). dpkg confirms the exact versions listed above.
Runtime official D435i mesh path exists and runtime combined URDF passes
check_urdf. Depth visual_observe run_20261007_034304 succeeded, detecting rack
Tags 0/1/2/3. GUI/API check --require-success passed; browser shows SUCCEEDED,
RGB/depth and Tag1 detection. N=1 nominal simulated trial, not repeatability or
physical camera acceptance. Evidence: tmp/d435i_acceptance.log,
tmp/d435i_runtime_check.log, tmp/d435i_gui_check.log and per-run reports.

SDK USB enumeration command completed with "No device detected" (nonzero).
Thus physical serial/USB/streams remain unverified; connect the camera and rerun
enumerate/start/check/record. No physical calibration or arm motion performed.
