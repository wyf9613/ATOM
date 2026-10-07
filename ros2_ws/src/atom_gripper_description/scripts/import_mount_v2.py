#!/usr/bin/env python3
"""Restore the verified print-pack coordinates and regenerate CAD collision envelopes.

Run from repository root with numpy and trimesh installed. Does not modify raw CAD.
"""
import zipfile,json,hashlib,io
from pathlib import Path
import numpy as np,trimesh
root=Path.cwd(); pkg=root/'ros2_ws/src/atom_gripper_description'; z=zipfile.ZipFile(root/'hardware/end effector/ATOM_three_parts_20261005.zip'); manifest=json.loads(z.read('export_manifest.json'))
out=pkg/'meshes/generated/mount_v2'; out.mkdir(parents=True,exist_ok=True)
R=np.array([[0,1,0],[0,0,-1],[-1,0,0]])
entries=[]
xml=['<?xml version="1.0"?>','<robot xmlns:xacro="http://www.ros.org/wiki/xacro">','  <!-- CAD-only placement; no measured mass/CoM. Not a dynamics model. -->','  <xacro:macro name="atom_mount_v2" params="parent gripper_base prefix:=\'\'">']
for p in manifest['parts']:
 data=z.read(p['filename']); assert hashlib.sha256(data).hexdigest()==p['sha256']
 mesh=trimesh.load(io.BytesIO(data),file_type='stl'); mesh.apply_translation(-np.array(p['translation_xyz_mm']))
 name={'camera_bracket_v2_mm.stl':'camera_bracket','esp32_bracket_v1_mm.stl':'esp32_bracket','flange_adapter_v2_mm.stl':'flange_adapter'}[p['filename']]
 flange=name=='flange_adapter'; t=np.array([-43.494,-22.225,80.8 if flange else 28.836])
 v=mesh.vertices@R.T+t; lo=v.min(0)/1000; hi=v.max(0)/1000
 # 0.5 mm per-side CAD-envelope inflation, not a validated safety clearance.
 centre=(hi+lo)/2; size=hi-lo+.001
 mesh.export(out/(name+'.stl'))
 entries.append(dict(name=name,zip_member=p['filename'],source_sha256=p['sha256'],restored_cad_bounds_mm=mesh.bounds.tolist(),link_bounds_m=[lo.tolist(),hi.tolist()],collision_padding_per_side_m=.0005))
 fmt=lambda values:' '.join(f'{x:.9f}' for x in values)
 xml.extend([f'    <link name="${{prefix}}{name}">',f'      <visual><origin xyz="{fmt(t/1000)}" rpy="1.5707963267948966 1.5707963267948966 0"/>',f'        <geometry><mesh filename="package://atom_gripper_description/meshes/generated/mount_v2/{name}.stl" scale="0.001 0.001 0.001"/></geometry>',f'        <material name="atom_mount"><color rgba="0.25 0.45 0.65 1"/></material></visual>',f'      <collision><origin xyz="{fmt(centre)}"/><geometry><box size="{fmt(size)}"/></geometry></collision>','    </link>',f'    <joint name="${{prefix}}{name}_joint" type="fixed"><parent link="${{{"parent" if flange else "gripper_base"}}}"/><child link="${{prefix}}{name}"/></joint>'])
xml.extend(['  </xacro:macro>','</robot>'])
(pkg/'urdf/atom_mount_v2.urdf.xacro').write_text('\n'.join(xml)+'\n')
(out/'manifest.json').write_text(json.dumps(dict(source_archive='hardware/end effector/ATOM_three_parts_20261005.zip',archive_sha256=hashlib.sha256(Path(z.filename).read_bytes()).hexdigest(),cad_to_gripper_R=R.tolist(),cad_flange_centre_mm=[80.8,43.494,-22.225],gripper_mount_z_m=.051964,parts=entries,notes=['Restored CAD coordinates by subtracting export translation; no rotations in archive.','Flange face x=80.8 mm inferred from planar face and 31.45 mm pilot at x=82.8 mm.','CAD placement only; flange yaw, actual hardware fit, camera/PCB/cables and mass/TCP unmeasured.']),indent=2)+'\n')
# Replace pad-only/body-short collisions with complete visual-mesh AABBs.
path=pkg/'urdf/atom_gripper.urdf.xacro'; content=path.read_text()
import re
for name in ['gripper_base','left_finger','right_finger']:
 mesh=trimesh.load(pkg/'meshes/generated'/({'gripper_base':'base'}.get(name,name)+'.stl'))
 v=mesh.vertices@R.T+[-43.494,-22.225,28.836]; lo=v.min(0)/1000; hi=v.max(0)/1000
 collision=f'<collision>\n        <!-- Full inherited mesh AABB + 0.5 mm per side; CAD-only envelope. -->\n        <origin xyz="{fmt((hi+lo)/2)}"/>\n        <geometry><box size="{fmt(hi-lo+.001)}"/></geometry>\n      </collision>'
 pattern=r'(<link name="\$\{prefix\}'+name+r'">.*?)(<collision>.*?</collision>)'
 content,n=re.subn(pattern,lambda m:m[1]+collision,content,count=1,flags=re.S); assert n==1
path.write_text(content)
