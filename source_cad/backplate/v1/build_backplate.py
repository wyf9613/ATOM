"""Review CAD: open UF850 adapter and removable, provisional ESP32 carrier.

All dimensions in mm in inherited gripper coordinates. Requires CadQuery 2.6.1.
PCB coordinates are explicitly unverified; flange dimensions from UF850 V2.3 p26.
"""
import hashlib, json, math, sys
from pathlib import Path
import cadquery as cq

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'ros2_ws/src/atom_gripper_description/scripts'))
from extract_step_meshes import load_components

CY,CZ=43.494,-22.225
P={
 'status':'REVIEW CAD: no physical fit/load validation',
 'gripper_holes_y_mm':[34.494,52.494],
 'gripper_holes_z_mm':[-70.725,26.275],
 'gripper_hole_diameter_cad_mm':3.2,'gripper_mount_face_x_mm':28.8,
 'gripper_plate_thickness_mm':6.0,'gripper_clearance_mm':3.4,
 'robot_contact_face_x_mm':93.0,'flange_disc_thickness_mm':8.0,
 'flange_outer_diameter_mm':63.0,'flange_pcd_mm':50.0,
 'flange_thread_on_robot':'4 x M6, drawing depth 10 mm',
 'flange_clearance_mm':6.6,'flange_angles_deg':[45,135,225,315],
 'flange_dowel_diameter_nominal_mm':6.0,'flange_dowel_y_mm':CY+25,
 'flange_pilot_bore_on_robot_mm':31.5,
 'adapter_pilot_od_provisional_mm':31.45,'adapter_pilot_height_provisional_mm':2.0,
 'central_passage_mm':24.0,
 'pcb_outline_provisional_mm':[54.0,30.0,1.6],
 'pcb_hole_pitch_provisional_mm':[46.5,23.5],
 'pcb_holes_x_mm':[43.25,89.75],'pcb_holes_z_mm':[-46.75,-23.25],
 'pcb_clearance_provisional_mm':4.0,'pcb_standoff_height_mm':8.0,
 'pcb_status':'User-provisional pitch 46.5 x 23.5 and confirmed diameter 4.0 mm; board outline unverified',
 'main_material':'UNSELECTED: load-bearing design not validated',
 'carrier_material':'UNSELECTED: electrical insulation and antenna clearance require verification'
}

def box(a,b,c,d,e,f):
 return cq.Workplane('XY').box(b-a,d-c,f-e).translate(((a+b)/2,(c+d)/2,(e+f)/2)).val()
def cyl(radius,length,start,direction):
 return cq.Solid.makeCylinder(radius,length,cq.Vector(*start),cq.Vector(*direction))
def fuse(parts):
 s=parts[0]
 for t in parts[1:]: s=s.fuse(t)
 return s.clean()
def valid(s): return s.isValid() and len(s.Solids())==1

# H frame: narrow rails around the four inherited rear tab holes.
main_parts=[box(28.8,34.8,27.494,40.494,-77.225,32.775),
 box(28.8,34.8,46.494,59.494,-77.225,32.775),
 box(28.8,34.8,27.494,59.494,-30.225,-14.225)]
# Two open bridge rails leave direct axial access to all four M6 screw heads.
main_parts.extend([box(34.8,85,37.494,49.494,-44.225,-36.225),
 box(34.8,85,37.494,49.494,-8.225,-0.225),
 cyl(31.5,8,(85,CY,CZ),(1,0,0)),
 cyl(15.725,2,(93,CY,CZ),(1,0,0))])
# Two side ears, placed away from the flange fastener tool corridors.
for z in [-56.225,-14.225]:
 main_parts.append(box(34.8,44.8,8.494,34.494,z-4,z+4))
main=fuse(main_parts)
for y in P['gripper_holes_y_mm']:
 for z in P['gripper_holes_z_mm']:
  main=main.cut(cyl(1.7,10,(27,y,z),(1,0,0)))
main=main.cut(cyl(12,12,(84,CY,CZ),(1,0,0)))
flange_holes=[]
for deg in P['flange_angles_deg']:
 y=CY+25*math.cos(math.radians(deg)); z=CZ+25*math.sin(math.radians(deg))
 flange_holes.append([y,z]); main=main.cut(cyl(3.3,12,(84,y,z),(1,0,0)))
main=main.cut(cyl(3,12,(84,CY+25,CZ),(1,0,0)))
# M3 pilot bores in side ears: thread manufacturing callout, not modeled helix.
for z in [-56.225,-14.225]: main=main.cut(cyl(1.25,12,(39.8,7.494,z),(0,1,0)))
main=main.clean(); assert valid(main)

carrier=box(34,98,4.494,8.494,-62.225,-8.225)
# Large central window and antenna-side window keep most of the board exposed.
carrier=carrier.cut(box(51,83,3,10,-42,-28))
carrier=carrier.cut(box(33,51,3,10,-42,-28))
for z in [-56.225,-14.225]: carrier=carrier.cut(cyl(1.6,8,(39.8,2.494,z),(0,1,0)))
pcb_holes=[]
for x in P['pcb_holes_x_mm']:
 for z in P['pcb_holes_z_mm']:
  pcb_holes.append([x,z]); carrier=carrier.cut(cyl(P['pcb_clearance_provisional_mm']/2,8,(x,2.494,z),(0,1,0)))
carrier=carrier.clean(); assert valid(carrier)

pcb=box(39.5,93.5,-5.106,-3.506,-50,-20)
spacers=[]
for x,z in pcb_holes:
 pcb=pcb.cut(cyl(2,3,(x,-6,z),(0,1,0)))
 spacers.append(cyl(4,8,(x,-3.506,z),(0,1,0)).cut(cyl(2,8,(x,-3.506,z),(0,1,0))))
# Context only: provisional module and Micro-USB / header envelopes.
module=box(43,63,-8.5,-5.106,-44,-26)
usb=box(89,97,-9,-5.106,-39,-31)
headers=[box(51,87,-13,-5.106,-49,-46),box(51,87,-13,-5.106,-24,-21)]
source=ROOT/'hardware/end effector/End Effector Assembly V3.step'
components=load_components(source)
camera_path=ROOT/'source_cad/camera_bracket/v2/camera_bracket_v2.step'
camera_bracket=cq.importers.importStep(str(camera_path)).val()

# Simple robot-flange reference, not vendor wrist CAD; axial threaded holes
# are shown as smooth bores to convey locations only.
robot=cyl(31.5,6,(93,CY,CZ),(1,0,0)).cut(cyl(15.75,6,(93,CY,CZ),(1,0,0)))
for y,z in flange_holes: robot=robot.cut(cyl(3,6,(93,y,z),(1,0,0)))
robot=robot.cut(cyl(3,5,(93,CY+25,CZ),(1,0,0)))

assembly=cq.Assembly(name='ATOM_BACKPLATE_REVIEW_V1')
for i,(name,s) in enumerate(components):
 assembly.add(cq.Shape.cast(s),name=f'inherited_{i}',color=cq.Color(.24,.29,.39))
assembly.add(main,name='open_backplate_UF850_adapter_review',color=cq.Color(1,.56,.12))
assembly.add(carrier,name='ESP32_carrier_HOLE_PATTERN_UNVERIFIED',color=cq.Color(.2,.65,.85))
assembly.add(pcb,name='ESP32_PCB_UNVERIFIED_ENVELOPE',color=cq.Color(.1,.5,.28))
assembly.add(module,name='ESP32_MODULE_CONTEXT_ENVELOPE',color=cq.Color(.7,.72,.73))
assembly.add(usb,name='USB_CONTEXT_ENVELOPE',color=cq.Color(.7,.72,.73))
for i,s in enumerate(spacers): assembly.add(s,name=f'pcb_standoff_reference_{i}',color=cq.Color(.85,.85,.8))
for i,s in enumerate(headers): assembly.add(s,name=f'header_envelope_{i}',color=cq.Color(.13,.13,.13))
assembly.add(camera_bracket,name='camera_bracket_v2',color=cq.Color(.9,.55,.2))
assembly.add(robot,name='UF850_FLANGE_REFERENCE_NOT_VENDOR_CAD',color=cq.Color(.65,.67,.7))
for name,s in [('open_backplate_v1',main),('esp32_carrier_PROVISIONAL_v1',carrier)]:
 path=OUT/f'{name}.step'; cq.exporters.export(s,str(path))
 assert valid(cq.importers.importStep(str(path)).val())
assembly.save(str(OUT/'gripper_backplate_esp32_assembly_v1.step'))

interference=[]
for name,s in components:
 vol=main.intersect(cq.Shape.cast(s)).Volume()
 if vol>.001: interference.append({'part':name,'overlap_mm3':vol})
# Straight driver shank/hex-head corridors: model geometry only, not proof
# of every socket/washer/wrench or real hand access.
tools=[]
for y,z in flange_holes: tools.append(('M6',cyl(5.5,48,(37,y,z),(1,0,0))))
for y in P['gripper_holes_y_mm']:
 for z in P['gripper_holes_z_mm']: tools.append(('M3',cyl(3.3,70,(34.8,y,z),(1,0,0))))
tool_hits=[]
for i,(kind,t) in enumerate(tools):
 for name,s in [('main',main),('carrier',carrier),('pcb',pcb)]+[(f'inherited_{name}',cq.Shape.cast(s)) for name,s in components]:
  vol=t.intersect(s).Volume()
  if vol>.001: tool_hits.append({'tool':i,'kind':kind,'part':name,'overlap_mm3':vol})
nut_hits=[]
for y in P['gripper_holes_y_mm']:
 for z in P['gripper_holes_z_mm']:
  # Approximate M3 nut envelope in front of the inherited tab.
  nut=cyl(3.3,2.4,(16.4,y,z),(1,0,0))
  for name,s in components:
   vol=nut.intersect(cq.Shape.cast(s)).Volume()
   if vol>.001: nut_hits.append({'centre_yz_mm':[y,z],'part':name,'overlap_mm3':vol})
report={'parameters':P,'source_step_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'flange_source':'https://www.ufactory.cc/wp-content/uploads/2024/01/UFactory-850-User-Manual-V2.3.0.pdf, printed page 26',
 'flange_hole_centres_yz_mm':flange_holes,'pcb_hole_centres_xz_mm_UNVERIFIED':pcb_holes,
 'checks':{'main_valid_single_solid':valid(main),'carrier_valid_single_solid':valid(carrier),
 'step_roundtrip_valid':True,'inherited_static_interference':interference,
 'main_carrier_overlap_mm3':main.intersect(carrier).Volume(),
 'robot_reference_overlap_mm3':main.intersect(robot).Volume(),
 'axial_tool_corridor_hits':tool_hits,'approximate_M3_nut_envelope_hits':nut_hits},
 'volume_mm3':{'main':main.Volume(),'carrier':carrier.Volume()},
 'limitations':['User-provisional PCB hole pitch/diameter; uncertainty unspecified; board outline is a placeholder.','No physical loads or fit verified.','Flange nominal geometry verified in manual, physical flange/revision and pilot fit unverified.','No wrist/connector full CAD, finger sweep, cable bend or dynamic tool access verification.','Material, structural design, bolt preload, fastener lengths and torque not finalized.']}
(OUT/'parameters_and_checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')

def render(items,path,pos,target,scale):
 import vtk
 ren=vtk.vtkRenderer(); ren.SetBackground(.96,.97,.98)
 for s,col in items:
  vertices,triangles=s.tessellate(.7,.35)
  pts=vtk.vtkPoints()
  for v in vertices: pts.InsertNextPoint(v.x,v.y,v.z)
  cells=vtk.vtkCellArray()
  for tri in triangles:
   cells.InsertNextCell(3)
   for n in tri: cells.InsertCellPoint(n)
  poly=vtk.vtkPolyData(); poly.SetPoints(pts); poly.SetPolys(cells)
  normals=vtk.vtkPolyDataNormals(); normals.SetInputData(poly)
  mapper=vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort())
  actor=vtk.vtkActor(); actor.SetMapper(mapper); actor.GetProperty().SetColor(*col)
  actor.GetProperty().SetSpecular(.2); ren.AddActor(actor)
 cam=ren.GetActiveCamera(); cam.SetPosition(*pos); cam.SetFocalPoint(*target); cam.SetViewUp(0,0,1); cam.ParallelProjectionOn(); cam.SetParallelScale(scale)
 ren.ResetCameraClippingRange()
 window=vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(1500,1100); window.AddRenderer(ren); window.Render()
 capture=vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.Update()
 writer=vtk.vtkPNGWriter(); writer.SetFileName(str(path)); writer.SetInputConnection(capture.GetOutputPort()); writer.Write(); window.Finalize()

adapter_items=[(main,(1,.56,.12)),(carrier,(.2,.65,.85)),(pcb,(.1,.5,.28)),(module,(.7,.72,.73)),(usb,(.7,.72,.73))]+[(s,(.85,.85,.8)) for s in spacers]+[(s,(.13,.13,.13)) for s in headers]
render(adapter_items,OUT/'adapter_esp32_preview.png',(240,-180,160),(63,25,-23),90)
render([(main,(1,.56,.12))],OUT/'open_backplate_preview.png',(220,-140,120),(58,35,-23),72)
render([(cq.Shape.cast(s),(.24,.29,.39)) for _,s in components]+adapter_items+[(camera_bracket,(.9,.55,.2)),(robot,(.65,.67,.7))],OUT/'assembly_preview.png',(300,-280,220),(-10,35,-23),137)
print(json.dumps(report,indent=2))
