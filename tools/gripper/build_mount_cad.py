"""Reproduce the active flange V2, ESP32 V1 and camera V3 CAD only.

Reads hardware/end effector/cad_parameters.json and cad_manifest.json.
Writes an isolated output directory; does not overwrite released hardware files.
"""
import argparse
import json
import math
from pathlib import Path

import cadquery as cq
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[2]
HARDWARE=ROOT/'hardware/end effector'
def box(bounds):
    (x0,x1),(y0,y1),(z0,z1)=bounds
    return cq.Workplane('XY').box(x1-x0,y1-y0,z1-z0,centered=False).translate((x0,y0,z0))


def cylinder(radius,start,end,axis,centre):
    p=list(centre);p.insert(axis,start)
    direction=[0,0,0];direction[axis]=1
    return cq.Solid.makeCylinder(radius,end-start,cq.Vector(*p),cq.Vector(*direction))


def clamp(part,p):
    for yl in p['clip_y_intervals_mm']:
        part=part.union(box([p['clip_x_limits_mm'],yl,p['clip_z_limits_mm']]))
        for x in p['clamp_hole_x_mm']:
            part=part.cut(cylinder(p['clamp_hole_diameter_mm']/2,yl[0]-1,yl[1]+1,
                                   1,[x,p['clamp_hole_z_mm']]))
    return part


def esp32(p):
    x,y,z=p['base_size_xyz_mm']
    part=box([[0,x],[0,y],[0,z]])
    for centre in p['board_holes_xy_mm']:
        part=part.cut(cylinder(p['board_hole_diameter_mm']/2,-1,z+1,2,centre))
    return clamp(part,p).clean()


def flange(p):
    x,y,z=p['backplate_size_xyz_mm'];centre=p['axis_yz_mm']
    part=box([[0,x],[0,y],[0,z]])
    t0,t1=p['taper_x_limits_mm'];r0,r1=p['taper_radii_mm']
    part=part.union(cq.Solid.makeCone(r0,r1,t1-t0,cq.Vector(t0,*centre),cq.Vector(1,0,0)))
    for name in ['barrel','face','pilot']:
        a,b=p[name+'_x_limits_mm']
        part=part.union(cylinder(p[name+'_radius_mm'],a,b,0,centre))
    maximum=p['pilot_x_limits_mm'][1]
    part=part.cut(cylinder(p['centre_bore_diameter_mm']/2,-1,maximum+1,0,centre))
    for angle in p['bolt_angles_deg']:
        rad=math.radians(angle);r=p['bolt_circle_radius_mm']
        c=[centre[0]+r*math.cos(rad),centre[1]+r*math.sin(rad)]
        part=part.cut(cylinder(p['bolt_hole_diameter_mm']/2,-1,maximum+1,0,c))
        a,b=p['counterbore_x_limits_mm']
        part=part.cut(cylinder(p['counterbore_diameter_mm']/2,a,b,0,c))
    for c in p['plate_holes_yz_mm']:
        part=part.cut(cylinder(p['plate_hole_diameter_mm']/2,-1,x+1,0,c))
    a,b=p['pin_hole_x_limits_mm']
    part=part.cut(cylinder(p['pin_hole_diameter_mm']/2,a,b,0,p['pin_hole_yz_mm']))
    return part.clean()


def distance_checks(source,target,random_count,seed):
    """Deterministic bidirectional mesh-surface sampling; NOT exact Hausdorff."""
    results={}
    for label,a,b in [('source_to_rebuilt',source,target),('rebuilt_to_source',target,source)]:
        random,_=trimesh.sample.sample_surface(a,random_count,seed=seed)
        points=np.vstack([a.vertices,a.triangles_center,random])
        distances=[]
        for i in range(0,len(points),512):
            _,d,_=trimesh.proximity.closest_point(b,points[i:i+512]);distances.append(d)
        d=np.concatenate(distances)
        results[label]=dict(vertex_count=len(a.vertices),triangle_centroid_count=len(a.faces),
                            random_surface_count=random_count,total_sample_count=len(points),
                            seed=seed,max_mm=float(d.max()),rms_mm=float(np.sqrt(np.mean(d*d))),
                            percentile_99_mm=float(np.percentile(d,99)))
    return results


def camera_v3(p):
    cy=p['clip_centre_y_mm'];gap=p['clip_gap_mm'];wall=p['clip_wall_mm']
    il,ih=cy-gap/2,cy+gap/2;ol,oh=il-wall,ih+wall
    x0,x1=p['beam_x_limits_mm'];cx0,cx1=p['clip_x_limits_mm']
    z0=p['clip_height_mm'];z1=z0+p['beam_thickness_mm'];over=p['beam_side_overhang_mm']
    part=box([[x0,x1],[ol-over,oh+over],[z0,z1]])
    for lo,hi in [(ol,il),(ih,oh)]:part=part.union(box([[cx0,cx1],[lo,hi],[0,z0]]))
    edges=[e for e in part.val().Edges() if abs(e.Center().z-z0)<1e-5
           and min(abs(e.Center().y-ol),abs(e.Center().y-oh))<1e-5 and abs(e.Length()-(cx1-cx0))<1e-5]
    if len(edges)!=2:raise ValueError('Expected two external clip roots')
    part=part.newObject(edges).fillet(p['root_fillet_mm'])
    px1=x0+p['rear_plate_thickness_mm'];w=p['rear_plate_width_mm']
    pz0=z1-p['rear_plate_overlap_mm'];pz1=pz0+p['rear_plate_height_mm']
    plate=box([[x0,px1],[cy-w/2,cy+w/2],[pz0,pz1]])
    plate=plate.edges('|X').fillet(p['rear_plate_corner_radius_mm'])
    part=part.union(plate)
    for y in [ol,ih]:
        plane=cq.Plane(origin=(0,y,0),xDir=(1,0,0),normal=(0,-1,0))
        rib=cq.Workplane(plane).polyline([(px1,z1),(px1+p['rib_run_mm'],z1),
                                        (px1,z1+p['rib_height_mm'])]).close().extrude(-p['rib_thickness_mm'])
        part=part.union(rib)
    edges=[e for e in part.val().Edges() if abs(e.Center().x-px1)<1e-5
           and abs(e.Center().z-z1)<1e-5 and abs(e.Length()-gap)<1e-5]
    if len(edges)!=1:raise ValueError('Expected central plate root')
    part=part.newObject(edges).fillet(p['root_fillet_mm'])
    for x in p['clamp_hole_x_mm']:
        part=part.cut(cylinder(p['clamp_hole_diameter_mm']/2,ol-1,oh+1,1,[x,p['clamp_hole_z_mm']]))
    hole_z=z1+p['camera_bottom_clearance_mm']+p['camera_size_width_height_depth_mm'][1]/2
    for y in [cy-p['rear_hole_spacing_mm']/2,cy+p['rear_hole_spacing_mm']/2]:
        part=part.cut(cylinder(p['rear_hole_diameter_mm']/2,x0-1,px1+1,0,[y,hole_z]))
    return part.clean()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True,help='New directory; use tmp/ for review builds')
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    params=json.loads((HARDWARE/'cad_parameters.json').read_text())
    manifest=json.loads((HARDWARE/'cad_manifest.json').read_text())
    builders={'flange_adapter_v2':flange,'esp32_bracket_v1':esp32,'camera_bracket_v3':camera_v3}
    results=[]
    for entry in manifest['parts']:
        name=entry['name'];part=builders[name](params[name]);solid=part.val()
        if not solid.isValid() or len(part.solids().vals())!=1:raise ValueError(name+': invalid solid')
        if name=='camera_bracket_v3':translation=entry['assembly_to_cad_translation_mm']
        else:translation=entry['print_to_cad_translation_mm']
        cad=part.translate(tuple(translation))
        cq.exporters.export(cad,str(args.output/entry['step']))
        original=cq.importers.importStep(str(HARDWARE/entry['step'])).val()
        verror=abs(cad.val().Volume()-original.Volume())/original.Volume()
        if verror>1e-6:raise ValueError(name+': baseline volume mismatch')
        # The print orientation is the inverse of the recorded print-to-CAD matrix.
        if name=='camera_bracket_v3':
            printable=part.rotate((0,0,0),(1,0,0),90).translate(tuple(entry['post_rotation_translation_mm']))
        else:printable=part
        dest=args.output/entry['print_stl']
        cq.exporters.export(printable,str(dest),tolerance=.005,angularTolerance=.04)
        mesh=trimesh.load(dest);source=trimesh.load(HARDWARE/entry['print_stl'])
        if not mesh.is_watertight or not mesh.is_winding_consistent or len(mesh.split())!=1:
            raise ValueError(name+': mesh topology')
        distances=distance_checks(source,mesh,8000,20261008)
        if max(d['max_mm'] for d in distances.values())>.02:raise ValueError(name+': baseline surface mismatch')
        results.append(dict(name=name,volume_relative_difference=verror,surface_distance_sampling=distances,
                            valid_single_solid=True,watertight=True))
        print(name, 'verified; sampled max mm',max(d['max_mm'] for d in distances.values()),flush=True)
    (args.output/'verification.json').write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':main()
