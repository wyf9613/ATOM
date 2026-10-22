"""Review figure from the computed geometry and temporary handle render."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Polygon,Circle
import compare_sections as model

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
plt.rcParams['font.family']=FontProperties(fname='C:/Windows/Fonts/msyh.ttc').get_name()
plt.rcParams['svg.fonttype']='path'
plt.rcParams['axes.unicode_minus']=False
ink='#21334a'; blue='#167cba'; green='#138b83'; orange='#ce832c'
fig=plt.figure(figsize=(16,9),facecolor='#f4f7fa')
fig.text(.04,.94,'ATOM｜力学筛查结论 + 径向直棒把手',fontsize=23,color=ink,weight='bold')
fig.text(.04,.895,'2026-10-21 · 暂按全 PETG 打印 · 截面/名义应力分析，未做 FEA，未改制造 CAD',fontsize=11,color='#56677c')
def panel(rect,title):
    a=fig.add_axes(rect); a.set_facecolor('white')
    for s in a.spines.values(): s.set_color('#d9e1ea')
    a.set_xticks([]); a.set_yticks([])
    a.set_title(title,loc='left',fontsize=15,color=ink,pad=14,weight='bold')
    return a
a=panel([.04,.29,.40,.55],'01  根部截面｜局部收肩，保留侧向材料')
a.set_aspect('equal'); a.set_xlim(-61,61); a.set_ylim(-66,67)
g=model.section(40.8001,'flat_caps')
a.add_patch(Polygon(np.array(g.exterior.coords),fc='#b4ded7',ec=green,lw=2))
for r in g.interiors:
    a.add_patch(Polygon(np.array(r.coords),fc='white',ec=green,lw=.7))
a.add_patch(Circle((0,0),42,fill=False,ec='#8a98a9',ls='--',lw=1.5))
t=np.linspace(0,2*np.pi,500)
a.plot(42*np.cos(t),36.5*np.sin(t),c=orange,ls=':',lw=1.5)
a.text(-56,58,'灰虚线：原圆根部',fontsize=9,color=ink)
a.text(-56,49,'橙点线：上一版完整椭圆',fontsize=9,color=orange)
a.text(-56,-53,'绿：只局部收掉上下面，避免过多削薄',fontsize=9,color=green)
a.text(-56,-63,'示意未加最终过渡圆角；安装耳另行加强。',fontsize=8,color=ink)

b=panel([.50,.29,.46,.55],'02  轴线指向圆心｜直接径向连接')
b.set_xlim(0,100); b.set_ylim(0,100)
im=plt.imread(ROOT/'tmp/backplate_review/handle_rev03_render.png')
b.imshow(im,extent=(0,100,6,100))
b.plot([28,78],[58,43],color=orange,ls='--',lw=1.3)
b.text(4,92,'独立法兰环 + 加粗根部 + 棒状握柄',fontsize=10,color=blue)
b.text(18,18,'握柄中心线向内延长经过法兰圆心',fontsize=10,color=blue)
b.annotate('',xy=(53,50),xytext=(53,24),arrowprops=dict(arrowstyle='->',color=blue))
b.text(4,6,'无 90° 转向杆；具体尺寸、定位和安装净空待验证。',fontsize=8,color=ink)

r=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
root={s['variant']:s for s in r['sections'] if s['location']=='root_start'}
stress=[100*(root['v2']['Wy_mm3']/root[k]['Wy_mm3']-1) for k in ['narrow','flat_caps']]
fig.text(.04,.21,f'相同根部 My 弯矩：完整椭圆的名义应力约 +{stress[0]:.0f}%；局部削肩约 +{stress[1]:.0f}%。',fontsize=12,color=ink)
fig.text(.04,.162,'安装耳净边料从 5.8 mm 减至 2.1 mm，是独立薄弱项；不能靠圆筒截面改善就认为耳片等强。',fontsize=11,color=ink)
fig.text(.04,.111,'建议继续研究：保留侧向材料、背面加厚/加强耳根、把手根部连续圆滑；全打印 PETG 路线。',fontsize=11,color=green)
fig.text(.04,.065,'这些数值是 CAD 名义几何下的对比，不是整件强度变化或允许载荷。材料牌号、层向、工况和实物承载仍待验证。',fontsize=9,color='#56677c')
fig.savefig(HERE.parent/'concept_rev03.png',dpi=150,facecolor=fig.get_facecolor())
fig.savefig(HERE.parent/'concept_rev03.svg',facecolor=fig.get_facecolor())
print(HERE.parent/'concept_rev03.png')
