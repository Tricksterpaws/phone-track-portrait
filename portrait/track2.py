import cv2, numpy as np, sys, json
src=sys.argv[1]; out=sys.argv[2]
cap=cv2.VideoCapture(src); frames=[]
while True:
    ok,f=cap.read()
    if not ok: break
    frames.append(f)
N=len(frames); H,W=frames[0].shape[:2]
def ss(a,b_,x): t=np.clip((x-a)/(b_-a),0,1); return t*t*(3-2*t)
def chroma(img):
    c=img.astype(np.float32)/255; b,g,r=c[...,0],c[...,1],c[...,2]
    sep=np.minimum(g-r,g-b)
    return ss(.42,.62,g)*(1-ss(.40,.62,np.maximum(r,b)))*ss(.15,.28,sep)
def cyc(q):
    q=np.array(q,float).reshape(4,2); c=q.mean(0)
    return q[np.argsort(np.arctan2(q[:,1]-c[1],q[:,0]-c[0]))]
raw=[None]*N; area=np.zeros(N); border=np.zeros(N,bool); prevbox=None
for n in range(N):
    m=(chroma(frames[n])>0.5).astype(np.uint8)
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    k,lab,st,_=cv2.connectedComponentsWithStats(m)
    if k<=1: continue
    ids=[i for i in range(1,k) if st[i,4]>=40]
    
    if not ids: continue
    big=max(ids,key=lambda i:st[i,4])
    if st[big,4]<800: continue
    x,y,w,h=st[big,:4]; pad=max(w,h)*0.08+4
    keep=[i for i in ids if st[i,0]<x+w+pad and st[i,0]+st[i,2]>x-pad and st[i,1]<y+h+pad and st[i,1]+st[i,3]>y-pad]
    pts=np.vstack([np.argwhere(lab==i)[:,::-1] for i in keep]).astype(np.int32)
    hull=cv2.convexHull(pts)
    raw[n]=cyc(cv2.approxPolyN(hull,4,ensure_convex=True).reshape(-1,2))
    area[n]=sum(st[i,4] for i in keep)
    bx,by,bw,bh=cv2.boundingRect(pts)
    border[n]=bx<=1 or by<=1 or bx+bw>=W-1 or by+bh>=H-1
first=next(i for i in range(N) if raw[i] is not None)
print("first green",first)
# --- pre-green: feature-track backwards from `first`
quad={first:raw[first]}
g=lambda f:cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
cur=raw[first].copy()
for n in range(first-1,-1,-1):
    a=g(frames[n+1]); b=g(frames[n])
    c=cur.mean(0); mask=np.zeros_like(a)
    big=(cur-c)*3.0+c
    cv2.fillConvexPoly(mask,big.astype(np.int32),255)
    p0=cv2.goodFeaturesToTrack(a,400,0.005,5,mask=mask)
    p1,stt,_=cv2.calcOpticalFlowPyrLK(a,b,p0,None,winSize=(31,31),maxLevel=4)
    s=stt.ravel()==1
    Hm,_=cv2.findHomography(p0[s],p1[s],cv2.RANSAC,2.0)
    cur=cv2.perspectiveTransform(cur.reshape(-1,1,2),Hm).reshape(4,2)
    quad[n]=cur.copy()
for n in range(first+1,N):
    if raw[n] is not None: quad[n]=raw[n]
json.dump({"W":W,"H":H,"first":first,"area":area.tolist(),"border":border.tolist(),
  "quad":{str(k):np.asarray(v).round(3).tolist() for k,v in quad.items()}},open(out,"w"))
