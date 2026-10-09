# SPDX-License-Identifier: MIT
"""Spherical skies: periodic longitude, latitude-correct poles, no edge extrusion."""
from pathlib import Path
import json, hashlib
import numpy as np
from PIL import Image
HERE=Path(__file__).parent

def smooth(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)

def lowpass_rows(x,sigma):
 # Vertical gaussian low-pass of a per-row colour signal, edges held.
 r=int(3*sigma);k=np.exp(-.5*(np.arange(-r,r+1)/sigma)**2);k/=k.sum()
 return np.stack([np.convolve(np.pad(x[:,c],r,mode='edge'),k,'valid') for c in range(x.shape[1])],1)

def join(a,width=160,sigma=16):
 # Periodic longitude join without double exposure. 0.7.0 cross-faded each
 # edge with its mirror image and spread every row's full seam offset over
 # the whole width, which superimposed ghost copies and row streaks. Here
 # only the vertically low-passed colour difference at the seam is split
 # between both edges and faded out over `width` columns. Detail is never
 # blended: what remains is one clean cut, placed behind the Signal massif.
 h,w,_=a.shape
 d=lowpass_rows(a[:,0]-a[:,-1],sigma);f=.5*(1+np.cos(np.pi*np.arange(width)/width))
 a[:,:width]-=d[:,None]*f[None,:,None]/2
 a[:,w-width:]+=d[:,None]*f[::-1][None,:,None]/2
 # Above the painted peaks (~26 deg) the massif no longer hides the cut, so
 # cloud rows soften gradually towards the seam (wrapped gaussian, feathered
 # over 64 columns each side): softer cloud, never a second copy.
 lat=90-(np.arange(h)+.5)/h*180;rows=np.nonzero(lat>22)[0];r=64;sig=9
 ring=np.concatenate([a[rows][:,w-1-r:w-1],a[rows][:,:r+1]],axis=1)
 k=np.exp(-.5*(np.arange(-3*sig,3*sig+1)/sig)**2);k/=k.sum()
 pad=np.concatenate([a[rows][:,w-1-r-3*sig:w-1],a[rows][:,:r+1+3*sig]],axis=1)
 soft=np.stack([np.apply_along_axis(lambda v:np.convolve(v,k,'valid'),1,pad[...,c]) for c in range(3)],-1)
 t=smooth((lat[rows]-22)/6)[:,None,None]*smooth(1-np.abs(np.arange(-r,r+1))/r)[None,:,None]
 ring=ring*(1-t)+soft*t
 # Column w-1 is overwritten by column 0 in save().
 a[rows,w-1-r:w-1]=ring[:,:r];a[rows,:r+1]=ring[:,r:]
 return a

def night_sky(h=1024,w=2048):
 # Band-limited basin sky. Its near walls stand 1-20 m from the yard, where
 # one texel covers dozens of 4K pixels; the painted master magnified like
 # that read as blocks and concentric rings. Only smooth gradients and soft,
 # broad ridge bands remain, periodic in longitude, every texel step small.
 lat=(90-(np.arange(h)+.5)/h*180)[:,None,None];u=((np.arange(w)+.5)/w)[None,:,None]
 zen=np.array([3,16,42]);mid=np.array([10,32,66]);hor=np.array([34,58,92]);ground=np.array([14,22,32])
 up=hor+(mid-hor)*smooth(lat/30);up=up+(zen-up)*smooth((lat-30)/60)
 sky=np.where(lat>=0,up,hor+(ground-hor)*smooth(-lat/20))
 wave=lambda terms:sum(a*np.sin(2*np.pi*(f*u+ph)) for a,f,ph in terms)
 for top,colour,edge in [(3.0+2.2*wave([(.5,3,.13),(.3,5,.41),(.2,8,.77)]),np.array([22,38,62]),5.5),(1.2+wave([(.6,4,.6),(.4,7,.2)]),np.array([13,24,40]),5.0)]:
  fill=colour+(ground-colour)*smooth(-lat/20);cover=1-smooth((lat-top+edge/2)/edge)
  sky=sky+(fill-sky)*cover
 return sky

def save(name,a):
 h,w,_=a.shape
 # Rows under the polar fans (<=40 rows) are fully uniform, so the fans
 # cannot pinch longitude detail into a pinwheel; then fade over 100 rows.
 for edge,rows in [(0,range(140)),(-1,range(h-140,h))]:
  color=a[edge].mean(axis=0)
  for y in rows:
   dist=y if edge==0 else h-1-y;t=smooth(1-(dist-40)/100)
   a[y]=a[y]*(1-t)+color*t
 a=np.round(np.clip(a,0,255)).astype('uint8');a[:,-1]=a[:,0]
 a[0]=a[0].mean(axis=0).round().astype('uint8');a[-1]=a[-1].mean(axis=0).round().astype('uint8')
 path=HERE/'tiles'/f'{name}-albedo.png';Image.fromarray(a).save(path,optimize=True)
 return {'name':name,'size':[w,h],'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'longitudeEdgeMax':int(abs(a[:,0].astype(int)-a[:,-1]).max()),'poleRangeMax':int(max(np.ptp(a[0],axis=0).max(),np.ptp(a[-1],axis=0).max()))}

def prepare():
 day=np.array(Image.open(HERE/'source/sky-v7.png').convert('RGB').resize((2048,1024),Image.Resampling.LANCZOS),dtype=float)
 rows=[save('sky-v7',join(day))]
 rows.append(save('night-sky-v7',night_sky()))
 (HERE/'tiles/sky-report.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':prepare()
