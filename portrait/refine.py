import cv2, numpy as np, json, sys
src,rawp,out=sys.argv[1:4]
d=json.load(open(rawp)); first=d['first']; W,H=d['W'],d['H']
cap=cv2.VideoCapture(src); frames=[]
while True:
    ok,f=cap.read()
    if not ok: break
    frames.append(f)
N=len(frames)
def ss(a,b_,x): t=np.clip((x-a)/(b_-a),0,1); return t*t*(3-2*t)
def chroma(img):
    c=img.astype(np.float32)/255; b,g,r=c[...,0],c[...,1],c[...,2]
    sep=np.minimum(g-r,g-b)
    return ss(.42,.62,g)*(1-ss(.40,.62,np.maximum(r,b)))*ss(.15,.28,sep)
def fitline(P):
    c=P.mean(0); u,s,vt=np.linalg.svd(P-c); dvec=vt[0]; nrm=np.array([-dvec[1],dvec[0]])
    return nrm, nrm@c
def inter(l1,l2):
    A=np.array([l1[0],l2[0]]); b=np.array([l1[1],l2[1]])
    return np.linalg.solve(A,b)
quads={}; quality={}
for n in range(N):
    q=np.array(d['quad'][str(n)])
    if n<first: quads[n]=q; quality[n]=1.0; continue
    m=(chroma(frames[n])>0.5).astype(np.uint8)
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    # keep pixels near the raw quad
    zone=np.zeros_like(m); c=q.mean(0)
    cv2.fillConvexPoly(zone,((q-c)*1.6+c).astype(np.int32),1); m&=zone
    cnts,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    P=np.vstack([c_.reshape(-1,2) for c_ in cnts]).astype(float)
    hull=cv2.convexHull(P.astype(np.float32))
    dist=np.array([cv2.pointPolygonTest(hull,(float(x),float(y)),True) for x,y in P])
    P=P[dist<1.6]
    # drop points on the image border (clipped edges)
    onb=(P[:,0]<=1)|(P[:,1]<=1)|(P[:,0]>=W-2)|(P[:,1]>=H-2)
    cur=q.copy(); lines=[None]*4; support=[0]*4
    for it in range(3):
        for k in range(4):
            a,b=cur[k],cur[(k+1)%4]; L=np.linalg.norm(b-a); t_=(b-a)/L; nv=np.array([-t_[1],t_[0]])
            rel=P-a; s=rel@t_/L; dd=np.abs(rel@nv)
            sel=(s>0.15)&(s<0.85)&(dd<max(3,0.04*L))&~onb
            support[k]=sel.sum()/max(1,0.7*L)
            lines[k]=fitline(P[sel]) if sel.sum()>=6 else None
        new=cur.copy()
        for k in range(4):
            l1,l2=lines[(k-1)%4],lines[k]
            if l1 is not None and l2 is not None:
                try: new[k]=inter(l1,l2)
                except np.linalg.LinAlgError: pass
        cur=new
    quads[n]=cur; quality[n]=float(min(support))
json.dump({"W":W,"H":H,"first":first,"quad":{k:v.round(3).tolist() for k,v in quads.items()},"quality":quality,"border":d['border']},open(out,"w"))
