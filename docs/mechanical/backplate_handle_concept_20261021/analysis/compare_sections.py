"""First-order geometry/mechanics screening, not FEA or a load qualification.

Units: mm, N, MPa.  Run with Python + numpy + scipy + shapely.
The v2 sections reproduce its CAD construction; the narrow variant is an
explicit hypothetical continuation of concept_rev02, not a manufacturing model.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import numpy as np
from scipy.integrate import fixed_quad
from shapely.geometry import Point, LineString, box
from shapely.geometry.polygon import orient
from shapely.affinity import scale
from shapely.ops import unary_union

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PARAMS=ROOT/'source_cad/backplate/v2/parameters_and_checks.json'
P=json.loads(PARAMS.read_text(encoding='utf-8'))['parameters']
HOLES=[(25*math.cos(math.radians(a)),25*math.sin(math.radians(a)))
       for a in [45,135,225,315]]
Q=256

def disk(r,y=0,z=0,q=None):
    return Point(y,z).buffer(r,quad_segs=q or Q)

def front_outline(variant):
    if variant=='v2': return box(-42,-56,42,56)
    if variant=='rounded':
        return unary_union([disk(42)]+[disk(7.5,y,z)
            for y in [-9,9] for z in [-48.5,48.5]]).convex_hull
    body=(disk(42).intersection(box(-43,-36.5,43,36.5)) if variant=='flat_caps'
          else scale(disk(1),xfact=42,yfact=36.5))
    return unary_union([body]+
        [LineString([(y,s*30),(y,s*48.5)]).buffer(3.8,quad_segs=Q)
         for y in [-9,9] for s in [-1,1]])

def section(x,variant):
    if x<40.8:
        s=front_outline(variant)
    elif x<46.8:
        r=42-(x-40.8)*4/6
        s=(scale(disk(1),xfact=r,yfact=36.5) if variant=='narrow' else
           disk(r).intersection(box(-43,-36.5,43,36.5)) if variant=='flat_caps' else disk(r))
    elif x<78.8:
        s=(scale(disk(1),xfact=38,yfact=36.5) if variant=='narrow' else
           disk(38).intersection(box(-43,-36.5,43,36.5)) if variant=='flat_caps' else disk(38))
    else:
        s=disk(31.5)
    cuts=[disk(12)]
    cuts += [disk(6.5 if x<66.8 else 3.3,y,z) for y,z in HOLES]
    if x<42.8: cuts += [disk(1.7,y,z) for y in [-9,9] for z in [-48.5,48.5]]
    if x>=66: cuts.append(disk(3,25,0))
    return s.difference(unary_union(cuts))

def properties(g):
    """Green's-theorem polygon integrals including holes; centroidal I."""
    sums=np.zeros(6)
    for poly in ([g] if g.geom_type=='Polygon' else g.geoms):
        p=orient(poly,sign=1)
        for ring in [p.exterior,*p.interiors]:
            yz=np.asarray(ring.coords); y,z=yz[:-1].T; v,w=yz[1:].T
            cross=y*w-v*z
            sums+=np.array([np.sum(cross)/2,
                np.sum((y+v)*cross)/6,np.sum((z+w)*cross)/6,
                np.sum((z*z+z*w+w*w)*cross)/12,
                np.sum((y*y+y*v+v*v)*cross)/12,
                np.sum((2*y*z+y*w+v*z+2*v*w)*cross)/24])
    A,Ay,Az,Iy,Iz,Iyz=sums; cy,cz=Ay/A,Az/A
    Iy-=A*cz**2; Iz-=A*cy**2; Iyz-=A*cy*cz
    ymin,zmin,ymax,zmax=g.bounds
    return dict(area_mm2=A,cy_mm=cy,cz_mm=cz,Iy_mm4=Iy,Iz_mm4=Iz,Iyz_mm4=Iyz,
        Wy_mm3=Iy/max(zmax-cz,cz-zmin),Wz_mm3=Iz/max(ymax-cy,cy-ymin))

def make_report():
    # Sanity checks against exact circle and rectangle integrals, independent of CAD.
    d=properties(disk(42))
    assert abs(d['area_mm2']/(math.pi*42**2)-1)<1e-5
    assert abs(d['Iy_mm4']/(math.pi*42**4/4)-1)<2e-5
    r=properties(box(-42,-56,42,56))
    assert abs(r['Iy_mm4']/(84*112**3/12)-1)<1e-12
    rows=[]
    for x,label in [(35,'front_plate'),(40.8001,'root_start'),(46.8001,'body_access'),
                    (70,'body_small_bores'),(79.8,'flange_contact_pad')]:
        for variant in ['v2','rounded','narrow','flat_caps']:
            p=properties(section(x,variant))
            rows.append(dict(location=label,x_mm=x,variant=variant,**p,
                sigma_My_1Nm_MPa=1000/p['Wy_mm3'],sigma_Mz_1Nm_MPa=1000/p['Wz_mm3']))
    # Euler-Bernoulli compliance integrals are trend indicators only. The adapter
    # is short/thick; shear, local distortion, contact and joints are omitted.
    intervals=[28.8,40.8,46.8,66,66.8,78.8,80.8]
    integrations={}
    for name in ['v2','rounded','narrow','flat_caps']:
        integrations[name]={}
        for axis in ['y','z']:
            def inv_I(xs): return np.array([1/properties(section(float(x),name))['I'+axis+'_mm4'] for x in xs])
            integrations[name][axis]=sum(fixed_quad(inv_I,a,b,n=16)[0]
                 for a,b in zip(intervals[:-1],intervals[1:]))
    # Arc approximation convergence for body and root; no mesh/FEA claim.
    global Q
    convergence=[]
    for name in ['v2','narrow','flat_caps']:
        for x in [40.8001,46.8001,79.8]:
            Q=128; c=properties(section(x,name))
            Q=512; f=properties(section(x,name))
            convergence.append(dict(variant=name,x_mm=x,
                max_relative_difference=max(abs(c[k]/f[k]-1) for k in
                    ['area_mm2','Iy_mm4','Iz_mm4','Wy_mm3','Wz_mm3'])))
    Q=256
    # Local single-strip screening: not the actual 3-D v2 ear, no Kt/contact.
    oldL=48.5-math.sqrt(42**2-9**2)
    newL=48.5-36.5*math.sqrt(1-(9/42)**2)
    oldw,neww,t=15,7.6,12
    sigma_ratio=(newL/oldL)*(oldw/neww)
    compliance_ratio=(newL/oldL)**3*(oldw/neww)
    ear=dict(model='independent ideal cantilever strip; ranking only, not 3D stress prediction',
        old_assumed_width_mm=oldw,new_assumed_width_mm=neww,thickness_mm=t,
        old_unsupported_length_mm=oldL,new_unsupported_length_mm=newL,
        nominal_bending_stress_ratio=sigma_ratio,compliance_ratio=compliance_ratio,
        thickness_for_same_strip_nominal_bending_stress_mm=t*math.sqrt(sigma_ratio),
        thickness_for_same_strip_compliance_mm=t*compliance_ratio**(1/3),
        warning='strips are too short/thick for quantitative beam deflection; no strength ratio claimed',
        v2_net_ligament_mm=7.5-1.7,narrow_net_ligament_mm=3.8-1.7,
        in_plane_shearout_geometric_area_ratio=(3.8-1.7)/(7.5-1.7),
        note='shear-out ratio applies only to two equal straight ligaments, same t/material, edge-directed in-plane load; not pull-through')
    # Elastic equal-stiffness bolt-group normal-force coefficients, ignoring
    # preload/contact/prying. Unit moments only; these are NOT actual bolt forces.
    gripper=np.array([(y,z) for y in [-9,9] for z in [-48.5,48.5]])
    m6=np.array(HOLES)
    bolt=dict(gripper_max_axial_reaction_per_My_1Nm_N=float(max(abs(1000*gripper[:,1]/sum(gripper[:,1]**2)))),
        gripper_max_axial_reaction_per_Mz_1Nm_N=float(max(abs(1000*gripper[:,0]/sum(gripper[:,0]**2)))),
        flange_max_axial_reaction_per_bending_1Nm_N=float(max(abs(1000*m6[:,0]/sum(m6[:,0]**2)))))
    # Straight radial handle, force normal to flange, hand at R=100mm.
    # Root is idealized as a SOLID elliptical t by w section at R=31.5mm.
    handle=[]
    for F in [20,50,100]:
        for t in [8,12,16]:
            L=100-31.5; w=24; W=math.pi*w*t*t/32
            handle.append(dict(force_N=F,hand_radius_mm=100,root_radius_mm=31.5,
                root_width_mm=w,root_axial_thickness_mm=t,
                ideal_root_section='solid ellipse; no local Kt, no pores/threads/contact',
                root_bending_moment_Nm=F*L/1000,flange_bending_moment_Nm=F*.1,
                nominal_root_stress_MPa=F*L/W,
                nominal_root_in_plane_bending_stress_MPa=F*L/(math.pi*t*w*w/32),
                nominal_root_axial_stress_MPa=F/(math.pi*w*t/4),
                ideal_flange_max_normal_reaction_N=F/4+F*.1*bolt['flange_max_axial_reaction_per_bending_1Nm_N']))
    cad_check=[]
    cad_path=HERE/'baseline_cad_sections.json'
    if cad_path.exists():
        for reference in json.loads(cad_path.read_text(encoding='utf-8')):
            p=properties(section(reference['x_mm'],'v2'))
            err=max(abs(p[k]/reference[k]-1) for k in ['area_mm2','Iy_mm4','Iz_mm4'])
            assert err<3e-5, (reference['x_mm'],err)
            cad_check.append(dict(x_mm=reference['x_mm'],max_relative_difference=err))
    return dict(scope='Analytical geometry/linear nominal-stress screening; NOT FEA or qualification',
        units='N, mm, N/mm2=MPa; all geometry CAD nominal; material/loads not measured',
        material='User tentatively identifies PETG, all printed structural parts; brand/process unknown',
        params_sha256=hashlib.sha256(PARAMS.read_bytes()).hexdigest(),
        source_step_sha256=hashlib.sha256((ROOT/'source_cad/backplate/v2/reinforced_backplate_v2.step').read_bytes()).hexdigest(),
        sections=rows,curvature_compliance_integrals_per_E=integrations,
        numerical_convergence=convergence,baseline_cad_crosscheck=cad_check,
        ear_screen=ear,bolt_group=bolt,handle_sensitivity=handle,
        no_allowable_load_or_safety_factor=True)

if __name__=='__main__':
    report=make_report()
    (HERE/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for key in ['sections','handle_sensitivity','numerical_convergence']:
        with (HERE/(key+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=report[key][0].keys()); w.writeheader(); w.writerows(report[key])
    print(json.dumps({k:v for k,v in report.items() if k not in ['sections','handle_sensitivity']},indent=2))
