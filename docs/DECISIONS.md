# 工程决策记录

本文件保留每项选择的完整英文证据与边界，便于和厂商资料、软件版本及测试日志逐字对应。中文速览如下：

| 决策 | 中文摘要 | 适用边界 |
| --- | --- | --- |
| D-001 | 原始交接资产保持不变 | 全项目 |
| D-002 | 机械臂、夹爪和底盘采用模块化描述 | 全项目 |
| D-003 | 先建立确定性、可复现基线 | 全项目 |
| D-004 | 未确认最终平台前，不冻结真实部署脚手架 | 真实系统 |
| D-005 | CAD、网格和 PDF 使用 Git LFS | 仓库管理 |
| D-006 | 使用 Jazzy/Harmonic 建立继承资产仿真基线 | 仅仿真验证，不代表最终部署版本 |
| D-007 | 使用官方 UR3e 包复现上一组平台 | 仅继承资产验证，不代表采购机械臂 |
| D-008 | 明确区分 UR 法兰、夹爪安装帧和暂定 CAD 基准 | 仿真基线，实机前必须测量 |
| D-009 | 增加参数明确的刚体接触抓取基线 | 仅软件和模型验证 |
| D-010 | 增加 Humble/Fortress Docker 兼容性门 | 实验室软件兼容验证，不代表实机兼容 |
| D-011 | UR3e 使用官方名义动力学，夹爪暂用报告质量 | 仿真基线，待实测替换 |
| D-012 | 使用 ros2_control、MoveIt 和逻辑/物理双模式抓取 | 仅仿真任务验证 |

下面是带日期、证据、验证结果和适用边界的完整记录。

## D-001 - Preserve raw handover assets

- Date: 2026-08-09
- Status: Accepted
- Decision: Keep the received context file, PDF and F3Z at their current paths and unchanged during repository initialization.
- Reason: Maintain provenance and avoid breaking the existing Obsidian workspace before the team agrees on migration.

## D-002 - Use modular robot descriptions

- Date: 2026-08-09
- Status: Accepted
- Decision: Compose vendor arm, custom gripper and future mobile base through top-level Xacro mounting transforms.
- Reason: Allows hardware substitution and mobile-base integration without rebuilding a monolithic model.

## D-003 - Establish the deterministic baseline first

- Date: 2026-08-09
- Status: Accepted
- Decision: Prioritise URDF/Xacro, TF, MoveIt 2, perception-guided pose updates and explicit state machines before learned control.
- Reason: These address the measured integration gaps and provide a reproducible comparison baseline.

## D-004 - Defer platform-specific ROS scaffolding

- Date: 2026-08-09
- Status: Accepted
- Decision: Create the ROS 2 workspace but no vendor/distro-specific packages until the arm and ROS 2 distribution are confirmed.
- Reason: Avoid committing to incompatible drivers, package formats or dependencies.

## D-005 - Track binary engineering assets with Git LFS

- Date: 2026-08-09
- Status: Accepted
- Decision: Use Git LFS for Fusion archives/models, neutral CAD meshes and PDFs.
- Reason: These binary files do not benefit from normal Git deltas and are expected to grow.

## D-006 - Use ROS 2 Jazzy and Gazebo Harmonic for the inherited-asset simulation baseline

- Date: 2026-08-12
- Status: Accepted for simulation baseline only
- Decision: Use Ubuntu 24.04, ROS 2 Jazzy and Gazebo Harmonic (Gazebo Sim 8) for the reproducible inherited-asset verification environment.
- Evidence: The development machine runs Ubuntu 24.04.3 and has ROS 2 Jazzy desktop, `ros_gz` 1.0.22 and Gazebo Sim 8.11.0 installed. ROS 2 Jazzy is the ROS release targeting Ubuntu 24.04, and its `ros_gz` vendor packages provide Gazebo Harmonic.
- Boundary: This does not select the deployment computer, a real-arm driver, or the final project ROS distribution. Revisit after the purchased arm, controller and mobile-base support matrix are confirmed.

## D-007 - Use official Universal Robots packages for the UR3e verification model

- Date: 2026-08-12
- Status: Accepted for inherited-asset verification only
- Decision: Use the official Universal Robots ROS 2 description and Gazebo simulation repositories, pinned in `ros2_ws/atom_sim.repos`, with `ur_type:=ur3e`. Keep the custom gripper in a separate package and compose it through a top-level Xacro.
- Evidence: The previous-team report identifies the university test platform as a UR3e. Universal Robots publishes `Universal_Robots_ROS2_Description` and `Universal_Robots_ROS2_GZ_Simulation`, both with Jazzy-compatible releases and UR3e support.
- Boundary: UR3e is a reference platform for reproducing the inherited experiment, not a claim about the arm purchased for Project ATOM.

## D-008 - Separate the UR flange, gripper mount and provisional CAD datum

- Date: 2026-08-12
- Status: Accepted for simulation baseline only
- Decision: Attach an explicit `gripper_mount` frame to the official UR description's `flange` frame, applying the upstream `flange`-to-`tool0` axis alignment so the gripper points forward along the wrist. Place the inherited gripper visual model using the geometric centre of the two case rear faces as a reproducible provisional CAD datum.
- Evidence: The upstream UR Xacro identifies `flange` as the end-effector attachment point and `tool0` as the all-zeros tool frame, with a fixed 90-degree-axis rotation between them. The previous-team report identifies URT-1 as the servo driver, so its component centre is not a mechanical mounting reference.
- Boundary: The case datum is not evidence of the physical quick-disconnect pose. Replace the provisional transform and TCP with measured values, units, method and uncertainty before using the model for clearance, planning or hardware deployment.

## D-009 - Add a parameter-explicit rigid-contact grasp baseline

- Date: 2026-08-12
- Status: Accepted for simulation baseline only
- Decision: Add a separate gravity-enabled Gazebo scenario with a rigid cuvette, simplified terminal finger-pad collisions and an automated grasp/lift/hold/return/release acceptance test. Preserve the zero-gravity resource and motion smoke test as a separate scenario.
- Evidence: The inherited report specifies a 14 x 14 mm cuvette cross-section, Silicone 20A pads, a mean friction coefficient of 0.88 from 10 inclined-plane trials and a 20 mm contact height used in its pressure analysis. The CAD confirms symmetric parallel-jaw motion but does not establish physical limits.
- Boundary: The 45 mm height, 10 g mass, rigid contact, single-side 20 mm joint travel and controller gains are provisional. A pass is software evidence only and does not establish grip force, material stress, hardware reliability or real instrument compatibility.

## D-010 - Add a Humble/Fortress deployment-compatibility container

- Date: 2026-08-13
- Status: Accepted for compatibility verification
- Decision: Keep the Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic host baseline, and add a separate Ubuntu 22.04 / ROS 2 Humble / Gazebo Fortress Docker environment as the deployment-compatibility gate. Include the Humble MoveIt 2 toolchain without selecting an ATOM MoveIt configuration. Use the official Humble branch of the UR description at commit `18e6f603b3ebc2ec479fecb62d6be544b15755e9`.
- Evidence: The project supervisor reported that the previous project and laboratory computer use Ubuntu 22.04 and ROS 2 Humble. REP-2000 defines Ubuntu 22.04 as Humble's Tier-1 platform, and Gazebo documents Fortress as the recommended Humble pairing.
- Verification: On 2026-08-13, image `atom-humble-fortress:latest` (`sha256:17ed7eb37301a67ec790d9344fef65193d15bb91be8b1aae829001bb9e46bb6b`) built on the Ubuntu 24.04 workstation. The Humble workspace, URDF check, four package-test results and one headless Fortress grasp/lift/hold/release run passed. Exact test conditions and results are recorded in `docs/SIM2REAL_LOG.md`.
- Boundary: Container success checks the software stack on the target OS/ROS pairing; it does not reproduce the laboratory computer's GPU, USB/serial devices, vendor controller, firmware, real-time settings or exact installed patch versions. The full test must still be repeated on the laboratory computer.
- Amendment (2026-08-13): D-012 subsequently adds and validates an ATOM-specific MoveIt verification configuration in this container. This does not change the deployment boundary above.

## D-011 - Use official nominal UR3e dynamics and the report-estimated gripper mass

- Date: 2026-08-13
- Status: Accepted for simulation baseline only
- Decision: Continue to source the UR3e joint limits, nominal kinematics, link masses, centres of mass and inertia tensors from the pinned official `ur_description` package. Limit the six Gazebo position-controller outputs using the same official joint-limit file (`54/54/28/9/9/9 N.m`). Use the inherited report's `0.58 kg` total gripper-mass estimate, provisionally split as `0.48/0.05/0.05 kg` across the body and two fingers.
- Evidence: The official UR3e files are present under `ur_description/config/ur3e` and are already inputs to the modular top-level Xacro. The inherited report is the best currently available source for total gripper mass; no physical gripper or CAD material/mass-property export is available for confirmation.
- Verification: Description tests require the expanded URDF effort limits and Gazebo output caps to agree with the official UR3e values, and require the three simulated gripper-link masses to sum to `0.58 kg`. The gravity-enabled grasp test also checks six-axis holding error and drift over a `5 s` loaded hold.
- Boundary: The official files provide a nominal rigid-body model, not serial-number calibration, joint compliance, backlash, gearbox/controller dynamics or public acceleration limits. The gripper mass split, centre of mass and box inertias remain estimates with unknown uncertainty; replace them after weighing the assembly and measuring or calculating its mass properties.

## D-012 - Use ros2_control and an explicit dual-mode MoveIt grasp baseline

- Date: 2026-08-13
- Status: Accepted for simulation verification only
- Decision: Preserve the Gazebo-native position-controller backend as a regression baseline and add a selectable `ros2_control` backend for trajectory execution. Keep the MoveIt configuration in the independent `atom_ur3e_moveit_config` package and task logic in `atom_manipulation`. Use OMPL RRT-Connect for the free-space transfer, Cartesian paths for the `50 mm` approach/lift/lower/retreat segments, and an explicit task state machine.
- Decision: Test two separate grasp modes. `logical` mode may create a Gazebo detachable fixed joint only after checking TCP distance (`<= 0.035 m`), arm-joint speed (`<= 0.020 rad/s`) and object speed (`<= 0.020 m/s`). `physical` mode never invokes that mechanism and relies only on the provisional rigid collision/friction model.
- Evidence: The controller YAML, SRDF groups, planning limits and MoveIt controller mappings are checked by package tests. In Ubuntu 22.04 / ROS 2 Humble / Gazebo Fortress / MoveIt 2.5.9, 10/10 fresh logical runs and 10/10 fresh physical-contact runs completed approach, close, acquisition, `50 mm` lift, `0.2 rad` shoulder-pan transfer, lower, release and retreat. All 20 then reproduced the G-014 `move_group` shutdown fault, so clean teardown is not accepted. Exact batch evidence is recorded in `docs/SIM2REAL_LOG.md`.
- Boundary: The fixtures are not real instrument geometry, their poses are fixed, and the PlanningScene does not yet include the Gazebo supports. The joint acceleration limits are conservative provisional planning values because the received evidence and official description do not provide a complete hardware acceleration model. Neither mode validates the physical mount, TCP, compliance, grip force, breakage risk, insertion tolerance or purchased-arm driver.
