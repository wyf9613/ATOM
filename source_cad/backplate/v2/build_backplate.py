"""Reinforced review adapter and independent opposite-side ESP32 bracket.

CAD geometry checks are not structural qualification. Millimetres throughout.
"""
import hashlib, json, math, sys
from pathlib import Path
import cadquery as cq
from render_cad import render
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
ESP=ROOT/'source_cad/esp32_bracket/v1'; ESP.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'ros2_ws/src/atom_gripper_description/scripts'))
from extract_step_meshes import load_components
CY,CZ=43.494,-22.225
P={'status':'REVIEW ONLY: printed strength unverified',
 'material_user_tentative':'PLA; brand and print settings unconfirmed',
 'gripper_camera_mass_user_estimate_kg':0.7,
 'mass_evidence':'User heft estimate, not a scale measurement; sample count and uncertainty not supplied',
 'gripper_face_x_mm':28.8,'robot_contact_x_mm':80.8,
 'rear_extension_mm':52.0,'front_plate_mm':12.0,
 'front_plate_yz_mm':[84.0,112.0],
 'body_od_mm':76.0,'root_od_mm':84.0,'central_passage_mm':24.0,
 'flange_plate_total_mm':14.0,'flange_mating_pad_od_mm':63.0,
 'pcd_mm':50.0,'m6_clearance_mm':6.6,'m6_access_bore_mm':13.0,
 'pilot_od_provisional_mm':31.45,'pilot_height_provisional_mm':2.0,
 'gripper_holes_y_mm':[34.494,52.494],'gripper_holes_z_mm':[-70.725,26.275],
 'esp_mount_holes_x_mm':[-33.7,-18.7],'esp_mount_holes_z_mm':-65.725,
 'esp_mount_gap_mm':4.0,'esp_clip_cheek_mm':4.0,
 'esp_pcb_hole_pitch_user_provisional_mm':[46.5,23.5],
 'esp_pcb_hole_diameter_user_provisional_mm':4.0,
 'esp_pcb_outline_placeholder_mm':[54.0,30.0,1.6],
 'esp_standoff_mm':8.0,
 'printing':'No infill, layer adhesion, material or orientation qualification assumed',
 'structural_bottleneck':'Inherited four 3.2 mm holes and shell tabs are also unverified load paths'}
def box(a,b,c,d,e,f):
 return cq.Workplane('XY').box(b-a,d-c,f-e).translate(((a+b)/2,(c+d)/2,(e+f)/2)).val()
def cyl(r,l,p,d): return cq.Solid.makeCylinder(r,l,cq.Vector(*p),cq.Vector(*d))
def union(parts):
 s=parts[0]
 for p in parts[1:]: s=s.fuse(p)
 return s.clean()
def valid(s): return s.isValid() and len(s.Solids())==1

# Broad front plate and continuous annular body: no electronics mount, no
# thin separated bridge rails. A conical collar spreads the root transition.
main=union([box(28.8,40.8,CY-42,CY+42,CZ-56,CZ+56),
 cq.Solid.makeCone(42,38,6,cq.Vector(40.8,CY,CZ),cq.Vector(1,0,0)),
 cyl(38,32,(46.8,CY,CZ),(1,0,0)),
 cyl(31.5,2,(78.8,CY,CZ),(1,0,0)),
 cyl(15.725,2,(80.8,CY,CZ),(1,0,0))])
main=main.cut(cyl(12,56,(27.8,CY,CZ),(1,0,0)))
for y in P['gripper_holes_y_mm']:
 for z in P['gripper_holes_z_mm']:
  main=main.cut(cyl(1.7,15,(27.8,y,z),(1,0,0)))
flange_holes=[]
for deg in [45,135,225,315]:
 y=CY+25*math.cos(math.radians(deg)); z=CZ+25*math.sin(math.radians(deg))
 flange_holes.append([y,z])
 # Full-length access sockets, seat x=66.8; 14 mm load-bearing plate to
 # robot contact x=80.8. Install flange screws before attaching gripper.
 main=main.cut(cyl(6.5,39,(27.8,y,z),(1,0,0)))
 main=main.cut(cyl(3.3,17,(66,y,z),(1,0,0)))
main=main.cut(cyl(3,17,(66,CY+25,CZ),(1,0,0)))
main=main.clean(); assert valid(main)

# Mirror of camera attachment around z=-22.225: lower inherited seam tabs.
clip=union([box(-41.2,-11.2,37.494,41.494,-79.725,-61.825),
 box(-41.2,-11.2,45.494,49.494,-79.725,-61.825),
 box(-78.2,-11.2,22.494,64.494,-79.725,-75.725)])
for x in P['esp_mount_holes_x_mm']:
 clip=clip.cut(cyl(1.7,16,(x,35.494,-65.725),(0,1,0)))
pcb_holes=[]
for x in [-69.45,-22.95]:
 for y in [31.744,55.244]:
  pcb_holes.append([x,y]); clip=clip.cut(cyl(2,8,(x,y,-82),(0,0,1)))
clip=clip.clean(); assert valid(clip)
pcb=box(-73.2,-19.2,28.494,58.494,-89.325,-87.725)
spacers=[]
for x,y in pcb_holes:
 pcb=pcb.cut(cyl(2,3,(x,y,-90),(0,0,1)))
 spacers.append(cyl(4,8,(x,y,-87.725),(0,0,1)).cut(cyl(2,8,(x,y,-87.725),(0,0,1))))
module=box(-70,-50,34,52,-93,-89.325)
usb=box(-23,-15,39.494,47.494,-94,-89.325)
headers=[box(-61,-25,28.494,31.494,-97,-89.325),box(-61,-25,55.494,58.494,-97,-89.325)]

source=ROOT/'hardware/end effector/End Effector Assembly V3.step'
components=load_components(source)
camera=cq.importers.importStep(str(ROOT/'source_cad/camera_bracket/v2/camera_bracket_v2.step')).val()
robot=cyl(31.5,6,(80.8,CY,CZ),(1,0,0)).cut(cyl(15.75,6,(80.8,CY,CZ),(1,0,0)))
for y,z in flange_holes: robot=robot.cut(cyl(3,6,(80.8,y,z),(1,0,0)))
robot=robot.cut(cyl(3,5,(80.8,CY+25,CZ),(1,0,0)))
assembly=cq.Assembly(name='ATOM_REINFORCED_BACKPLATE_V2_INDEPENDENT_ESP32')
for i,(name,s) in enumerate(components): assembly.add(cq.Shape.cast(s),name=f'inherited_{i}',color=cq.Color(.24,.29,.39))
parts=[('reinforced_backplate_review',main,(1,.56,.12)),
 ('independent_esp32_bracket',clip,(.2,.65,.85)),
 ('pcb_outline_placeholder',pcb,(.1,.5,.28)),('module_envelope',module,(.7,.72,.73)),
 ('usb_envelope',usb,(.7,.72,.73)),('camera_bracket_v2',camera,(.9,.55,.2)),
 ('UF850_flange_reference_NOT_VENDOR_CAD',robot,(.65,.67,.7))]
parts.extend([(f'standoff_{i}',s,(.85,.85,.8)) for i,s in enumerate(spacers)])
parts.extend([(f'header_{i}',s,(.13,.13,.13)) for i,s in enumerate(headers)])
for name,s,col in parts: assembly.add(s,name=name,color=cq.Color(*col))
for path,s in [(OUT/'reinforced_backplate_v2.step',main),(ESP/'esp32_bracket_v1.step',clip)]:
 cq.exporters.export(s,str(path)); assert valid(cq.importers.importStep(str(path)).val())
assembly.save(str(OUT/'gripper_backplate_esp32_assembly_v2.step'))

hits=[]
for part,s,_ in parts:
 if part in ['UF850_flange_reference_NOT_VENDOR_CAD']: continue
 for name,t in components:
  v=s.intersect(cq.Shape.cast(t)).Volume()
  if v>.001: hits.append({'part':part,'inherited':name,'overlap_mm3':v})
pair_hits=[]
for i,(a,s,_) in enumerate(parts):
 for b,t,_ in parts[i+1:]:
  v=s.intersect(t).Volume()
  if v>.001: pair_hits.append({'a':a,'b':b,'overlap_mm3':v})
tools=[]
for y,z in flange_holes:
 tools.append(('M6_before_gripper_install',cyl(5.5,38,(28.8,y,z),(1,0,0)),False))
for y in P['gripper_holes_y_mm']:
 for z in P['gripper_holes_z_mm']:
  tools.append(('M3_gripper',cyl(3.3,50,(40.8,y,z),(1,0,0)),True))
for x in P['esp_mount_holes_x_mm']:
 tools.append(('M3_ESP_clip',cyl(3.3,25,(x,49.494,-65.725),(0,1,0)),True))
tool_hits=[]
for kind,t,include_inherited in tools:
 check=[(n,s) for n,s,_ in parts if not n.startswith('UF850')]
 if include_inherited: check += [(n,cq.Shape.cast(s)) for n,s in components]
 for name,s in check:
  v=s.intersect(t).Volume()
  if v>.001: tool_hits.append({'tool':kind,'part':name,'overlap_mm3':v})
report={'parameters':P,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'flange_reference':'UF850 V2.3.0 p26; same nominal pattern as v1',
 'flange_hole_centres_yz_mm':flange_holes,'pcb_hole_centres_xy_mm':pcb_holes,
 'checks':{'main_valid_single_solid':valid(main),'esp_valid_single_solid':valid(clip),
 'step_roundtrip_valid':True,'inherited_intersections':hits,'pair_intersections':pair_hits,'tool_corridor_intersections':tool_hits},
 'volume_mm3':{'reinforced_adapter':main.Volume(),'esp_bracket':clip.Volume()},
 'limitations':['Geometry review only, no deflection, stress, fatigue, creep or printed-layer qualification.','Inherited M3 tabs can remain the structural bottleneck.','PCB hole pattern user-provisional; PCB/USB/header envelopes unverified.','M6 screws accessible before gripper is attached; full wrist/connectors/cables and wrench sweep unverified.','Board now below inherited case; lowest envelope z=-97 mm needs workcell clearance check.']}
(OUT/'parameters_and_checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
(ESP/'parameters_and_checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
allitems=[(cq.Shape.cast(s),(.24,.29,.39)) for _,s in components]+[(s,c) for _,s,c in parts]
render([(main,(1,.56,.12))],OUT/'reinforced_backplate_preview.png',(240,-180,140),(55,43,-22),84)
render(allitems,OUT/'assembly_preview.png',(280,-300,-180),(-15,43,-33),145)
render([(clip,(.2,.65,.85))],ESP/'esp32_bracket_preview.png',(-150,210,-160),(-44,43,-72),57)
render([(clip,(.2,.65,.85)),(pcb,(.1,.5,.28)),(module,(.7,.72,.73)),(usb,(.7,.72,.73))]+[(s,(.85,.85,.8)) for s in spacers]+[(s,(.13,.13,.13)) for s in headers],ESP/'esp32_installed_preview.png',(-170,210,-170),(-44,43,-77),64)
print(json.dumps(report,indent=2))
