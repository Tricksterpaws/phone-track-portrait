import json, numpy as np, cv2
from pathlib import Path
from scipy.signal import medfilt
from scipy.ndimage import gaussian_filter1d
ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)
Q=np.array(json.load(open(WORK/'oriented.json'))['Q']); N=len(Q); W,H=1080,1440
border=json.load(open(WORK/'raw2.json'))['border']
ASPECT=None
def sim_from2(a0,a1,b0,b1):
    # similarity mapping a0->b0, a1->b1 (complex numbers)
    A0,A1,B0,B1=[complex(*p) for p in (a0,a1,b0,b1)]
    s=(B1-B0)/(A1-A0); t=B0-s*A0
    return lambda P: np.array([[ (s*complex(*p)+t).real,(s*complex(*p)+t).imag] for p in P])
# 1) pickup, flat phase
REF=196; ref=Q[REF].copy()
for n in range(REF+1,224):
    f=sim_from2(ref[0],ref[1],Q[n][0],Q[n][1]); Q[n]=f(ref)
# 2b) tilt-up + lift: blend shape between anchors as similarity, anchor TL on detection
CLEAN=258
def params(q):
    v=q[1]-q[0]; return np.arctan2(v[1],v[0]), np.linalg.norm(v)
def canon(q,a,s):
    R=np.array([[np.cos(-a),-np.sin(-a)],[np.sin(-a),np.cos(-a)]]); return ((q-q[0])@R.T)/s
ANCH=[215,236,CLEAN]
# anchor 236: bottom is under the fingers -> take long-edge/top-edge ratio from the clean frame
def ratio(q): return (np.linalg.norm(q[3]-q[0])+np.linalg.norm(q[2]-q[1]))/2/np.linalg.norm(q[1]-q[0])
q=Q[236].copy(); L=ratio(Q[CLEAN])*np.linalg.norm(q[1]-q[0])
dl=(q[3]-q[0])/np.linalg.norm(q[3]-q[0]); dr=(q[2]-q[1])/np.linalg.norm(q[2]-q[1])
q[3]=q[0]+dl*max(L,np.linalg.norm(q[3]-q[0])); q[2]=q[1]+dr*max(L,np.linalg.norm(q[2]-q[1])); Q[236]=q
tl=gaussian_filter1d(Q[ANCH[0]:CLEAN+1,0],1.5,axis=0)
for A,B in zip(ANCH[:-1],ANCH[1:]):
    aA,sA=params(Q[A]); aB,sB=params(Q[B])
    cA=canon(Q[A],aA,sA); cB=canon(Q[B],aB,sB)
    da=np.arctan2(np.sin(aB-aA),np.cos(aB-aA))
    for n in range(A+1,B):
        t=(n-A)/(B-A); t=t*t*(3-2*t) if False else t
        a_=aA+da*t; s_=sA*(sB/sA)**t; cc=cA*(1-t)+cB*t
        R=np.array([[np.cos(a_),-np.sin(a_)],[np.sin(a_),np.cos(a_)]])
        Q[n]=(cc*s_)@R.T+tl[n-ANCH[0]]
# 3) generic outlier repair (outside pickup)
med=np.stack([np.stack([medfilt(Q[:,k,j],9) for j in range(2)],-1) for k in range(4)],1)
err=np.linalg.norm(Q-med,axis=2).max(1); diag=np.linalg.norm(Q[:,0]-Q[:,2],axis=1)
for n in np.where(err>0.03*diag+3)[0]:
    if not (REF<n<CLEAN+6) and not border[n]: Q[n]=med[n]
# 4) push-in: rebuild clipped frames as axis-aligned rect from aspect
clean=[n for n in range(440,N) if not border[n]]; last=max(clean)
ws=[(np.linalg.norm(Q[n][1]-Q[n][0])+np.linalg.norm(Q[n][2]-Q[n][3]))/2 for n in range(last-10,last+1)]
hs=[(np.linalg.norm(Q[n][3]-Q[n][0])+np.linalg.norm(Q[n][2]-Q[n][1]))/2 for n in range(last-10,last+1)]
ASPECT=float(np.median(np.array(ws)/np.array(hs)))
cy=np.array([Q[n][:,1].mean() for n in range(last-12,last+1)]); vy=np.polyfit(np.arange(13),cy,1)[0]
print('last clean',last,'aspect',ASPECT,'cy vel',vy)
# horizontal edges visible?  left/right x from data while not on border
xl=[];xr=[]
for n in range(last+1,N):
    q=Q[n]; l=min(q[0][0],q[3][0]); r=max(q[1][0],q[2][0])
    xl.append(l); xr.append(r)
xl=np.array(xl); xr=np.array(xr); ns=np.arange(last+1,N)
okx=(xl>2)&(xr<W-3)
# fit log width on valid, extrapolate where invalid
wv=xr-xl; cx=(xl+xr)/2
p=np.polyfit(ns[okx][-20:],np.log(wv[okx][-20:]),2); pc=np.polyfit(ns[okx][-20:],cx[okx][-20:],1)
cy0=Q[last][:,1].mean()
for i,n in enumerate(ns):
    if okx[i]: w=wv[i]; c=cx[i]
    else: w=np.exp(np.polyval(p,n)); c=np.polyval(pc,n)
    h=w/ASPECT; k=n-last; cyn=cy0+vy*k*np.exp(-k/40)  # damped drift
    Q[n]=np.array([[c-w/2,cyn-h/2],[c+w/2,cyn-h/2],[c+w/2,cyn+h/2],[c-w/2,cyn+h/2]])
# 5) smoothing (segment-wise, light)
segs=[(0,48),(48,REF+1),(REF+1,N)]
S=Q.copy()
for a,b in segs:
    sig=2.0 if (a,b)==(0,48) else (1.0 if a<REF else 1.2)
    S[a:b]=gaussian_filter1d(Q[a:b],sig,axis=0,mode='nearest')
json.dump({"Q":S.tolist(),"aspect":ASPECT},open(WORK/'final.json','w'))
