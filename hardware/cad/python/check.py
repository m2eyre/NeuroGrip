from build import *
for name, f in [('base',base()),('driver',finger(True)),('idler',finger(False)),('wrist',wrist_mount()),('servo',servo())]:
    print(name, 'vol %.1f cm3'%(f.volume()/1000), 'genus', f.genus(), 'bbox', [round(v,1) for v in f.bounding_box()])
def inter(a,b): return (a ^ b).volume()
for ang in (0, 10, 20, 30, 40, 50):
    P = assembly(ang)
    pairs = [('driver','idler'),('driver','base'),('idler','base'),('driver','servo'),('idler','servo'),('base','wrist'),('base','servo')]
    print(ang, {f'{a}-{b}': round(inter(P[a],P[b]),2) for a,b in pairs})
