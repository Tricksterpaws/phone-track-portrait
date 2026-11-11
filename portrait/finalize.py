import json, numpy as np, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)
raw=json.load(open(WORK/'raw2.json')); ref=json.load(open(WORK/'ref.json'))
W,H=ref['W'],ref['H']; N=len(raw['border']); first=ref['first']
def cyc(q):
    q=np.array(q,float); c=q.mean(0)
    return q[np.argsort(np.arctan2(q[:,1]-c[1],q[:,0]-c[0]))]
Q=[]
for n in range(N):
    r=cyc(raw['quad'][str(n)]); f=cyc(ref['quad'][str(n)])
    diag=np.linalg.norm(r[0]-r[2])+1e-6
    # match f's rotation to r
    best=min(range(4),key=lambda k:np.abs(np.roll(f,-k,0)-r).sum()); f=np.roll(f,-best,0)
    dev=np.linalg.norm(f-r,axis=1).max()/diag
    use = f if (n<first or (dev<0.18 and not raw['border'][n])) else r
    Q.append(use)
Q=np.array(Q)
# --- orientation
def align(prev,q):
    k=min(range(4),key=lambda k:np.linalg.norm(np.roll(q,-k,0)-prev,axis=1).sum()); return np.roll(q,-k,0)
end=N-1
q=Q[end]; i=np.argmin(q.sum(1)); Q[end]=np.roll(q,-i,0)
for n in range(end-1,243,-1): Q[n]=align(Q[n+1],Q[n])
# lying phone: top = right-hand short edge, TL = upper point of that edge
for n in range(0,201):
    q=Q[n]; best=None
    for k in range(4):
        r=np.roll(q,-k,0); topc=(r[0]+r[1])/2; botc=(r[2]+r[3])/2
        L01=np.linalg.norm(r[1]-r[0]); L12=np.linalg.norm(r[2]-r[1])
        if L01<L12 and topc[0]>botc[0] and r[0][1]<r[1][1]: best=r
    Q[n]=best if best is not None else Q[n]
for n in range(201,244): Q[n]=align(Q[n-1],Q[n])
print("check 243->244 alignment err", np.linalg.norm(Q[243]-Q[244],axis=1).round(1))
json.dump({"Q":Q.tolist()},open(WORK/'oriented.json','w'))
