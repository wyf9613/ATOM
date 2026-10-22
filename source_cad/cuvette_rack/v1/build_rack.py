"""Parametric 2D laser prototype; mm; Python + numpy/opencv/ezdxf/shapely/matplotlib.

CUT paths include one kerf compensation. Disable machine/software compensation.
3D illustrations derive from nominal 2D polygons, not a physical validation.
"""
from pathlib import Path
import json, hashlib, html
import numpy as np
import cv2
import ezdxf
from shapely.geometry import box, Point, Polygon
from shapely.ops import unary_union
from shapely.affinity import translate
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PatchPolygon, Circle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

OUT = Path(__file__).resolve().parent
P = json.loads((OUT/'parameters.json').read_text(encoding='utf-8'))
T, W, D = P['thickness'], P['width'], P['depth']
F, B = P['front_y'], D-P['front_y']-T
SEAT = P['base_bottom']+T
REPORT = {'parameters': P, 'variants': {}, 'digital_tag_checks': []}


def loops(poly):
    return [list(poly.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in poly.interiors]


def polygons(shape):
    if shape.is_empty:
        return []
    return [shape] if shape.geom_type == 'Polygon' else list(shape.geoms)


def marker(tag_id):
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    # OpenCV 4.13 canonical artwork is 180 degrees from the AprilRobotics PNGs.
    # Match upstream artwork orientation; detector corner/frame conventions remain separate.
    bits = np.rot90(cv2.aruco.generateImageMarker(dictionary, tag_id, 8), 2).copy()
    canvas = np.full((600, 600), 255, np.uint8)
    canvas[60:540,60:540] = cv2.resize(bits,(480,480),interpolation=cv2.INTER_NEAREST)
    _, ids, _ = cv2.aruco.ArucoDetector(dictionary).detectMarkers(canvas)
    assert ids is not None and ids.flatten().tolist() == [tag_id]
    REPORT['digital_tag_checks'].append({'id': tag_id, 'decoded_id': int(ids[0,0]),
                                        'condition': 'synthetic frontal 600 px, white background; no MDF/camera test'})
    # 8x8 including black border. A 5 mm module yields 40 mm black border,
    # with an additional one-module unengraved/white perimeter on all sides.
    cell=P['tag_black_border_size']/8
    black=unary_union([box(c*cell,r*cell,(c+1)*cell,(r+1)*cell)
                      for r in range(8) for c in range(8) if bits[r,c]==0])
    return bits, black


def shelf():
    poly=box(T,F+T,W-T,B)
    tabs=[box(a,y0,b,y1) for a,b in [(0,T),(W-T,W)] for y0,y1 in P['shelf_tab_y']]
    return unary_union([poly]+tabs)


def apron():
    return unary_union([box(T,0,W-T,SEAT)] +
        [box(a,z0,b,z1) for a,b in [(0,T),(W-T,W)] for z0,z1 in P['apron_tab_z']])


def end(guide_bottom):
    poly=box(0,0,D,guide_bottom+T+8)
    sw=T-P['interference']
    slack=P['tab_length_clearance']/2
    for z in [P['base_bottom'],guide_bottom]:
        for y0,y1 in P['shelf_tab_y']:
            poly=poly.difference(box(y0-slack,z+(T-sw)/2,y1+slack,z+(T+sw)/2))
    for y in [F,B]:
        for z0,z1 in P['apron_tab_z']:
            poly=poly.difference(box(y+(T-sw)/2,z0-slack,y+(T+sw)/2,z1+slack))
    return poly


def write_job(name, parts, size, compensate=True):
    """parts: (name, nominal polygon, dx, dy, engraving polygons). SVG uses y-up geometry."""
    doc=ezdxf.new('R2010'); doc.units=4
    for layer,color in [('CUT_OUTER',1),('CUT_INNER',1),('RASTER',7)]:
        doc.layers.new(layer,dxfattribs={'color':color,'lineweight':0})
    m=doc.modelspace()
    width,height=size
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}mm" height="{height}mm" viewBox="0 0 {width} {height}">',
         '<title>ATOM review prototype; red=CUT; black fill=RASTER; mm; compensation already applied</title>',
         f'<g transform="translate(0,{height}) scale(1,-1)">']
    for part,poly,x,y,engraving in parts:
        q=translate(poly,xoff=x,yoff=y)
        cut=q.buffer(P['kerf']/2,join_style=2) if compensate else q
        assert cut.is_valid and cut.geom_type=='Polygon', part
        for i,ring in enumerate(loops(cut)):
            layer='CUT_OUTER' if i==0 else 'CUT_INNER'
            m.add_lwpolyline(ring,close=True,dxfattribs={'layer':layer})
            points=' '.join(f'{u:.5f},{v:.5f}' for u,v in ring)
            svg.append(f'<polygon data-part="{part}" data-layer="{layer}" points="{points}" fill="none" stroke="red" stroke-width="0.01"/>')
        for shape in engraving:
            for tile in polygons(translate(shape,xoff=x,yoff=y)):
                # Use individual cells merged by row, so solid hatches have no holes.
                assert len(tile.interiors)==0
                pts=loops(tile)[0]
                hatch=m.add_hatch(color=7,dxfattribs={'layer':'RASTER'})
                hatch.paths.add_polyline_path(pts,is_closed=True)
                svg.append('<polygon data-layer="RASTER" points="'+ ' '.join(f'{u:.5f},{v:.5f}' for u,v in pts)+'" fill="black"/>')
    svg.append('</g></svg>')
    doc.saveas(OUT/f'{name}.dxf')
    (OUT/f'{name}.svg').write_text('\n'.join(svg),encoding='utf-8')
    reread=ezdxf.readfile(OUT/f'{name}.dxf')
    assert not reread.audit().has_errors
    cut_entities=[e for e in reread.modelspace() if e.dxftype()=='LWPOLYLINE']
    assert all(e.closed for e in cut_entities)
    # No duplicate closed paths, including cyclic/reversed equivalence.
    keys=[]
    for e in cut_entities:
        coords=[(round(v[0],5),round(v[1],5)) for v in e.get_points()]
        keys.append(tuple(sorted((min(a,b),max(a,b)) for a,b in zip(coords,coords[1:]+coords[:1]))))
    assert len(keys)==len(set(keys))
    return {'dxf_closed_cut_paths':len(keys),'dxf_audit_errors':0,'sheet_mm':size}


def row_cells(bits,x,y):
    """Image row 0 is top. Convert to upright on the panel viewed from front."""
    cells=[]
    cell=P['tag_black_border_size']/8
    for r in range(8):
        c=0
        while c<8:
            if bits[r,c]: c+=1; continue
            start=c
            while c<8 and bits[r,c]==0: c+=1
            cells.append(box(x+start*cell,y+(7-r)*cell,x+c*cell,y+(8-r)*cell))
    return cells


def review_flat(name, parts, size):
    fig,ax=plt.subplots(figsize=(12,12))
    for label,poly,x,y,engrave in parts:
        q=translate(poly,xoff=x,yoff=y)
        ax.add_patch(PatchPolygon(loops(q)[0],facecolor='#d7b78b',edgecolor='#764e2a',lw=.7))
        for r in loops(q)[1:]:
            ax.add_patch(PatchPolygon(r,facecolor='white',edgecolor='#764e2a',lw=.7))
        for shape in engrave:
            for tile in polygons(translate(shape,xoff=x,yoff=y)):
                ax.add_patch(PatchPolygon(loops(tile)[0],facecolor='#26221e',edgecolor='none'))
        minx,miny,maxx,maxy=q.bounds
        ax.text(minx,miny-2,label,va='top',fontsize=9)
    ax.set(xlim=(0,size[0]),ylim=(0,size[1]),aspect='equal',xlabel='mm',ylabel='mm')
    ax.set_title(f'ATOM {name} | {len(parts)} parts | nominal geometry, not machine paths\nRed CUT / filled black RASTER are separate in DXF and SVG',loc='left')
    ax.grid(alpha=.12)
    fig.tight_layout();fig.savefig(OUT/f'{name}_layout.png',dpi=160);plt.close(fig)


def render_assembly(name, pieces, v, guide_bottom, tag_cells):
    fig=plt.figure(figsize=(14,7));ax=fig.add_subplot(111,projection='3d',computed_zorder=False)
    colors=['#cda66b','#e6c28c','#b78f5b','#b78f5b','#d8b780','#cda66b']
    faces=[]; face_colors=[]
    def face(points,color,alpha=1):
        faces.append(points);face_colors.append(color)
    # Extrude nominal polygons. Triangulate and clip faces to preserve actual holes.
    from shapely.ops import triangulate
    def coords(uv,axis,offset):
        u,v=uv
        return (u,v,offset) if axis=='z' else ((offset,u,v) if axis=='x' else (u,offset,v))
    axes=[('z',P['base_bottom']),('z',guide_bottom),('x',0),('x',W-T),('y',F),('y',B)]
    for ((label,poly),color,(axis,off)) in zip(pieces,colors,axes):
        for tri in triangulate(poly):
            if poly.covers(tri):
                uv=list(tri.exterior.coords)[:-1]
                face([coords(p,axis,off) for p in uv],color)
                face([coords(p,axis,off+T) for p in uv],color)
        for ring in loops(poly):
            for a,b in zip(ring,ring[1:]+ring[:1]):
                face([coords(a,axis,off),coords(b,axis,off),coords(b,axis,off+T),coords(a,axis,off+T)],color)
    # white backing is an optional contrast treatment; preview shows unpainted MDF.
    ax.add_collection3d(Poly3DCollection(faces,facecolors=face_colors,edgecolor='none'))
    tag_faces=[[(x,F-.05,z) for x,z in loops(tile)[0]] for tile in tag_cells]
    ax.add_collection3d(Poly3DCollection(tag_faces,facecolors='#211c17',edgecolor='none',zorder=10))
    angles=np.linspace(0,2*np.pi,40)
    for i,x in enumerate(P['slot_x']):
        r=v['vessel_diameter']/2
        xx=x+r*np.cos(angles); yy=P['slot_y']+r*np.sin(angles)
        zz=np.array([SEAT,SEAT+v['vessel_height']])
        ax.plot_surface(np.tile(xx,(2,1)),np.tile(yy,(2,1)),np.tile(zz[:,None],(1,len(xx))),color='#71b6cb',alpha=.24,shade=False)
        ax.plot(xx,yy,np.full_like(xx,SEAT+v['vessel_height']),color='#3a9bb5',lw=.9)
    ax.set(xlim=(0,W),ylim=(0,D),zlim=(0,SEAT+v['vessel_height']+8))
    ax.set_box_aspect((W,D,SEAT+v['vessel_height']+8));ax.view_init(elev=24,azim=-65)
    ax.set_xlabel('X / mm');ax.set_ylabel('Y / mm');ax.set_zlabel('Z / mm')
    ax.set_title(f'ATOM {name} | 5 x {v["vessel_diameter"]:g} dia. x {v["vessel_height"]:g} mm\nMDF 3 mm nominal | press-fit prototype | blue = vessel envelopes',loc='left')
    fig.tight_layout();fig.savefig(OUT/f'{name}_assembly.png',dpi=180);plt.close(fig)


def build_variant(name,v):
    guide_bottom=SEAT+v['guide_above_seat']
    base=shelf()
    holes=[Point(x,P['slot_y']).buffer((v['vessel_diameter']+P['hole_clearance_diameter'])/2,quad_segs=96) for x in P['slot_x']]
    guide=base.difference(unary_union(holes))
    side=end(guide_bottom); front=apron()
    pieces=[('BASE',base),('GUIDE',guide),('LEFT',side),('RIGHT',side),('FRONT',front),('BACK',front)]
    tag_cells=[]
    for x,tag_id in zip(P['slot_x'],v['tag_ids']):
        bits,_=marker(tag_id)
        tag_cells+=row_cells(bits,x-20,SEAT/2-20)
    # 600 x 450 mm candidate nesting, not a TCS bed-size assertion.
    placements=[(10,10),(10,105),(350,10),(455,10),(10,205),(10,285)]
    parts=[(label,poly,x,y,tag_cells if label=='FRONT' else [])
           for (label,poly),(x,y) in zip(pieces,placements)]
    for i,(_,a,x,y,_) in enumerate(parts):
        assert a.is_valid
        for _,b,xb,yb,_ in parts[i+1:]:
            assert translate(a,xoff=x,yoff=y).distance(translate(b,xoff=xb,yoff=yb))>5
    checks=write_job(f'{name}_cut_RASTER_REVIEW',parts,(600,450))
    review_flat(name,parts,(600,450))
    render_assembly(name,pieces,v,guide_bottom,tag_cells)
    dimensioned(name,v,guide_bottom,tag_cells)
    # Exact-scale front artwork, white border included. Contains no CUT paths.
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{SEAT}mm" viewBox="0 0 {W} {SEAT}">',
       f'<rect width="{W}" height="{SEAT}" fill="white"/>',f'<g transform="translate(0,{SEAT}) scale(1,-1)">']
    for cell in tag_cells:
        s.append('<polygon fill="black" points="'+' '.join(f'{x},{y}' for x,y in loops(cell)[0])+'"/>')
    s+=['</g></svg>'];(OUT/f'{name}_tags_PRINT_100percent.svg').write_text('\n'.join(s))
    checks.update({'hole_count':len(holes),'hole_diameter':v['vessel_diameter']+P['hole_clearance_diameter'],
        'rack_external_mm':[W,D,guide_bottom+T+8],'vessel_seat_z':SEAT,
        'vessel_exposed_above_guide_mm':v['vessel_height']-v['guide_above_seat']-T,
        'parts':{label:{'bounds_mm':list(poly.bounds),'area_mm2':poly.area} for label,poly in pieces},
        'slots':[{'slot':i+1,'tag_id':tag,'vessel_bottom_mm':[x,P['slot_y'],SEAT],
                  'tag_center_mm':[x,F,SEAT/2], 'tag_to_seat_translation_rack_axes_mm':[0,P['slot_y']-F,SEAT/2]}
                 for i,(x,tag) in enumerate(zip(P['slot_x'],v['tag_ids']))]})
    # All end-panel openings are interior, with no accidentally open boundary.
    assert len(side.interiors)==8
    assert len(guide.interiors)==5
    REPORT['variants'][name]=checks


def dimensioned(name,v,guide_bottom,cells):
    fig,axes=plt.subplots(3,1,figsize=(13,10),gridspec_kw={'height_ratios':[1,1.15,1.25]})
    height=guide_bottom+T+8
    def rect(ax,x,y,w,h,color='#d5b07b'):
        ax.add_patch(plt.Rectangle((x,y),w,h,facecolor=color,edgecolor='#544638',lw=.8))
    ax=axes[0];rect(ax,0,0,W,D)
    for x in P['slot_x']:
        ax.add_patch(Circle((x,P['slot_y']),(v['vessel_diameter']+.6)/2,facecolor='white',edgecolor='#544638'))
        ax.plot([x-3,x+3],[P['slot_y'],P['slot_y']],color='#548092',lw=.6)
    ax.text(W/2,D+6,f'TOP | 5 x diameter {v["vessel_diameter"]+.6:.1f} | pitch 60 | centres X=40,100,160,220,280; Y=45',ha='center',fontsize=10)
    ax.set(xlim=(-12,W+12),ylim=(-10,D+18))
    ax=axes[1];rect(ax,0,0,W,SEAT)
    for x in [0,W-T]:rect(ax,x,0,T,height)
    rect(ax,T,guide_bottom,W-2*T,T)
    for cell in cells:
        ax.add_patch(PatchPolygon(loops(cell)[0],facecolor='#201c18',edgecolor='none'))
    ax.annotate('',xy=(0,-7),xytext=(W,-7),arrowprops={'arrowstyle':'<->'})
    ax.text(W/2,-10,'320 overall',ha='center',va='top',fontsize=9)
    ax.text(W/2,height+8,f'FRONT | 40 mm black tag border + 5 mm quiet margin | tag centre Z={SEAT/2:g}',ha='center',fontsize=10)
    ax.set(xlim=(-12,W+12),ylim=(-22,height+20))
    ax=axes[2];rect(ax,0,0,D,height,color='#f1e4cd')
    rect(ax,F,0,T,SEAT);rect(ax,B,0,T,SEAT)
    for z in [P['base_bottom'],guide_bottom]:rect(ax,F+T,z,B-F-T,T)
    rect(ax,P['slot_y']-v['vessel_diameter']/2,SEAT,v['vessel_diameter'],v['vessel_height'],color='#c7e5eb')
    for z,label in [(SEAT,f'seat Z={SEAT:g}'),(guide_bottom+T,f'guide top Z={guide_bottom+T:g}'),
                    (SEAT+v['vessel_height'],f'vessel top Z={SEAT+v["vessel_height"]:g}')]:
        ax.plot([D,D+12],[z,z],color='#777',lw=.5);ax.text(D+14,z,label,va='center',fontsize=9)
    ax.text(0,SEAT+v['vessel_height']+16,f'SIDE | depth {D:g} | rack height {height:g} | exposed vessel {v["vessel_height"]-v["guide_above_seat"]-T:g}',fontsize=10)
    ax.set(xlim=(-12,W+12),ylim=(-8,SEAT+v['vessel_height']+30))
    for ax in axes:
        ax.set_aspect('equal');ax.axis('off')
    fig.suptitle(f'ATOM {name.upper()} / DIMENSIONED ASSEMBLY REVIEW / ALL DIMENSIONS mm\n3 mm MDF nominal; no physical measurements; not a laser job file',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.94))
    fig.savefig(OUT/f'{name}_dimensioned.svg');fig.savefig(OUT/f'{name}_dimensioned.png',dpi=160);plt.close(fig)


def coupon():
    # Individual test sockets mimic a 12 mm tab and the same 3 mm through-thickness.
    slots=[round(T+d,2) for d in [-.20,-.15,-.10,-.05,0,.05,.10]]
    comb=box(0,0,155,32)
    for i,sw in enumerate(slots):
        cx=12+i*21
        comb=comb.difference(box(cx-6.1,12-sw/2,cx+6.1,12+sw/2))
    male=unary_union([box(0,0,24,18),box(6,18,18,18+T)])
    bits,_=marker(10)
    cells=row_cells(bits,10,10)
    tagplate=box(0,0,60,60)
    parts=[('SLOTS left-to-right '+str(slots),comb,10,10,[]),('INSERT 12 mm tab',male,180,10,[]),
           ('TAG 10 | 40 mm border',tagplate,10,65,cells)]
    REPORT['coupon']=write_job('fit_and_tag_coupon_FIRST',parts,(230,145))
    REPORT['coupon']['finished_slot_widths_mm']=slots
    review_flat('fit_and_tag_coupon',parts,(230,145))


if __name__=='__main__':
    assert 0<P['interference']<T and 0<=P['kerf']<T/2
    for name,v in P['variants'].items(): build_variant(name,v)
    coupon()
    REPORT['opencv_version']=cv2.__version__
    REPORT['validation_scope']='Digital geometry/export and synthetic ID decoding only; zero physical fit/load/camera samples.'
    REPORT['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (OUT/'geometry_checks.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
    print('Generated two 6-panel rack prototypes, fit/tag coupon and reviews; digital checks passed.')
