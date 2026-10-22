# CAD Inventory

Updated 2026-10-08. The active hardware directory is
[hardware/end effector](<../hardware/end effector/README.md>).

| Asset | Files retained | Evidence / limitation |
|---|---|---|
| Inherited end-effector assembly | `End Effector Assembly V3.f3z`, `.step` | Original binary content preserved; all five declared F3D members present |
| Flange V2 | `flange_adapter_v2.step`, `_print_mm.stl` | Analytic STEP reconstruction; original STL retained; original Fusion history unavailable |
| ESP32 bracket V1 | `esp32_bracket_v1.step`, `_print_mm.stl` | Analytic STEP reconstruction; original STL retained; original Fusion history unavailable |
| D435i bracket V3 | `camera_bracket_v3.step`, `_print_mm.stl` | New rear M3 design, 6 mm clip opening; untested physical fit/load |
| Provenance and parameters | `cad_manifest.json`, `cad_parameters.json`, `README.md` | Units, coordinate transforms, SHA and geometry checks; one generation script under tools/gripper |

All three part STEP files use the inherited assembly CAD frame. STL files use
print frames; do not assemble them without the manifest transforms. Old standalone
camera V2, repeated STEP/STL, SVG previews, print ZIP and machine-specific sliced
3MF have been removed from the active folder at the user's request. A local ignored
tmp backup and prior Git history preserve historical inputs; no old generation
script remains necessary for the current three-part build.

Raw F3Z: 3,242,872 bytes; SHA-256
`9e27b636ee18203d0501dda5fddbf83745068a4c52f6580ee69b1a690c6e5581`.
Original STEP and part hashes are in the manifest. Per-part neutral CAD exists;
this does not recover original Fusion history or release individual drawings for
all inherited gripper components.

Still needed: a verified current full assembly including actual D435i/PCB,
fasteners/cables; manufacturing drawings and fit tolerances; physical flange
clocking, finger limits, TCP/camera extrinsics, mass/CoM and print/load validation.
No mobile-base CAD is present. Planning documents do not establish those results.

The ROS composition now uses flange V2, ESP32 V1 and camera V3 with a nominal D435i
housing envelope. It is an offline kinematic/collision-review description, not a
validated hardware or dynamics deployment. See
[URDF integration and checks](GRIPPER_MOUNT_V2_INTEGRATION.md).
