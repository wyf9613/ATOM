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

