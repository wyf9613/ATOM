# ATOM D435i camera module

Imports `realsense2_description` D435i model through `atom_d435i.urdf.xacro`.
No copied vendor mesh or monolithic arm/tool export. Model and SDK versions are
installed/pinned in docker/jazzy/Dockerfile. Macro mount origin is the bottom
screw frame. Current reserved placement is provisional.

`camera_enabled:=true` enables the camera in the combined ATOM Xacro. Set
`camera_nominal_extrinsics:=true` only in simulation; leave false with the real
camera driver so its calibrated internal TF is the sole authority.

Camera-only launch: `ros2 launch atom_camera_description d435i_hardware.launch.py`.
Host wrapper: `tools/camera/d435i.sh --help`. No arm runtime or motion starts.
Full setup, calibration gates and limitations:
[commissioning guide](../../../docs/D435I_BRINGUP_AND_CALIBRATION.md).
