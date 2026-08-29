# Project ATOM

## Autonomous Transport & Object Manipulation for the Autonomous Chemical Laboratory

> **Project type:** University of Melbourne Mechatronics Capstone, 2026
> S2--2027 S1\
> **Project title:** **ATOM**\
> **Long-form title:** *Autonomous Transport & Object Manipulation for the Autonomous Chemical Laboratory*\
> **Project theme:** Toward a Robotic and AI-Enabled Autonomous Chemical
> Laboratory

------------------------------------------------------------------------

## 1. Project Overview

Project ATOM is a year-long mechatronics Capstone project aiming to develop
an integrated robotic platform for autonomous material/sample handling
in a chemical laboratory.

The intended final platform consists of three principal physical
subsystems:

1.  a **mobile robotic base**;
2.  a **commercial robotic manipulator**;
3.  a **custom two-finger gripper inherited from the previous Capstone
    team**.

These physical systems are to be integrated with perception,
localisation, motion planning, task-level control, safety functions and
a ROS 2-based software architecture.

The long-term objective is not merely to demonstrate a robot arm
performing a fixed pick-and-place motion. The project should progress
toward a **mobile manipulator capable of travelling between laboratory
workstations, localising itself relative to laboratory equipment,
manipulating cuvettes or related labware, and executing an end-to-end
sample-transfer workflow with minimal human intervention**.

The project is intentionally staged over two semesters:

-   **2026 Semester 2:** develop and validate the manipulation subsystem
    around the commercial arm and inherited gripper, initially on a
    fixed platform;
-   **2027 Semester 1:** integrate the mature manipulation subsystem
    with the mobile base developed by another team and demonstrate the
    complete mobile manipulation workflow.

------------------------------------------------------------------------

## 2. Project Background

The previous Capstone team developed a custom gripper for transferring
cuvettes between laboratory instruments. Their nominal application was
the transfer of cuvettes between an **Opentrons Flex** and a **DynaPro
NanoStar**.

Their work established an important hardware and software baseline, but
it did not complete the full autonomous laboratory system.

### 2.1 Previous-team hardware

The inherited gripper uses:

-   a two-finger parallel gripping architecture;
-   a servo-driven rack-and-pinion mechanism;
-   an STS3215 servo;
-   an STM32 Nucleo microcontroller;
-   silicone contact pads;
-   embedded magnets and magnetic sensing to infer silicone deformation;
-   ROS-to-STM32 serial communication;
-   a quick-release mechanical interface.

The reported gripper dimensions were approximately:

-   225 mm length;
-   105 mm width;
-   131 mm height;
-   580 g total mass.

### 2.2 Previous-team experimental platform

Although the previous project identified the UFactory xArm 850 as the
intended future robotic platform, its physical experiments were
conducted using a **Universal Robots UR3e** available at the university.

The previous team demonstrated a fixed-workstation pick-and-place task
using two simulated cuvette holders. The robot followed manually defined
waypoints, and the gripper was commanded to grasp and release at
predetermined positions.

The report recorded 49 successful complete cycles from 50 trials under
those controlled conditions.

### 2.3 Important limitations of the inherited work

The previous work should be treated as a subsystem prototype rather than
a completed autonomous laboratory solution.

Known limitations include:

-   no mobile platform integration;
-   no autonomous navigation;
-   no real Opentrons-to-DynaPro end-to-end validation;
-   fixed manually defined robot waypoints;
-   no robust workstation localisation;
-   no general object pose estimation;
-   no demonstrated compensation for mobile-base positioning error;
-   no fully validated force measurement;
-   no maximum gripper travel limit;
-   no robust timeout logic;
-   possible empty-grasp behaviour;
-   silicone adhesion during release;
-   possible quick-release wear;
-   inconsistent documentation of some final gripper parameters;
-   incomplete system-level emergency-stop implementation.

The inherited gripper, CAD and software therefore form the **starting
point**, not the final solution.

------------------------------------------------------------------------

## 3. Project Identity: ATOM

### ATOM

**A**utonomous\
**L**aboratory\
**C**oordination,\
**H**andling,\
**E**xperiment\
**M**anipulation,\
**I**ntegration,\
**S**imulation and\
**T**ransport

The name reflects the project's actual system scope:

-   **Autonomous Laboratory** --- the final application domain;
-   **Coordination** --- coordination among mobile base, manipulator,
    gripper, sensors and laboratory stations;
-   **Handling** --- physical handling of cuvettes/labware;
-   **Experiment Manipulation** --- robotic interaction with
    experimental samples and equipment;
-   **Integration** --- the central engineering challenge of the
    project;
-   **Simulation** --- development and validation before hardware
    deployment;
-   **Transport** --- eventual mobile transfer between laboratory
    workstations.

The name deliberately avoids implying that the project is purely an AI
or reinforcement-learning project. The primary challenge is robotic
system integration and reliable autonomous manipulation.

------------------------------------------------------------------------

## 4. Final System Concept

The intended final architecture is:

``` text
                 Laboratory Task / User Command
                            |
                            v
                     Task Executive
                            |
          +-----------------+-----------------+
          |                                   |
          v                                   v
   Mobile Navigation                    Manipulation
          |                                   |
          v                                   v
 Localisation / Docking              Perception / Localisation
          |                                   |
          v                                   v
     Mobile Base                    Motion Planning / MoveIt 2
                                              |
                                              v
                                      Commercial Robot Arm
                                              |
                                              v
                                       Custom Gripper
                                              |
                                              v
                                         Cuvette/Labware
```

A representative final workflow is:

``` text
Navigate to source workstation
        ->
Dock / localise relative to workstation
        ->
Identify source / cuvette pose
        ->
Plan arm trajectory
        ->
Approach cuvette
        ->
Close gripper
        ->
Verify grasp
        ->
Retract arm to transport pose
        ->
Navigate to destination workstation
        ->
Dock / relocalise
        ->
Identify destination pose
        ->
Plan insertion / placement trajectory
        ->
Release cuvette
        ->
Verify release
        ->
Return to safe configuration
```

------------------------------------------------------------------------

## 5. Semester Structure

## 5.1 Semester 2, 2026 --- Manipulation Subsystem

The mobile base is expected to be integrated primarily in 2027 S1.
Therefore, 2026 S2 should focus on building a mature manipulation
subsystem.

The target system for this semester is:

``` text
Fixed Base
    +
Commercial Robot Arm
    +
Inherited Gripper
    +
Perception / Workstation Localisation
    +
Motion Planning
    +
Task-Level Control
```

The semester should not end with merely proving that the purchased arm
can move or that the inherited gripper can open and close.

A meaningful S2 outcome should demonstrate an integrated manipulation
pipeline.

### Minimum S2 baseline

-   commercial robot arm operational;
-   inherited gripper mechanically and electrically integrated;
-   ROS 2 communication operational;
-   TCP and gripper mounting transform defined;
-   fixed-position pick-and-place demonstrated;
-   task execution repeatable;
-   basic safety and fault handling implemented.

### Preferred S2 outcome

-   simulation model established before hardware arrival;
-   arm + gripper represented as a modular URDF/Xacro system;
-   MoveIt 2 motion planning;
-   workstation or object localisation using perception/fiducials;
-   pick-and-place remains functional when target pose changes within a
    defined range;
-   repeatable quantitative experiments;
-   architecture prepared for mobile-base integration.

------------------------------------------------------------------------

## 5.2 Semester 1, 2027 --- Mobile Manipulation Integration

The second semester should integrate the manipulation subsystem with the
mobile platform being developed separately.

The major new challenges will include:

-   mechanical mounting of the arm onto the mobile base;
-   payload and centre-of-mass management;
-   power distribution;
-   onboard computing;
-   ROS 2 network integration;
-   full TF-tree integration;
-   navigation;
-   workstation approach;
-   docking/localisation repeatability;
-   compensation for mobile-base positioning errors;
-   safe transport configuration of the manipulator;
-   end-to-end task execution.

The target system becomes:

``` text
Mobile Base
    +
Robot Arm
    +
Gripper
    +
Perception
    +
Navigation
    +
Motion Planning
    +
Task Executive
    +
Safety Supervisor
```

------------------------------------------------------------------------

## 6. Recommended Technical Philosophy

The project should not be framed prematurely as:

> traditional control versus learning-based control.

A commercial robotic manipulator already contains proprietary low-level
servo loops for joint position, velocity and motor control.

The primary project-level algorithmic problems are instead:

-   perception;
-   coordinate transformation;
-   inverse kinematics;
-   collision-free motion planning;
-   task sequencing;
-   grasp verification;
-   precise placement/insertion;
-   localisation;
-   mobile-base docking;
-   error recovery.

The recommended strategy is therefore:

> **Build a robust model-based robotic baseline first, then add
> learning-based methods only where they solve a clearly demonstrated
> limitation.**

------------------------------------------------------------------------

## 7. Proposed Manipulation Algorithm Stack

### 7.1 Baseline: Fixed Waypoint Manipulation

This reproduces the conceptual baseline of the previous team.

``` text
Known source pose
        ->
Predefined waypoint trajectory
        ->
Grasp
        ->
Predefined transfer trajectory
        ->
Release
```

Purpose:

-   hardware commissioning;
-   inherited-gripper reproduction;
-   reference performance;
-   comparison against later methods.

This should not be the final technical contribution.

### 7.2 Main Method: Perception-Guided Model-Based Manipulation

Recommended core architecture:

``` text
Camera / Fiducial Detection
          |
          v
Target / Workstation Pose Estimation
          |
          v
TF Coordinate Transformation
          |
          v
MoveIt 2 Motion Planning
          |
          v
Robot Trajectory Execution
          |
          v
Gripper Action
          |
          v
Grasp / Release Verification
```

Possible localisation approaches include:

-   AprilTag;
-   ArUco;
-   structured workstation fiducials;
-   object pose estimation;
-   fixed-camera or eye-in-hand camera arrangements.

Fiducial-based localisation is particularly suitable as an initial
engineering solution because it is deterministic, measurable and easier
to validate than unconstrained learned vision.

### 7.3 Advanced Manipulation

If precise insertion into real equipment becomes a requirement, the
final few millimetres of motion may require more than open-loop position
control.

Potential methods include:

-   Cartesian low-speed control;
-   visual servoing;
-   force/torque feedback;
-   impedance control;
-   admittance control;
-   passive mechanical compliance;
-   search-based insertion;
-   learned residual correction.

Learning-based control should be treated as an optional advanced module
rather than the foundation of the complete robot.

------------------------------------------------------------------------

## 8. Simulation Strategy

Simulation should begin before the commercial arm arrives.

Its purpose is not simply to claim a "sim-to-real" component. It should
reduce integration risk and allow software development to proceed
independently of hardware delivery.

### 8.1 Primary simulation objectives

The simulation should validate:

-   arm workspace;
-   reachability;
-   inverse kinematics;
-   gripper orientation;
-   collision geometry;
-   workstation approach poses;
-   singular configurations;
-   motion planning;
-   task-state transitions;
-   ROS 2 interfaces;
-   future mobile-base compatibility.

### 8.2 Recommended primary stack

Initial recommended stack:

-   Ubuntu;
-   ROS 2;
-   Xacro/URDF;
-   RViz;
-   MoveIt 2;
-   Gazebo;
-   ros2_control.

Gazebo is recommended as the primary system-integration simulator
because the project is fundamentally a ROS 2 mobile-manipulation system.

Isaac Sim may later be considered if high-fidelity vision or synthetic
visual data becomes important.

Isaac Lab is only justified if the project commits to reinforcement
learning, imitation learning or another policy-training problem.

------------------------------------------------------------------------

## 9. CAD-to-URDF Strategy

The inherited gripper CAD should **not** be permanently merged with the
commercial robot CAD and exported as one monolithic URDF.

The robot description should remain modular.

### 9.1 Recommended architecture

``` text
Vendor Robot Arm Description
            +
Custom Gripper Description
            |
            v
Top-Level Robot Xacro
            |
            v
Combined Arm + Gripper Robot
```

The arm should use the manufacturer's official ROS 2/URDF/Xacro package
whenever available.

The inherited CAD is the mechanical source of truth for the gripper.

### 9.2 Gripper abstraction

The physical gripper contains a servo, pinion, racks and fingers.

For initial robot-level simulation, it can be simplified to:

``` text
gripper_base_link
      |
      +---- left_finger_joint [prismatic]
      |            |
      |            v
      |      left_finger_link
      |
      +---- right_finger_joint [prismatic]
                   |
                   v
             right_finger_link
```

The internal rack-and-pinion contact mechanics do not need to be
simulated unless they become directly relevant to a research question.

### 9.3 CAD use

CAD should provide:

-   visual geometry;
-   mounting dimensions;
-   gripper dimensions;
-   finger geometry;
-   mechanical reference frames;
-   approximate inertial information;
-   mounting transform;
-   TCP definition.

Visual meshes may retain relatively detailed geometry.

Collision meshes should normally be simplified.

### 9.4 Arm-to-gripper connection

The gripper should be attached to the manufacturer's end-effector flange
through a fixed joint.

Conceptually:

``` text
arm tool0 / flange
       |
       | fixed joint
       v
gripper_mount
       |
       v
gripper_base_link
```

The critical parameter is the measured or CAD-derived rigid transform
between the arm flange and gripper reference frame.

------------------------------------------------------------------------

## 10. Future Mobile-Base URDF Integration

The modular description should allow the 2027 system to evolve from:

``` text
world
  |
fixed_arm_base
  |
robot_arm
  |
gripper
```

to:

``` text
map
 |
odom
 |
mobile_base
 |
arm_mount
 |
robot_arm
 |
gripper
```

without redesigning the complete arm or gripper descriptions.

The eventual full robot description should include:

-   mobile-base description;
-   arm description;
-   gripper description;
-   sensor descriptions;
-   mounting transforms;
-   ros2_control configuration;
-   collision geometry.

------------------------------------------------------------------------

## 11. Coordinate Frames

Coordinate management is a core technical issue.

The final system may contain a TF hierarchy similar to:

``` text
map
 |
odom
 |
base_link
 |
arm_mount
 |
arm_base
 |
...
 |
tool0
 |
gripper_base
 |
gripper_tcp
 |
cuvette
```

Additional frames may include:

-   camera_link;
-   camera_optical_frame;
-   source_workstation;
-   destination_workstation;
-   Opentrons reference frame;
-   DynaPro reference frame;
-   grasp pose;
-   pre-grasp pose;
-   insertion pose.

Calibration should be treated as a formal subsystem, not an informal
setup step.

------------------------------------------------------------------------

## 12. Gripper Inheritance and Improvement

The previous team's gripper should initially be inherited rather than
redesigned from scratch.

The first task is reproduction and characterisation.

### Required handover assets

Where available:

-   original CAD;
-   STEP/STL files;
-   assembly files;
-   STM32 firmware;
-   ROS 2 code;
-   wiring diagrams;
-   pin mapping;
-   final parameter configuration;
-   test data;
-   physical prototype;
-   manufacturing information.

### Initial verification

Before modification:

-   verify opening and closing;
-   verify homing/calibration;
-   inspect rack-and-pinion motion;
-   inspect silicone condition;
-   inspect magnetic sensors;
-   inspect servo behaviour;
-   verify serial communication;
-   identify actual final control parameters;
-   reproduce basic grasping.

### Known improvement areas

Potential improvements include:

-   motion timeout;
-   maximum finger travel;
-   empty-grasp detection;
-   robust object-present detection;
-   sensor fault handling;
-   release reliability;
-   gripper state machine;
-   force/deformation calibration;
-   quick-release repeatability;
-   improved cable management;
-   mechanical collision risk reduction.

------------------------------------------------------------------------

## 13. Gripper State Machine

The gripper software should expose explicit states rather than only raw
open/close commands.

Suggested states:

``` text
UNCALIBRATED
     |
     v
CALIBRATING
     |
     v
OPEN
     |
     v
CLOSING
  /       \
 v         v
GRASPED   EMPTY_GRASP
 |
 v
HOLDING
 |
 v
RELEASING
 |
 v
OPEN
```

Fault transitions may include:

``` text
SENSOR_FAULT
SERVO_FAULT
TIMEOUT
OVERLOAD
SLIP_DETECTED
EMERGENCY_STOP
```

The higher-level task controller should interact with this state machine
through a defined ROS 2 interface.

------------------------------------------------------------------------

## 14. Task-Level Control

The complete system should use an explicit task executive/state machine.

For 2026 S2:

``` text
IDLE
 |
LOCALISE_SOURCE
 |
MOVE_TO_PREGRASP
 |
APPROACH
 |
GRASP
 |
VERIFY_GRASP
 |
RETRACT
 |
MOVE_TO_DESTINATION_POSE
 |
APPROACH_DESTINATION
 |
RELEASE
 |
VERIFY_RELEASE
 |
RETURN_SAFE
 |
COMPLETE
```

For 2027 S1, navigation states can be inserted:

``` text
NAVIGATE_TO_SOURCE
DOCK_AT_SOURCE
...
NAVIGATE_TO_DESTINATION
DOCK_AT_DESTINATION
...
```

This allows the manipulation subsystem to remain largely unchanged when
the mobile base is introduced.

------------------------------------------------------------------------

## 15. Mobile-Base Integration Requirements

Although physical integration is planned mainly for 2027, the interface
with the mobile-base team should be defined during 2026.

### Mechanical interface

Need to determine:

-   payload;
-   mounting surface;
-   arm mounting pattern;
-   allowable centre of gravity;
-   allowable overturning moment;
-   platform stiffness;
-   sensor mounting;
-   computer mounting;
-   cable routing.

### Electrical interface

Need to determine:

-   battery voltage;
-   available power;
-   arm power strategy;
-   DC/DC requirements;
-   emergency-stop architecture;
-   power isolation;
-   charging strategy.

### Software interface

Need to define:

-   Ubuntu version;
-   ROS 2 distribution;
-   base_link convention;
-   odometry topic;
-   velocity command interface;
-   localisation output;
-   navigation interface;
-   docking interface;
-   battery state;
-   emergency-stop state.

### Performance interface

The mobile-base team should eventually characterise:

-   translational docking error;
-   lateral docking error;
-   heading error;
-   repeatability;
-   braking performance;
-   behaviour under manipulator payload.

This is essential because the manipulation system must be designed to
tolerate or compensate for base-placement uncertainty.

------------------------------------------------------------------------

## 16. Sim-to-Real Strategy

For model-based manipulation, the simulation-to-hardware process should
be treated primarily as **simulation-based development followed by
calibrated hardware deployment**.

Important simulation-to-real differences include:

-   TCP offset;
-   gripper mounting offset;
-   joint zero offsets;
-   mechanical compliance;
-   collision geometry approximation;
-   camera extrinsics;
-   target pose error;
-   friction;
-   gripper travel;
-   control latency;
-   communication latency.

The transition should be documented systematically.

Suggested file:

``` text
docs/SIM2REAL_LOG.md
```

Each discrepancy should record:

-   simulated assumption;
-   real measurement;
-   correction;
-   validation result.

If a learned policy is later introduced, then additional sim-to-real
methods such as domain randomisation may become relevant.

------------------------------------------------------------------------

## 17. Proposed Experimental Progression

A strong experimental structure would compare progressively more
autonomous methods.

### Experiment 1 --- Fixed-Waypoint Baseline

Replicate the conceptual previous-team task:

-   fixed source;
-   fixed destination;
-   predefined robot motion;
-   gripper close/open.

Measure:

-   task success rate;
-   grasp success rate;
-   cycle time;
-   release failures.

### Experiment 2 --- Pose-Perturbed Manipulation

Randomly perturb the source/workstation pose within a controlled range.

Compare:

**Fixed waypoint** versus **perception-guided replanning**.

Measure:

-   localisation error;
-   planning success;
-   grasp success;
-   placement error;
-   task success;
-   execution time.

### Experiment 3 --- Precision Placement / Insertion

If the real laboratory task requires precise insertion:

compare possible methods such as:

-   open-loop position control;
-   vision correction;
-   compliant/force-assisted insertion.

Measure:

-   insertion success;
-   peak contact force;
-   alignment error;
-   completion time;
-   recovery behaviour.

### Experiment 4 --- Mobile Manipulation

In 2027:

-   vary mobile-base docking error;
-   relocalise workstation;
-   perform manipulation;
-   quantify total end-to-end success.

This directly tests whether the 2026 perception/manipulation
architecture successfully handles the uncertainty introduced by
mobility.

------------------------------------------------------------------------

## 18. Metrics

The project should use quantitative verification rather than qualitative
claims such as "accurate" or "reliable".

Candidate metrics:

### Manipulation

-   grasp success rate;
-   release success rate;
-   full-cycle success rate;
-   placement error;
-   orientation error;
-   cycle time;
-   trajectory planning time;
-   collision-free planning rate.

### Perception

-   translation error;
-   rotation error;
-   detection rate;
-   localisation latency;
-   robustness to target displacement.

### Gripper

-   finger position repeatability;
-   grasp detection accuracy;
-   empty-grasp detection rate;
-   slip detection rate;
-   maximum measured gripping force;
-   release reliability.

### Mobile integration

-   docking translation error;
-   docking yaw error;
-   docking repeatability;
-   manipulation success versus docking error;
-   full end-to-end task success.

### Safety

-   emergency-stop response;
-   timeout behaviour;
-   communication-loss response;
-   obstacle response;
-   failed-grasp recovery.

------------------------------------------------------------------------

## 19. Safety

Safety must be designed at system level.

Relevant hazards include:

-   robot-human collision;
-   arm-mobile-base instability;
-   gripper collision with equipment;
-   glass/cuvette breakage;
-   liquid spillage;
-   electrical faults;
-   unexpected arm motion;
-   communication failure;
-   sensor failure;
-   navigation failure.

Software protection should not be treated as a substitute for hardware
emergency-stop architecture.

The final system should distinguish:

-   operational stop;
-   protective stop;
-   software fault;
-   hardware emergency stop.

------------------------------------------------------------------------

## 20. Software Architecture

Recommended repository structure:

``` text
autonomous_lab_robot/
|
+-- AGENTS.md
+-- README.md
|
+-- docs/
|   +-- PROJECT_CONTEXT.md
|   +-- SYSTEM_ARCHITECTURE.md
|   +-- GRIPPER_DESIGN.md
|   +-- CAD_INVENTORY.md
|   +-- ASSUMPTIONS.md
|   +-- DECISIONS.md
|   +-- KNOWN_ISSUES.md
|   +-- SIM2REAL_LOG.md
|
+-- reference/
|   +-- previous_report.pdf
|
+-- source_cad/
|   +-- previous_gripper/
|
+-- ros2_ws/
    +-- src/
        +-- autolab_gripper_description/
        +-- autolab_robot_description/
        +-- autolab_moveit_config/
        +-- autolab_gripper_driver/
        +-- autolab_perception/
        +-- autolab_task_control/
        +-- autolab_simulation/
```

In 2027, additional packages may include:

``` text
autolab_mobile_base/
autolab_navigation/
autolab_docking/
```

------------------------------------------------------------------------

## 21. Recommended Development Workflow

Development should be gated.

### Gate 1 --- Inherited gripper understood

Do not modify the design until:

-   CAD hierarchy is understood;
-   moving components are identified;
-   units are confirmed;
-   mounting interface is identified;
-   original software is archived;
-   physical gripper is inspected.

### Gate 2 --- Gripper robot description validated

Before arm integration:

-   gripper Xacro parses;
-   TF tree is valid;
-   mesh scale is correct;
-   finger directions are correct;
-   joint limits are correct;
-   RViz visualisation works.

### Gate 3 --- Arm + gripper model validated

Before Gazebo:

-   official arm model used;
-   fixed mounting joint correct;
-   TCP defined;
-   MoveIt recognises combined robot;
-   no obvious self-collision;
-   planning succeeds in RViz.

### Gate 4 --- Simulation baseline

Before real-hardware deployment:

-   Gazebo launches reliably;
-   controllers start automatically;
-   arm executes trajectories;
-   gripper opens/closes;
-   baseline pick-and-place works;
-   task state machine works.

### Gate 5 --- Real arm deployment

-   hardware arm commissioned;
-   mounting transform measured;
-   TCP calibrated;
-   speed reduced initially;
-   gripper integrated;
-   baseline reproduced physically.

### Gate 6 --- Perception-guided manipulation

-   workstation/target localisation;
-   target perturbation tests;
-   automatic replanning;
-   quantitative comparison with fixed-waypoint baseline.

### Gate 7 --- Mobile integration

-   mobile-base interface validated;
-   mechanical/electrical integration complete;
-   navigation operational;
-   docking error measured;
-   perception compensates for docking uncertainty;
-   end-to-end task demonstrated.

------------------------------------------------------------------------

## 22. Indicative Timeline

### 2026 S2

**August** - inherited project handover; - CAD/software inventory; -
confirm commercial arm model; - confirm hardware delivery schedule; -
define system requirements; - define interface with mobile-base team; -
establish repository and simulation environment.

**September** - gripper CAD abstraction; - gripper URDF/Xacro; - RViz
validation; - commercial arm simulation model; - combined arm-gripper
Xacro; - MoveIt 2 configuration; - gripper software/state-machine
improvements.

**October** - Gazebo manipulation simulation; - baseline
pick-and-place; - perception/fiducial localisation; - target-pose
perturbation experiments; - physical arm integration when hardware
arrives.

**November** - real arm + gripper demonstration; - perception-guided
manipulation where feasible; - quantitative testing; - S2 preliminary
presentation; - freeze mobile-base integration requirements.

### Summer 2026/27

-   improve gripper reliability;
-   finalise mounting hardware;
-   improve calibration;
-   maintain simulation;
-   prepare full mobile-manipulator URDF;
-   coordinate with mobile-base team;
-   prepare laboratory workstation models.

### 2027 S1

**Early semester** - integrate arm with mobile base; - integrate
power/computing; - establish full TF tree; - validate transport pose and
stability.

**Mid semester** - navigation; - workstation approach; -
docking/localisation; - compensate for docking error; - integrate
manipulation.

**Late semester** - end-to-end laboratory transfer; - robustness
experiments; - fault injection; - repeated trials; - final system
evaluation; - final report and exhibition.

------------------------------------------------------------------------

## 23. Immediate Unknowns

The following items must be confirmed rather than assumed:

1.  exact commercial robot arm model actually purchased;
2.  confirmed delivery date;
3.  exact mobile-base architecture and delivery schedule;
4.  access to real Opentrons Flex;
5.  access to real DynaPro NanoStar;
6.  exact final laboratory workflow;
7.  whether real instrument insertion is mandatory;
8.  whether fiducial markers may be installed;
9.  available cameras and force/torque sensors;
10. laboratory safety constraints;
11. whether the previous team can provide a technical handover;
12. availability of complete previous-team source code and raw data.

The UFactory xArm 850 subsequently arrived for Project ATOM on
2026-08-29. This confirms the project arm model, but not the controller,
firmware, calibration, ROS 2 support matrix or commissioning state; see
`docs/DECISIONS.md` D-006.

------------------------------------------------------------------------

## 24. Project Success Definition

A weak interpretation of the project would be:

> attach an inherited gripper to a purchased robot arm and replay fixed
> waypoints.

That would provide limited technical progression beyond the previous
project.

A stronger and more defensible definition is:

> Develop a modular, perception-aware robotic manipulation system
> capable of locating, grasping, transporting and placing laboratory
> samples, validate it in simulation and on real hardware, and
> subsequently integrate it with a mobile platform to create an
> autonomous mobile laboratory manipulation system.

The core technical progression is therefore:

``` text
Previous Project
Fixed UR3e + custom gripper + fixed waypoints
              |
              v
2026 S2
Commercial arm + inherited gripper
+ simulation
+ motion planning
+ perception
+ robust manipulation
              |
              v
2027 S1
Mobile base
+ localisation/navigation
+ workstation docking
+ mobile manipulation
+ end-to-end laboratory workflow
```

------------------------------------------------------------------------

## 25. Guiding Engineering Principle

The project should prioritise:

> **reliable autonomy over decorative complexity.**

Learning-based methods, advanced AI and high-fidelity simulation are
valuable only when they address a clearly measured limitation.

The engineering order should remain:

1.  understand inherited hardware;
2.  reproduce it;
3.  model it;
4.  simulate it;
5.  establish a deterministic manipulation baseline;
6.  add perception and closed-loop correction;
7.  deploy on real hardware;
8.  integrate mobility;
9.  quantify robustness;
10. add advanced learning methods only where justified.

This approach maximises the probability of producing both a strong
Capstone demonstration and a technically defensible engineering
contribution.
