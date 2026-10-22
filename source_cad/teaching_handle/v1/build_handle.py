"""Independent radial PETG teaching-handle fit prototype; mm throughout.

Run with the project's CadQuery 2.6.1 runtime. Backplate/raw CAD are read only.
The print STL lies on its tool-side face with the flange axis vertical.
Geometry checks do not qualify printed strength or physical compatibility.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import zipfile
import numpy as np
import cadquery as cq
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
PACK=ROOT/'source_cad/print_pack/2026-10-21_handle'
sys.path.insert(0,str(ROOT/'source_cad/print_pack'))
from export_stls import check_mesh
sys.path.insert(0,str(ROOT/'source_cad/backplate/v2'))
from render_cad import render

P=dict(status='FIT/PRINT PROTOTYPE; hardware strength and wrist clearance unverified',
       units='mm',material='PETG provisional; user said probably pteg; exact grade unknown',
       ring_od_mm=63.0,ring_axial_thickness_mm=16.0,central_passage_mm=24.0,
       screw_pcd_mm=50.0,screw_clearance_mm=6.8,screw_angles_deg=[45,135,225,315],
       tool_side_pilot_recess_mm=31.8,tool_side_pilot_recess_depth_mm=2.4,
       tool_side_entry_chamfer_mm=0.3,internal_transition_45deg_length_mm=3.9,
       robot_side_pilot_od_provisional_mm=31.45,robot_side_pilot_height_mm=2.0,
       robot_side_pilot_tip_chamfer_mm=0.3,locator_relief_hole_mm=6.4,
       inherited_locator_yz_mm=[25.0,0.0],grip_tip_radial_y_mm=141.0,
       grip_axis='local +Y, collinear with flange center in YZ; no elbow',
       palm_capsule_radius_mm=13.0,palm_capsule_center_x_mm=13.0,
       palm_capsule_end_centres_y_mm=[56.0,125.0],
       structural_core_axial_thickness_mm=16.0,
       structural_core_edge_fillet_mm=0.8,ring_flat_contact_outer_diameter_mm=61.4,
       palm_to_core_blend_mm=0.4,
       root_transition='G1 tangent cubic Bezier in flange plane; continuous 16 mm core',
       fit_coupon_ring_thickness_mm=7.0,
       print_orientation='STL X=CAD Y, STL Y=CAD Z, STL Z=CAD X; translated to >=0',
       tessellation_linear_mm=0.02,tessellation_angular_rad=0.08)

def cyl(r,x,l,y=0,z=0):
    return cq.Solid.makeCylinder(r,l,cq.Vector(x,y,z),cq.Vector(1,0,0))

def interface(thickness):
    s=cyl(P['ring_od_mm']/2,0,thickness)
    # Female seat receives existing backplate's 31.45 x 2 mm pilot. The 45 deg
    # internal transition avoids an unsupported circular pocket roof in print.
    cuts=[cyl(12,-1,thickness+5),cyl(15.9,-1,3.4),
          cq.Solid.makeCone(16.2,15.9,.3,cq.Vector(0,0,0),cq.Vector(1,0,0)),
          cq.Solid.makeCone(15.9,12,3.9,cq.Vector(2.4,0,0),cq.Vector(1,0,0))]
    for cut in cuts: s=s.cut(cut)
    # Male pilot on robot face: nominal inherited fit, not a qualified printed fit.
    pilot=cyl(15.725,thickness,1.7).fuse(
        cq.Solid.makeCone(15.725,15.425,.3,cq.Vector(thickness+1.7,0,0),cq.Vector(1,0,0)))
    s=s.fuse(pilot).cut(cyl(12,-1,thickness+5))
    return s.clean()

def holes(s):
    for deg in P['screw_angles_deg']:
        a=math.radians(deg)
        s=s.cut(cyl(3.4,-1,40,25*math.cos(a),25*math.sin(a)))
    # Clearance only; an alignment pin and its engagement length are not selected.
    s=s.cut(cyl(3.2,-1,40,25,0))
    return s.clean()

def core_outline():
    """Smooth load path from circular ring to straight radial grip, without elbow."""
    v=math.sqrt(31.5**2-22.5**2)
    p=cq.Workplane('YZ').moveTo(22.5,v).threePointArc((-31.5,0),(22.5,-v))
    p=p.bezier([(29,-v+6.5*22.5/v),(35,-15),(45,-15)],includeCurrent=True)
    p=p.bezier([(63,-15),(70,-14),(85,-14)],includeCurrent=True)
    p=p.bezier([(105,-14),(114,-15),(126,-15)],includeCurrent=True)
    p=p.threePointArc((141,0),(126,15))
    p=p.bezier([(114,15),(105,14),(85,14)],includeCurrent=True)
    p=p.bezier([(70,14),(63,15),(45,15)],includeCurrent=True)
    p=p.bezier([(35,15),(29,v-6.5*22.5/v),(22.5,v)],includeCurrent=True)
    return p.close()

def dimensions(s):
    b=Bnd_Box(); BRepBndLib.AddOptimal_s(s.wrapped,b,False,False)
    x,y,z,u,v,w=b.Get()
    return [u-x,v-y,w-z]

def print_pose(s):
    p=s.rotate((0,0,0),(1,1,1),-120)
    b=Bnd_Box(); BRepBndLib.AddOptimal_s(p.wrapped,b,False,False)
    x,y,z,*_=b.Get()
    shift=[-x,-y,-z]
    return p.translate(tuple(shift)),shift

def valid(s): return s.isValid() and len(s.Solids())==1

def export_part(name,s):
    assert valid(s),name
    path=OUT/(name+'.step'); cq.exporters.export(s,str(path))
    loaded=cq.importers.importStep(str(path)).val()
    assert valid(loaded) and abs(loaded.Volume()/s.Volume()-1)<1e-7
    printable,shift=print_pose(s)
    target=PACK/(name+'_mm.stl')
    assert printable.exportStl(str(target),tolerance=.02,angularTolerance=.08,relative=False,ascii=False)
    check=check_mesh(target,np.array(dimensions(printable)),s.Volume())
    check.update(source_step=str(path.relative_to(ROOT)).replace('\\','/'),
        step_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        step_roundtrip_valid_single_solid=True,cad_dimensions_xyz_mm=dimensions(s),
        translation_after_rotation_xyz_mm=shift,cad_volume_mm3=s.Volume(),
        print_filename=target.name)
    return check

def main():
    OUT.mkdir(parents=True,exist_ok=True); PACK.mkdir(parents=True,exist_ok=True)
    back_path=ROOT/'source_cad/backplate/v2/reinforced_backplate_v2.step'
    back_hash=hashlib.sha256(back_path.read_bytes()).hexdigest()
    base=interface(16)
    blank=core_outline().extrude(16).val()
    # Small outer edge rounds preserve broad contact lands; the in-plane root
    # outline is tangent by construction. No sharp concave elbow is introduced.
    perimeter=[e for e in blank.Edges() if e.BoundingBox().xlen<1e-6]
    core=blank.fillet(.8,perimeter).clean()
    # Analytic capsule makes a smooth palm surface without spline overshoot.
    grip=cq.Solid.makeCylinder(13,69,cq.Vector(13,56,0),cq.Vector(0,1,0))
    for y in [56,125]:
        grip=grip.fuse(cq.Solid.makeSphere(13,cq.Vector(13,y,0),
                         angleDegrees1=-90,angleDegrees2=90))
    grip=grip.clean()
    # Subtract the exact interface voids from the continuous structural core.
    interface_void=cyl(31.5,0,16).cut(base)
    pilot=base.cut(cyl(40,-1,17)).clean()
    handle=core.fuse(pilot).fuse(grip).cut(interface_void).clean()
    palm_edges=[e for e in handle.Edges() if e.BoundingBox().xlen<1e-6
        and abs(e.Center().x-16)<1e-5 and 43<e.Center().y<138
        and abs(e.Center().z)<13]
    assert palm_edges,'No palm/core blend edges selected'
    handle=handle.fillet(.4,palm_edges).clean()
    handle=holes(handle)
    coupon=holes(interface(7))
    results={}
    for name,s in [('radial_teaching_handle_v1',handle),('flange_fit_coupon_v1',coupon)]:
        results[name]=export_part(name,s)
    # Read-only placement check against CURRENT v2 backplate, including its pilot.
    back=cq.importers.importStep(str(back_path)).val()
    posed=handle.translate((80.8,43.494,-22.225))
    overlap=posed.intersect(back).Volume()
    assert overlap<.001,overlap
    # A nominal robot-side reference tests the recreated pilot/recess pair.
    reference=cyl(31.5,16,6).cut(cyl(15.75,16,2.1)).cut(cyl(12,16,7))
    nominal_overlap=handle.intersect(reference).Volume()
    assert nominal_overlap<.001,nominal_overlap
    # All five pin/bolt clearance cylinders must be open in the generated handle.
    passage_tests=[]
    for deg in P['screw_angles_deg']:
        a=math.radians(deg); y,z=25*math.cos(a),25*math.sin(a)
        v=handle.intersect(cyl(3,-.1,18.2,y,z)).Volume()
        assert v<.001
        passage_tests.append(dict(angle_deg=deg,shaft_diameter_mm=6,overlap_mm3=v))
    assert hashlib.sha256(back_path.read_bytes()).hexdigest()==back_hash
    report=dict(date='2026-10-21',parameters=P,cadquery_version=cq.__version__,parts=results,
        unchanged_backplate_sha256=back_hash,backplate_overlap_mm3=overlap,
        nominal_robot_reference_overlap_mm3=nominal_overlap,bolt_shaft_checks=passage_tests,
        added_tool_offset_mm=16,old_effective_M6_grip_mm=14,new_effective_M6_grip_mm=30,
        structural_core_rounded_edge_count=len(perimeter),
        limitations=['No full vendor wrist/connector/cable CAD or physical clearance verification',
            'No printed-strength, creep, fatigue, contact/preload or completed FEA qualification',
            'Male pilot/locating pin/printed-hole fits must be physically checked',
            'M6 length, washer/head access and actual thread engagement must be selected on hardware',
            'Coupon is a fit gauge only, not a load-bearing adapter'])
    (OUT/'parameters_and_checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (PACK/'export_manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    render([(handle,(.08,.43,.66))],OUT/'handle_preview.png',(250,195,165),(10,55,0),88)
    render([(back,(.9,.52,.16)),(posed,(.08,.43,.66))],OUT/'backplate_handle_fit_preview.png',
        (300,280,170),(58,85,-22.225),110)
    printable,_=print_pose(handle)
    render([(printable,(.08,.43,.66))],OUT/'print_orientation_preview.png',(260,-220,220),(86,31,10),96)
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__': main()
