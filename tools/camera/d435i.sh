#!/usr/bin/env bash
# Camera-only hardware preparation; no arm motion.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"
operation="${1:---help}"
case "${operation}" in
  --help|-h)
    echo 'Usage: tools/camera/d435i.sh enumerate|start [serial_no]|check|record'
    echo 'Start only the D435i driver; check/record require it in another terminal.'
    exit 0 ;;
  enumerate|start|check|record) ;;
  *) echo 'Unknown camera operation' >&2; exit 2 ;;
esac
if [[ "${operation}" == enumerate || "${operation}" == start ]]; then
  [[ -d /dev/bus/usb ]] || { echo 'No USB bus exposed on this host' >&2; exit 1; }
  usb_args=(--user root --device /dev/bus/usb:/dev/bus/usb)
  # Native V4L2/HID backend: expose only Intel USB camera nodes, not every webcam.
  for class_name in video4linux hidraw; do
    for entry in /sys/class/"${class_name}"/*; do
      [[ -e "${entry}/device" ]] || continue
      ancestor="$(readlink -f "${entry}/device")"
      while [[ "${ancestor}" != / && "${ancestor}" != /sys ]]; do
        if [[ -r "${ancestor}/idVendor" ]]; then
          if [[ "$(cat "${ancestor}/idVendor")" == 8086 && -e "/dev/$(basename "${entry}")" ]]; then
            usb_args+=(--device "/dev/$(basename "${entry}")")
          fi
          break
        fi
        ancestor="$(dirname "${ancestor}")"
      done
    done
  done
else
  usb_args=()
fi
# Separate domain prevents camera tests joining the simulation/arm domain.
docker run --rm -i --network host --ipc host "${usb_args[@]}" \
  -v "${repo_root}:/workspace" \
  -e ROS_DOMAIN_ID="${ATOM_CAMERA_DOMAIN_ID:-43}" \
  -e ATOM_CAMERA_OPERATION="${operation}" -e ATOM_CAMERA_SERIAL="${2:-}" \
  atom-xarm850-jazzy-harmonic:latest bash -lc '
    set -eo pipefail
    source /opt/ros/jazzy/setup.bash
    case "${ATOM_CAMERA_OPERATION}" in
      enumerate) /opt/ros/jazzy/bin/rs-enumerate-devices ;;
      start)
        serial_args=()
        if [[ -n "${ATOM_CAMERA_SERIAL}" ]]; then serial_args=("serial_no:=_${ATOM_CAMERA_SERIAL}"); fi
        ros2 launch /workspace/ros2_ws/src/atom_camera_description/launch/d435i_hardware.launch.py "${serial_args[@]}"
        ;;
      check) python3 /workspace/tools/camera/check_d435i.py ;;
      record)
        output="/workspace/tmp/camera_calibration/d435i_$(date +%Y%m%d_%H%M%S)"
        mkdir -p /workspace/tmp/camera_calibration
        ros2 bag record -o "${output}" /atom/wrist_camera/color/image_raw \
          /atom/wrist_camera/color/camera_info /atom/wrist_camera/depth/image_rect_raw \
          /atom/wrist_camera/depth/camera_info /atom/wrist_camera/aligned_depth_to_color/image_raw \
          /atom/wrist_camera/aligned_depth_to_color/camera_info /atom/wrist_camera/imu \
          /tf /tf_static /diagnostics
        ;;
    esac
  '
