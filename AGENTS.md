# Project instructions

## Scope

This repository belongs to Project ATOM (Autonomous Transport & Object Manipulation for the Autonomous Chemical Laboratory), a University of Melbourne Mechatronics Capstone project. The current phase is inherited-asset verification and architecture definition, not a completed autonomous-laboratory implementation.

## Sources of truth

Use evidence in this order:

1. measurements from the physical system and repeatable test data;
2. original CAD, firmware and source code;
3. the previous-team PDF report;
4. `ATOM_Project_Context.md` and planning documents.

Planning documents describe intended work and must not be presented as implemented capability.

## Engineering constraints

- Do not state that the xArm 850 is the purchased arm until procurement is confirmed.
- Do not select a ROS 2 distribution, Ubuntu version, vendor driver or MoveIt configuration without recording the evidence in `docs/DECISIONS.md`.
- Keep the vendor arm description, custom gripper description and future mobile-base description modular. Do not export a monolithic arm-plus-gripper URDF from CAD.
- Use simplified collision meshes and measured inertial/TCP data; retain detailed CAD only as the mechanical source of truth.
- Establish a deterministic, model-based manipulation baseline before proposing a learned controller.
- Treat calibration, TF frames, fault handling and system-level safety as first-class subsystems.
- A software stop is not a hardware emergency stop. Do not claim safety compliance without evidence.

## Asset handling

- Treat files under `previous report/` and binary handover files under `hardware/` as read-only raw inputs unless the user explicitly requests a revision.
- Store derived notes under `docs/`, generated meshes in a future dedicated package, and temporary extraction/rendering under `tmp/`.
- Track binary CAD and PDF files through Git LFS.

## Documentation discipline

- Record confirmed choices in `docs/DECISIONS.md`.
- Record unresolved facts in `docs/ASSUMPTIONS.md` or `docs/KNOWN_ISSUES.md`.
- Record simulation-to-hardware differences in `docs/SIM2REAL_LOG.md`.
- Attach units, test conditions, sample counts and uncertainty to quantitative claims.
