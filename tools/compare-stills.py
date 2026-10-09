#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""PSNR (RGB, 8-bit) and CIEDE2000 deltaE (sRGB D65 -> Lab) between stills at
identical poses. Pairs: a.png=b.png ... ; JSON to stdout or --output."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
def lab(rgb):
 c=rgb/255.;c=np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
 xyz=c@np.array([[.4124564,.3575761,.1804375],[.2126729,.7151522,.0721750],[.0193339,.1191920,.9503041]]).T/np.array([.95047,1.,1.08883])
 f=np.where(xyz>(6/29)**3,np.cbrt(xyz),xyz/(3*(6/29)**2)+4/29)
 return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],-1)
def de2000(a,b):
 L1,a1,b1=a[...,0],a[...,1],a[...,2];L2,a2,b2=b[...,0],b[...,1],b[...,2]
 C1=np.hypot(a1,b1);C2=np.hypot(a2,b2);Cm=(C1+C2)/2;G=.5*(1-np.sqrt(Cm**7/(Cm**7+25**7)))
 a1p=(1+G)*a1;a2p=(1+G)*a2;C1p=np.hypot(a1p,b1);C2p=np.hypot(a2p,b2)
 h1=np.degrees(np.arctan2(b1,a1p))%360;h2=np.degrees(np.arctan2(b2,a2p))%360
 dL=L2-L1;dC=C2p-C1p;dh=h2-h1;dh=np.where(dh>180,dh-360,np.where(dh<-180,dh+360,dh));dh=np.where(C1p*C2p==0,0,dh);dH=2*np.sqrt(C1p*C2p)*np.sin(np.radians(dh)/2)
 Lm=(L1+L2)/2;Cmp=(C1p+C2p)/2;hs=h1+h2;hm=np.where(C1p*C2p==0,hs,np.where(np.abs(h1-h2)<=180,hs/2,np.where(hs<360,(hs+360)/2,(hs-360)/2)))
 T=1-.17*np.cos(np.radians(hm-30))+.24*np.cos(np.radians(2*hm))+.32*np.cos(np.radians(3*hm+6))-.2*np.cos(np.radians(4*hm-63))
 SL=1+.015*(Lm-50)**2/np.sqrt(20+(Lm-50)**2);SC=1+.045*Cmp;SH=1+.015*Cmp*T
 RT=-2*np.sqrt(Cmp**7/(Cmp**7+25**7))*np.sin(np.radians(60*np.exp(-((hm-275)/25)**2)))
 return np.sqrt((dL/SL)**2+(dC/SC)**2+(dH/SH)**2+RT*(dC/SC)*(dH/SH))
p=argparse.ArgumentParser(description=__doc__);p.add_argument('pairs',nargs='+');p.add_argument('--output',type=Path);a=p.parse_args()
rows=[]
for pair in a.pairs:
 x,y=pair.split('=');A=np.asarray(Image.open(x).convert('RGB'),dtype=np.float64);B=np.asarray(Image.open(y).convert('RGB'),dtype=np.float64)
 mse=((A-B)**2).mean();d=de2000(lab(A[::2,::2]),lab(B[::2,::2]))
 rows.append({'a':x,'b':y,'psnrDb':round(float(10*np.log10(255**2/mse)) if mse else 99.0,2),'deltaE2000Mean':round(float(d.mean()),3),'deltaE2000P95':round(float(np.percentile(d,95)),3),'pixelsOver2':round(float((d>2).mean()),5)})
text=json.dumps(rows,indent=1)+'\n'
if a.output:a.output.write_text(text)
print(text)
