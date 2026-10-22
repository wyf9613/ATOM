#!/usr/bin/env python3
"""Orthographic mounting audit from original URDF visual meshes at zero joints."""
from pathlib import Path
import argparse
import json
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection


def render(source, output):
    root=Path(__file__).resolve().parents[2]
    packages={'xarm_description':root/'tmp/xarm_ros2/xarm_description',
              'atom_gripper_description':root/'ros2_ws/src/atom_gripper_description'}
    robot=ET.parse(source).getroot()
    def origin(element):
        if element is None:return np.eye(4)
        m=trimesh.transformations.euler_matrix(*map(float,element.get('rpy','0 0 0').split()))
        m[:3,3]=list(map(float,element.get('xyz','0 0 0').split()))
        return m
    transforms={'base_link':np.eye(4)}
    pending=list(robot.findall('joint'))
    while pending:
        available=[j for j in pending if j.find('parent').get('link') in transforms]
        if not available:raise ValueError('Disconnected model')
        for joint in available:
            transforms[joint.find('child').get('link')]=transforms[joint.find('parent').get('link')]@origin(joint.find('origin'))
            pending.remove(joint)
    # Audit the frame positions before drawing. A material or view change must
    # never silently alter the mounting geometry to make the picture look right.
    base=transforms['base_link'][:3,3]
    mount=transforms['link_base'][:3,3]
    top=transforms['base_top'][:3,3]
    assert np.allclose(base[:2],mount[:2],atol=1e-10), 'Arm/base XY centres differ'
    assert abs((mount[2]-top[2])-.805)<1e-9, 'Unexpected top-to-arm mount height'
    meshes=[]
    original_base_bounds=None
    for link in robot.findall('link'):
        name=link.get('name')
        for visual in link.findall('visual'):
            geo=visual.find('geometry');mesh=geo.find('mesh');box=geo.find('box');cylinder=geo.find('cylinder')
            if mesh is not None:
                package,relative=mesh.get('filename').removeprefix('package://').split('/',1)
                shape=trimesh.load(packages[package]/relative,force='mesh')
                shape.apply_scale(list(map(float,mesh.get('scale','1 1 1').split())))
                if name=='link_base':original_base_bounds=shape.bounds.tolist()
            elif box is not None:shape=trimesh.creation.box(extents=list(map(float,box.get('size').split())))
            elif cylinder is not None:shape=trimesh.creation.cylinder(radius=float(cylinder.get('radius')),height=float(cylinder.get('length')),sections=24)
            else:continue
            shape.apply_transform(transforms[name]@origin(visual.find('origin')))
            if name=='link_base':color='#e99530'
            elif name=='arm_pedestal':color='#bfc8cf'
            elif name.startswith(('base','left_wheel','right_wheel')):color='#303943'
            elif name in ['camera_bracket','esp32_bracket','flange_adapter','d435i_body','gripper_base','left_finger','right_finger']:color='#3d8a9f'
            else:color='#9daab5'
            meshes.append((shape,color))
    triangles=np.concatenate([s.triangles for s,c in meshes])
    from matplotlib.colors import to_rgb
    colors=np.concatenate([np.tile(to_rgb(c),(len(s.faces),1)) for s,c in meshes])
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    light=np.array([-.3,-.5,1.]);light/=np.linalg.norm(light)
    colors=np.clip(colors*(.7+.3*np.abs(normals@light))[:,None],0,1)
    fig,axes=plt.subplots(1,2,figsize=(11.5,11))
    max_z=max(1.9,float(triangles[:,:,2].max())+.12)
    for ax,horizontal,depth,title in zip(axes,[0,1],[1,0],['FRONT — looking along +Y','SIDE — looking along -X']):
        # Orthographic projection; sort far surfaces first and retain all faces.
        d=triangles[:,:,depth].mean(axis=1)
        order=np.argsort(-d if depth==1 else d)
        projected=triangles[:,:,[horizontal,2]]
        ax.add_collection(PolyCollection(projected[order],facecolors=colors[order],edgecolors='none',rasterized=True))
        ax.axvline(0,color='#b72e37',ls='--',lw=1.2,zorder=5)
        ax.scatter([base[horizontal],mount[horizontal]],[top[2],mount[2]],s=95,
                   marker='+',color='#b72e37',linewidths=2,zorder=6)
        ax.annotate('Base top centre\n(0, 0, 150) mm',xy=(0,top[2]),xytext=(-.43,.34),
                    fontsize=9,color='#7f2430',arrowprops={'arrowstyle':'->','color':'#7f2430'},zorder=7)
        ax.annotate('Arm mounting centre\n(0, 0, 955) mm',xy=(0,mount[2]),xytext=(-.43,.76),
                    fontsize=9,color='#7f2430',arrowprops={'arrowstyle':'->','color':'#7f2430'},zorder=7)
        dimension_x=.41
        ax.annotate('',xy=(dimension_x,mount[2]),xytext=(dimension_x,top[2]),
                    arrowprops={'arrowstyle':'<->','color':'#9a5910','lw':1.4})
        ax.text(dimension_x+.025,(mount[2]+top[2])/2,'805 mm',rotation=90,
                ha='left',va='center',fontsize=10,color='#9a5910')
        for z in [top[2],mount[2]]:ax.plot([0,dimension_x],[z,z],color='#9a5910',lw=.7,ls=':')
        axis='X' if horizontal==0 else 'Y'
        ax.set(xlim=(-.47,.51),ylim=(0,max_z),xlabel=f'{axis} [m]',ylabel='Z [m]')
        ax.set_aspect('equal');ax.set_title(title,fontsize=11)
        ax.grid(True,color='#dddddd',linewidth=.5);ax.set_axisbelow(True)
    fig.suptitle('ATOM mounting-centre audit\nOriginal visual meshes; zero joint angles; red line: X = Y = 0',fontsize=15,y=.97)
    fig.text(.08,.035,'Orange: arm base. Blue: current tool assembly. Support/chassis geometry is provisional.\n150 mm base-top height and 955 mm mounting height are nominal model values; only the 805 mm offset is user supplied.',fontsize=9,color='#555555')
    fig.subplots_adjust(left=.07,right=.95,bottom=.11,top=.90,wspace=.18)
    fig.savefig(output,dpi=160,bbox_inches='tight');plt.close(fig)
    report={'condition':'source URDF visual geometry at zero joints; no physical measurements',
            'base_link_world_m':base.tolist(),'base_top_world_m':top.tolist(),
            'arm_base_world_m':mount.tolist(),'arm_minus_base_xy_m':(mount[:2]-base[:2]).tolist(),
            'top_to_arm_height_m':float(mount[2]-top[2]),
            'vendor_arm_base_visual_local_bounds_m':original_base_bounds,
            'rendering':'front/side orthographic projection of original visual triangles; no convex hull replacement'}
    output.with_name('mount_centre_check.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('urdf',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();render(args.urdf,args.output)
