#!/usr/bin/env bash
# Public Project ATOM entry point. Keep implementation in scripts/lib/.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
usage() {
  cat <<'HELP'
Usage: ./scripts/atom.sh COMMAND [OPTIONS]

Daily workflow:
  sim       [--camera depth|rgb] [--restart] [--workflow approach|transfer] [--recipe visual_observe|visual_approach] [--tag-id 0|1|2|3] [--gui]
            Gazebo + English web GUI. Default: Tag-guided approach, not physical pick/place.
  attach    [--camera depth|rgb]       Monitor an existing simulation; no motion starts.
  observe   [--camera depth|rgb] [--control]
            Fixed observation demo; --control enables its guarded simulation commands.
  status                             List ATOM containers.
  stop      [--session tube|observe|monitor]
            Close a simulation/container session; this is not a robot emergency stop.

Development and tests:
  build                              Build Docker image and selected ROS packages.
  shell                              Enter the ROS development container.
  demo arm [--gui]                    Arm-only trajectory baseline.
  demo dynamics|transfer|smoke        Headless baseline tests (transfer uses simulated grasp).
  demo camera [--gui] [--camera depth|rgb] [--rack-dx M] [--rack-dy M] [--rack-yaw RAD]
  demo approach --gui [--camera depth|rgb] [--rack-dx M] [--rack-dy M] [--rack-yaw RAD] [--distance M]
  benchmark run|analyze [ARGS]        Existing RGB/depth batch experiment tools.

  --dry-run                          Show the selected entry without starting anything.
  --help                             Show this help.
Web GUI: http://127.0.0.1:8089. Build once before the first simulation.
HELP
}
fail() { echo "Error: $*" >&2; exit 2; }
command_name="${1:---help}"
shift || true
case "${command_name}" in --help|-h|help) usage; exit 0 ;; esac
case "${command_name}" in
  benchmark)
    action="${1:-}"; shift || true
    case "${action}" in run) tool=run_approach.py ;; analyze) tool=analyze_approach.py ;; *) fail 'benchmark requires run or analyze' ;; esac
    exec python3 "${repo_root}/scripts/benchmarks/${tool}" "$@"
    ;;
  sim|attach|observe|status|stop|build|shell) demo='' ;;
  demo)
    demo="${1:-}"; shift || true
    case "${demo}" in arm|dynamics|transfer|smoke|camera|approach) ;; *) fail 'Unknown demo; see --help' ;; esac
    ;;
  *) fail "Unknown command ${command_name}; see --help" ;;
esac
tag_id=1;recipe=visual_approach;camera=depth;restart='';workflow=approach;gui=false;control=monitor;session=tube
dx=0.0;dy=0.0;dyaw=0.0;distance=0.35;dry_run=false
while (($#)); do
  option="$1"; shift
  case "${option}" in
    --help|-h) usage; exit 0 ;;
    --dry-run) dry_run=true ;;
    --restart) [[ "${command_name}" == sim ]] || fail '--restart applies to sim'; restart=--restart ;;
    --gui) [[ "${command_name}" == sim || ( "${command_name}" == demo && "${demo}" =~ ^(arm|camera|approach)$ ) ]] || fail '--gui applies to sim or demo arm/camera/approach'; gui=true ;;
    --control) [[ "${command_name}" == observe ]] || fail '--control applies to observe'; control=control ;;
    --tag-id|--recipe|--camera|--workflow|--session|--rack-dx|--rack-dy|--rack-yaw|--distance)
      (($#)) || fail "Missing value for ${option}"
      value="$1";shift
      case "${option}" in
        --tag-id)
          [[ "${command_name}" == sim ]] || fail '--tag-id applies to sim'
          [[ "${value}" =~ ^[0-3]$ ]] || fail 'Tag ID must be 0, 1, 2 or 3';tag_id="${value}" ;;
        --camera)
          [[ "${command_name}" =~ ^(sim|attach|observe)$ || "${demo}" =~ ^(camera|approach)$ ]] || fail '--camera is not supported for this command'
          [[ "${value}" == rgb || "${value}" == depth ]] || fail 'Camera must be rgb or depth';camera="${value}" ;;
        --recipe) [[ "${command_name}" == sim ]] || fail '--recipe applies to sim';[[ "${value}" == visual_observe || "${value}" == visual_approach ]] || fail 'Unknown recipe';recipe="${value}" ;;
        --workflow) [[ "${command_name}" == sim ]] || fail '--workflow applies to sim';[[ "${value}" == approach || "${value}" == transfer ]] || fail 'Workflow must be approach or transfer';workflow="${value}" ;;
        --session) [[ "${command_name}" == stop ]] || fail '--session applies to stop';[[ "${value}" =~ ^(tube|observe|monitor)$ ]] || fail 'Unknown session';session="${value}" ;;
        --rack-*|--distance)
          [[ "${demo}" =~ ^(camera|approach)$ ]] || fail 'Rack/target options apply to demo camera/approach'
          [[ "${option}" != --distance || "${demo}" == approach ]] || fail '--distance applies to demo approach'
          case "${option}" in --rack-dx) dx="${value}" ;; --rack-dy) dy="${value}" ;; --rack-yaw) dyaw="${value}" ;; --distance) distance="${value}" ;; esac
          ;;
      esac ;;
    *) fail "Unknown option ${option}; see --help" ;;
  esac
done
[[ "${workflow}" != transfer || "${recipe}" == visual_approach ]] || fail '--recipe cannot be combined with legacy transfer'
# Reject malformed/non-finite geometry before any build or container operation.
python3 - "${dx}" "${dy}" "${dyaw}" "${distance}" <<'PY'
import math,sys
try:
    dx,dy,yaw,distance=map(float,sys.argv[1:])
    assert all(math.isfinite(v) for v in (dx,dy,yaw,distance))
    assert abs(dx)<=.05 and abs(dy)<=.05 and abs(yaw)<=.2 and distance>0
except (ValueError,AssertionError):
    sys.exit('Invalid geometry: finite rack offsets <=0.05 m / yaw <=0.2 rad, positive distance required')
PY
case "${command_name}" in
  sim) selected=(bash "${repo_root}/scripts/lib/operator.sh" workflow "${camera}" "${restart}" "${workflow}" "${recipe}" "${tag_id}" "${gui}") ;;
  attach) selected=(bash "${repo_root}/scripts/lib/operator.sh" attach "${camera}") ;;
  observe) selected=(bash "${repo_root}/scripts/lib/operator.sh" observe "${camera}" "${control}") ;;
  build|shell) selected=(bash "${repo_root}/scripts/lib/runtime.sh" "${command_name}") ;;
  status) selected=(docker ps -a --filter name=atom- --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}') ;;
  stop)
    case "${session}" in tube) container=atom-tube-workflow ;; observe) container=atom-operator-gazebo ;; monitor) container=atom-operator-monitor ;; esac
    selected=(docker stop --timeout 5 "${container}") ;;
  demo)
    case "${demo}" in
      arm) if "${gui}";then selected=(bash "${repo_root}/scripts/lib/desktop.sh" arm);else selected=(bash "${repo_root}/scripts/lib/baseline.sh" arm);fi ;;
      dynamics|transfer|smoke) selected=(bash "${repo_root}/scripts/lib/baseline.sh" "${demo}") ;;
      camera) if "${gui}";then backend=desktop;mode=camera;else backend=camera;mode=probe;fi;selected=(bash "${repo_root}/scripts/lib/${backend}.sh" "${mode}" "${camera}" "${dx}" "${dy}" "${dyaw}") ;;
      approach) "${gui}" || fail 'For approach + web monitoring, use sim. The desktop approach demo requires --gui.';selected=(bash "${repo_root}/scripts/lib/desktop.sh" approach "${camera}" "${dx}" "${dy}" "${dyaw}" "${distance}") ;;
    esac ;;
esac
if "${dry_run}";then printf '%q ' "${selected[@]}";printf '\n';exit 0;fi
cd "${repo_root}"
exec "${selected[@]}"
