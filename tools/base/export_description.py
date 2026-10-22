#!/usr/bin/env python3
"""Export the modular whole-robot review model without ROS, CAN or serial access."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/gripper'))
from export_description import expand


def export(vendor, output, top_height=.15, pedestal_height=.805, yaw=0.):
    if not all(math.isfinite(x) for x in (top_height, pedestal_height, yaw)) or min(top_height,pedestal_height)<=0:
        raise ValueError('Finite positive heights and finite yaw required')
    pin = subprocess.check_output(['git','-C',str(vendor),'rev-parse','HEAD'],text=True).strip()
    if pin != '3dc2b5e8294758d96b54b15fa5920d581b7cbb3d':
        raise ValueError('Vendor checkout must match D-007')
    packages = {n: ROOT/'ros2_ws/src'/n for n in (
        'atom_mobile_description','atom_xarm_description','atom_gripper_description')}
    packages.update({n:vendor/n for n in ('xarm_description','xarm_moveit_config')})
    mappings = {'base_top_height':str(top_height),'pedestal_height':str(pedestal_height),'arm_mount_yaw':str(yaw)}
    output.mkdir(parents=True, exist_ok=False)
    for suffix in ('urdf','srdf'):
        source = packages['atom_mobile_description']/suffix/f'atom_mobile.{suffix}.xacro'
        xml = expand(source,packages,mappings)
        ET.fromstring(xml)
        path = output/f'atom_mobile.{suffix}'
        path.write_text(xml+'\n')
        print(path)
    (output/'mount_parameters.json').write_text(json.dumps({
        'base_top_height_m':top_height,'pedestal_height_m':pedestal_height,
        'arm_mount_yaw_rad':yaw,'arm_base_xy_m':[0.,0.], 'vendor_commit':pin,
        'evidence':{'pedestal_height':'user supplied 2026-10-22; measurement uncertainty not supplied',
                    'base_top_height':'nominal inherited simulation value, unmeasured',
                    'yaw':'review setting only; user left physical direction unconfirmed'},
        'scope':'geometry review only; no measured base/stand inertia, calibrated optical TF or hardware acceptance',
    },indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vendor-root',type=Path,default=ROOT/'tmp/xarm_ros2')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--base-top-height',type=float,default=.15)
    parser.add_argument('--pedestal-height',type=float,default=.805)
    parser.add_argument('--arm-mount-yaw',type=float,default=0.)
    args=parser.parse_args()
    export(args.vendor_root,args.output,args.base_top_height,args.pedestal_height,args.arm_mount_yaw)
