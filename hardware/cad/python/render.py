from build import *
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
COL={'wrist':'#8fa3b8','base':'#e07b39','servo':'#3b6fd6','driver':'#f2c14e','idler':'#5bb381'}
def draw(ax, P, elev, azim):
    for k,mf in P.items():
        m=tm(mf); 
        n=m.face_normals; light=np.clip(0.35+0.65*(n@np.array([0.3,-0.5,0.8])/np.linalg.norm([0.3,-0.5,0.8])),0.2,1)
        base=np.array(matplotlib.colors.to_rgb(COL[k]))
        pc=Poly3DCollection(m.triangles, facecolors=base*light[:,None], edgecolor='none')
        ax.add_collection3d(pc)
    ax.set_xlim(-40,40); ax.set_ylim(-40,40); ax.set_zlim(-25,55)
    ax.set_box_aspect((1,1,1)); ax.view_init(elev,azim); ax.axis('off')
fig=plt.figure(figsize=(14,7),dpi=110)
for i,(ang,el,az,t) in enumerate([(0,25,-60,'Closed'),(25,25,-60,'Open 25°'),(25,80,-90,'Top view, open 25°')]):
    ax=fig.add_subplot(1,3,i+1,projection='3d'); draw(ax, assembly(ang), el, az); ax.set_title(t)
plt.tight_layout(); plt.savefig('neurogrip_render.png',bbox_inches='tight')
# gear mesh close-up top view
fig,axs=plt.subplots(1,3,figsize=(15,5.5),dpi=110)
for ax,ang in zip(axs,(0,15,35)):
    for k in ('base','driver','idler'):
        P=assembly(ang)
        cs=P[k].slice(RAIL_TOP+GEAR_Z+3 if k!='base' else RAIL_TOP+DECK-1)
        for poly in cs.to_polygons():
            e=np.vstack([poly,poly[:1]]); ax.plot(e[:,0],e[:,1],color=COL[k],lw=1.2)
    ax.set_aspect('equal'); ax.set_title(f'Gear plane section, open {ang}°'); ax.grid(alpha=.3)
plt.tight_layout(); plt.savefig('gear_mesh.png',bbox_inches='tight')
