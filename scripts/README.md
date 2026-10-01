# ATOM commands

Use `./scripts/atom.sh --help` for the complete interface. It works from any working directory. Shell implementations under `lib/` are internal; batch Python tools live under `benchmarks/`.

```bash
./scripts/atom.sh build
./scripts/atom.sh sim --camera depth
./scripts/atom.sh sim --camera depth --restart
./scripts/atom.sh attach --camera depth
./scripts/atom.sh status
./scripts/atom.sh stop
```

The default `sim` runs the existing Tag-guided visual approach and read-only English web GUI at <http://127.0.0.1:8089>. Physical grasp/placement is not implemented. `sim --workflow transfer` selects the legacy fixed-target motion test, whose targets do not correspond to the tube slots. `observe --control` enables the separate fixed-observation supervisor, not tube pick/place commands. `stop` closes a simulation session and is not a robot emergency stop.

`--dry-run` prints the selected implementation and arguments without invoking Docker. Options are checked before starting anything. Restart is explicit. Headless baseline and desktop demos retain their existing full-build behavior; `sim` reuses the image and incrementally builds its package.

## Migration

Old `scripts/docker/*.sh` entry files have been merged and removed. Use these replacements:

| Previous script | New command |
| --- | --- |
| `jazzy_build.sh` | `./scripts/atom.sh build` |
| `jazzy_shell.sh` | `./scripts/atom.sh shell` |
| `jazzy_tube_workflow_gui.sh depth --restart` | `./scripts/atom.sh sim --camera depth --restart` |
| `jazzy_operator_attach.sh depth` | `./scripts/atom.sh attach --camera depth` |
| `jazzy_operator_gui.sh rgb control` | `./scripts/atom.sh observe --camera rgb --control` |
| `jazzy_arm_trajectory_sim.sh` | `./scripts/atom.sh demo arm` |
| `jazzy_arm_trajectory_gui.sh` | `./scripts/atom.sh demo arm --gui` |
| `jazzy_arm_dynamics_sim.sh` | `./scripts/atom.sh demo dynamics` |
| `jazzy_transfer_sim.sh` | `./scripts/atom.sh demo transfer` |
| `jazzy_sim_smoke.sh` | `./scripts/atom.sh demo smoke` |
| `jazzy_camera_experiment.sh depth 0 0 0` | `./scripts/atom.sh demo camera --camera depth` |
| `jazzy_camera_experiment_gui.sh depth 0 0 0` | `./scripts/atom.sh demo camera --gui --camera depth` |
| `jazzy_pre_observation_gui.sh depth 0 0 0 0.35` | `./scripts/atom.sh demo approach --gui --camera depth --distance 0.35` |
| `jazzy_approach_trial.sh` | Internal benchmark trial; use `./scripts/atom.sh benchmark run --help` |

Rack perturbations use `--rack-dx` / `--rack-dy` in metres and `--rack-yaw` in radians. Existing provisional bounds are ±0.05 m and ±0.2 rad. Desktop `--gui` demos require DISPLAY/Xauthority. The web GUI does not require a desktop session.

```bash
./scripts/atom.sh demo camera --camera rgb --rack-dx 0.01 --rack-yaw 0.05
./scripts/atom.sh benchmark run --runs 2 --modes rgb depth
./scripts/atom.sh benchmark analyze --help
```

## Internal layout

- `lib/common.sh`: repository path, user IDs and workspace directories.
- `lib/runtime.sh`: build/development shell.
- `lib/baseline.sh`: shared headless arm/dynamics/transfer/smoke runner.
- `lib/desktop.sh`: Gazebo/RViz desktop experiments.
- `lib/camera.sh`: headless camera probe.
- `lib/operator.sh`: web experiment, attach, observation and benchmark trial.

Validation: `python3 -m unittest discover -s tests/scripts -v` passes seven CLI checks, including invalid-option rejection, named stop targets, routing, moved benchmark help and shared-baseline Docker shell syntax through a fake Docker executable. All seven shell files pass `bash -n`. Re-running `sim` against the existing live session confirms reuse without restart; newly launched scenes and desktop windows were not re-executed solely for this reorganisation.

用 `sim --tag-id 0|1|2|3` 选择本架目标（默认 1）。预观察输入是带噪试管架 XY 与精确仿真 TCP 高度；预观察识别全部配置架 tag 后，确认目标属于当前有效观测再对准。RGB/Depth 共用该逻辑。

视觉任务现在共用一个 `atom_task_executive` node：`sim --recipe visual_observe` 只观察，默认 `sim --recipe visual_approach` 观察后对齐/接近。`--camera rgb|depth` 是同一能力的数据源参数，不创建另一套任务实现。
