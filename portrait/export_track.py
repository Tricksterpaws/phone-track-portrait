import cv2, numpy as np, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)
Qd=json.load(open(WORK/'final.json')); Q=np.array(Qd['Q']); aspect=Qd['aspect']
cap=cv2.VideoCapture(str(ROOT/'plate_portrait.mp4')); N=len(Q); W,H=1080,1440
def ss(a,b_,x): t=np.clip((x-a)/(b_-a),0,1); return t*t*(3-2*t)
def chroma(img):
    c=img.astype(np.float32)/255; b,g,r=c[...,0],c[...,1],c[...,2]
    sep=np.minimum(g-r,g-b)
    return ss(.42,.62,g)*(1-ss(.40,.62,np.maximum(r,b)))*ss(.15,.28,sep)
UNIT=np.float32([[0,0],[1,0],[1,1],[0,1]])
slack=[]; n=0
while True:
    ok,f=cap.read()
    if not ok: break
    q=Q[n].astype(np.float32)
    m=(chroma(f)>0.35).astype(np.uint8)
    zone=np.zeros_like(m); c=q.mean(0); cv2.fillConvexPoly(zone,((q-c)*1.5+c).astype(np.int32),1)
    # don't count the background monitors region far above the phone
    k,lab,st,_=cv2.connectedComponentsWithStats(m&zone)
    pts=[]
    for i in range(1,k):
        if st[i,4]>=6: pts.append(np.argwhere(lab==i)[:,::-1])
    s=0.02
    if pts:
        P=np.vstack(pts).astype(np.float32)
        Hinv=cv2.getPerspectiveTransform(q,UNIT)
        U=cv2.perspectiveTransform(P.reshape(-1,1,2),Hinv).reshape(-1,2)
        ex=np.maximum(np.maximum(-U,U-1),0).max(1)
        s=float(np.percentile(ex,99.9))+0.02 if len(ex) else 0.02
    slack.append(min(round(s,3),0.4)); n+=1
sl=np.array(slack)
# smooth up (max filter) so it never under-covers between frames
from scipy.ndimage import maximum_filter1d
sl=maximum_filter1d(sl,3)
print('frames with slack>0.03:',int((sl>0.03).sum()),'max',sl.max())
print([ (i,round(float(sl[i]),2)) for i in range(N) if sl[i]>0.06])
out={"fps":24.0,"width":W,"height":H,"frameCount":N,"screenAspect":round(aspect,4),
     "cornerRadius":round(0.1247*aspect,4),"keyFrom":48,
     "frames":[[round(float(v),2) for v in Q[i].reshape(-1)] for i in range(N)],
     "slack":[round(float(v),3) for v in sl]}
json.dump(out,open(WORK/'portrait.json','w'),separators=(',',':'))
