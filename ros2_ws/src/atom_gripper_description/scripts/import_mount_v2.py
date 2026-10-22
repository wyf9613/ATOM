#!/usr/bin/env python3
"""Import the active flange V2 / ESP32 V1 / camera V3 print meshes into Xacro.

All transforms and provenance come from the hardware manifest. No hardware access.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[4]
PACKAGE=ROOT/'ros2_ws/src/atom_gripper_description'
HARDWARE=ROOT/'hardware/end effector'
OUT=PACKAGE/'meshes/generated/mount'


def main():
    manifest=json.loads((HARDWARE/'cad_manifest.json').read_text())
    R=np.array(manifest['cad_to_gripper_R'])
    translation=np.array(manifest['cad_to_gripper_translation_mm'])
    flange_translation=np.array([-43.494,-22.225,manifest['cad_flange_centre_mm'][0]])
    OUT.mkdir(parents=True,exist_ok=True)
    fmt=lambda v:' '.join(f'{x:.9f}' for x in v)
    xml=['<?xml version="1.0"?>','<robot xmlns:xacro="http://www.ros.org/wiki/xacro">',
         '  <!-- Nominal CAD review only; inertial and camera calibration are unmeasured. -->',
         '  <xacro:macro name="atom_mount_v2" params="parent gripper_base prefix:=\'\'">']
    records=[]
    for part in manifest['parts']:
        path=HARDWARE/part['print_stl']
        expected=part['files_sha256'][path.name]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Mesh changed: '+str(path))
        mesh=trimesh.load(path);mesh.apply_transform(np.array(part['print_to_cad_transform_mm']))
        role=part['role'];is_flange=role=='flange_adapter';t=flange_translation if is_flange else translation
        mesh.export(OUT/(role+'.stl'))
        v=mesh.vertices@R.T+t;lo=v.min(0)/1000;hi=v.max(0)/1000
        centre=(lo+hi)/2;size=hi-lo+.001
        record=dict(name=role,revision=part['name'],source_print_stl=str(path.relative_to(ROOT)),
                    source_sha256=expected,print_to_cad_transform_mm=part['print_to_cad_transform_mm'],
                    restored_cad_bounds_mm=mesh.bounds.tolist(),link_bounds_m=[lo.tolist(),hi.tolist()],
                    collision_padding_per_side_m=.0005)
        records.append(record)
        parent='parent' if is_flange else 'gripper_base'
        xml.extend([f'    <link name="${{prefix}}{role}">',
                    f'      <visual><origin xyz="{fmt(t/1000)}" rpy="1.5707963267948966 1.5707963267948966 0"/>',
                    f'        <geometry><mesh filename="package://atom_gripper_description/meshes/generated/mount/{role}.stl" scale="0.001 0.001 0.001"/></geometry>',
                    '        <material name="atom_mount"><color rgba="0.25 0.45 0.65 1"/></material></visual>',
                    f'      <collision><origin xyz="{fmt(centre)}"/><geometry><box size="{fmt(size)}"/></geometry></collision>',
                    '    </link>',
                    f'    <joint name="${{prefix}}{role}_joint" type="fixed"><parent link="${{{parent}}}"/><child link="${{prefix}}{role}"/></joint>'])
    # Housing envelope only: deliberately no uncalibrated driver/optical TF names.
    camera=next(p for p in manifest['parts'] if p['role']=='camera_bracket')
    bounds=np.array(camera['rear_camera_envelope_assembly_mm'])+camera['assembly_to_cad_translation_mm']
    centre=R@bounds.mean(0)+translation
    size=np.abs(R)@(bounds[1]-bounds[0])
    xml.extend(['    <!-- Nominal D435i housing; USB/cables/optical TF and inertial data absent. -->',
                '    <link name="${prefix}d435i_body">',
                f'      <visual><geometry><box size="{fmt(size/1000)}"/></geometry>',
                '        <material name="atom_camera"><color rgba="0.55 0.57 0.60 1"/></material></visual>',
                f'      <collision><origin xyz="0 0 0"/><geometry><box size="{fmt(size/1000+.001)}"/></geometry></collision>',
                '    </link>',
                f'    <joint name="${{prefix}}d435i_body_joint" type="fixed"><parent link="${{gripper_base}}"/><child link="${{prefix}}d435i_body"/><origin xyz="{fmt(centre/1000)}" rpy="0 0 0"/></joint>',
                '  </xacro:macro>','</robot>'])
    (PACKAGE/'urdf/atom_mount_v2.urdf.xacro').write_text('\n'.join(xml)+'\n')
    (OUT/'manifest.json').write_text(json.dumps(dict(
        hardware_manifest='hardware/end effector/cad_manifest.json',
        hardware_manifest_sha256=hashlib.sha256((HARDWARE/'cad_manifest.json').read_bytes()).hexdigest(),
        cad_to_gripper_R=R.tolist(),cad_flange_centre_mm=manifest['cad_flange_centre_mm'],
        gripper_mount_z_m=manifest['gripper_mount_z_mm']/1000,parts=records,
        d435i_body=dict(centre_in_gripper_m=(centre/1000).tolist(),size_m=(size/1000).tolist(),
                        collision_padding_per_side_m=.0005,calibrated=False),
        notes=['Active revisions: flange V2, ESP32 V1, camera V3.',
               'CAD frame and nominal camera envelope only; physical fit, mass/CoM, TCP and optical TF unmeasured.',
               'No PCB, cables, fasteners or carried-object envelopes.']),indent=2)+'\n')
    print('Imported active mount meshes and nominal D435i envelope')


if __name__=='__main__':main()
