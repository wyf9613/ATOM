"""Build a review-only bracket in inherited STEP coordinates (mm).

Requires cadquery==2.6.1. Camera is a provisional envelope, not vendor CAD.
"""
import json, sys, hashlib
from pathlib import Path
import cadquery as cq

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'ros2_ws/src/atom_gripper_description/scripts'))
from extract_step_meshes import load_components

P={
 'hole_x_mm':[-33.7,-18.7], 'hole_z_mm':21.275,
 'shell_outer_mount_y_mm':45.494, 'shell_seam_y_mm':43.494,
 'shell_front_x_mm':-81.2, 'shell_hole_diameter_mm':3.2,
 'bracket_hole_diameter_mm':3.4, 'thickness_mm':4.0,
 'deck_bottom_z_mm':35.275, 'camera_clearance_hole_mm':6.8,
 'camera_envelope_mm':[25.0,90.0,25.0],
 'camera_hole_assumed_center_mm':[-68.7,43.494],
 'camera_hole_location_status':'UNVERIFIED: envelope-centre placeholder; check vendor mechanical drawing',
 'status':'REVIEW ONLY: not approved for manufacture or hardware use'
}

def box(x0,x1,y0,y1,z0,z1):
 return cq.Workplane('XY').box(x1-x0,y1-y0,z1-z0).translate(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))

plate=box(-41.2,-11.2,45.494,49.494,17.375,39.275)
deck=box(-81.2,-11.2,25.494,61.494,35.275,39.275)
tray=box(-85.2,-51.2,-4.506,91.494,35.275,39.275)
bracket=plate.union(deck).union(tray)
# Two side gussets below the deck, outside the shell seam tab.
for y in [25.494,57.494]:
 plane=cq.Plane(origin=(0,y,0),xDir=(1,0,0),normal=(0,-1,0))
 rib=cq.Workplane(plane).polyline([(-81.2,35.275),(-11.2,35.275),(-11.2,25.275)]).close().extrude(-4)
 bracket=bracket.union(rib)
# Provisional non-optical housing locating lips, 0.2 mm per side.
for a,b in [(-4.506,-1.706),(88.694,91.494)]:
 bracket=bracket.union(box(-79.2,-53.2,a,b,39.275,43.275))
bracket=bracket.union(box(-56.0,-51.2,-1.706,88.694,39.275,43.275))
for x in P['hole_x_mm']:
 cutter=cq.Solid.makeCylinder(P['bracket_hole_diameter_mm']/2,8,cq.Vector(x,44,P['hole_z_mm']),cq.Vector(0,1,0))
 bracket=bracket.cut(cutter)
x,y=P['camera_hole_assumed_center_mm']
bracket=bracket.cut(cq.Solid.makeCylinder(P['camera_clearance_hole_mm']/2,10,cq.Vector(x,y,32),cq.Vector(0,0,1)))
shape=bracket.val()
assert shape.isValid() and len(shape.Solids())==1
camera=box(-81.2,-56.2,-1.506,88.494,39.275,64.275)
source=ROOT/'hardware/end effector/End Effector Assembly V3.step'
components=load_components(source)
assembly=cq.Assembly(name='ATOM_CAMERA_BRACKET_REVIEW_V1')
for i,(name,s) in enumerate(components):
 assembly.add(cq.Shape.cast(s),name=f'inherited_{i}_{name.replace(":","_")}',color=cq.Color(0.24,0.29,0.39))
assembly.add(shape,name='camera_bracket_v1_review_only',color=cq.Color(1.0,0.56,0.12))
assembly.add(camera,name='D435_ENVELOPE_ONLY_NOT_VENDOR_CAD',color=cq.Color(0.72,0.74,0.77))
cq.exporters.export(bracket,str(OUT/'camera_bracket_v1.step'))
assembly.save(str(OUT/'gripper_camera_assembly_v1.step'))
reloaded=cq.importers.importStep(str(OUT/'camera_bracket_v1.step')).val()
assert reloaded.isValid() and len(reloaded.Solids())==1
overlap=[]
for name,s in components:
 volume=shape.intersect(cq.Shape.cast(s)).Volume()
 if volume>0.001: overlap.append({'component':name,'overlap_mm3':volume})
bb=shape.BoundingBox()
report={'parameters':P,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'checks':{'valid_single_solid':True,'step_roundtrip_valid_single_solid':True,
 'static_inherited_cad_overlap':overlap,'camera_envelope_overlap_mm3':shape.intersect(camera.val()).Volume()},
 'bounds_mm':[bb.xmin,bb.ymin,bb.zmin,bb.xmax,bb.ymax,bb.zmax],
 'volume_mm3':shape.Volume(),'limitations':['Static inherited pose only; finger sweep and cable not checked.','No physical fit, load, vibration or hand-eye validation.','Camera mounting hole position, insertion depth and housing lips must be checked against actual model.']}
(OUT/'parameters_and_checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')

def render(items,path,pos,target,scale):
 import vtk
 ren=vtk.vtkRenderer(); ren.SetBackground(0.96,0.97,0.98)
 for s,col in items:
  vertices,triangles=s.tessellate(0.8,0.4)
  pts=vtk.vtkPoints()
  for v in vertices: pts.InsertNextPoint(v.x,v.y,v.z)
  cells=vtk.vtkCellArray()
  for tri in triangles:
   cells.InsertNextCell(3)
   for n in tri: cells.InsertCellPoint(n)
  poly=vtk.vtkPolyData(); poly.SetPoints(pts); poly.SetPolys(cells)
  normals=vtk.vtkPolyDataNormals(); normals.SetInputData(poly); normals.ComputePointNormalsOn()
  mapper=vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort())
  actor=vtk.vtkActor(); actor.SetMapper(mapper); actor.GetProperty().SetColor(*col)
  actor.GetProperty().SetSpecular(0.25); actor.GetProperty().SetSpecularPower(25)
  ren.AddActor(actor)
 cam=ren.GetActiveCamera(); cam.SetPosition(*pos); cam.SetFocalPoint(*target); cam.SetViewUp(0,0,1); cam.ParallelProjectionOn(); cam.SetParallelScale(scale)
 ren.ResetCameraClippingRange()
 window=vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(1400,1000); window.AddRenderer(ren); window.Render()
 capture=vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.Update()
 writer=vtk.vtkPNGWriter(); writer.SetFileName(str(path)); writer.SetInputConnection(capture.GetOutputPort()); writer.Write(); window.Finalize()

render([(cq.Shape.cast(s),(0.24,0.29,0.39)) for _,s in components]+[(shape,(1,.56,.12)),(camera.val(),(.72,.74,.77))],OUT/'assembly_preview.png',(-260,300,210),(-42,43,-5),115)
render([(shape,(1,.56,.12))],OUT/'bracket_preview.png',(-240,240,170),(-45,43,29),67)
render([(shape,(1,.56,.12))],OUT/'mounting_holes_preview.png',(150,250,-100),(-45,43,29),67)
print(json.dumps(report,indent=2))
