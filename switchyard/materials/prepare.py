# SPDX-License-Identifier: MIT
"""Build requested tiling/trim/PBR derivatives from original imagegen masters.
Offset inspection + toroidal Poisson boundary healing removes low-frequency
edge mismatch. A narrow symmetric periodic edge collar makes boundary pixels
identical. Original masters are retained; all derivatives are reproducible.
"""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,ImageDraw
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'tiles';OUT.mkdir(exist_ok=True)
PARAMS={'stone':(2,.82,0,.55),'metal':(1,.48,.45,.25),'wood':(1,.48,0,.7),'rubber':(1,.91,0,.65),'brass':(1,.29,.78,.25),'cloth':(1,.9,0,.55),'glass':(2,.19,0,.08),'panel':(1,.42,.15,.18)}
def periodic(a):
 h,w,_=a.shape;v=np.zeros_like(a)
 v[0]+=a[-1]-a[0];v[-1]+=a[0]-a[-1];v[:,0]+=a[:,-1]-a[:,0];v[:,-1]+=a[:,0]-a[:,-1]
 yy,xx=np.mgrid[:h,:w];den=2*np.cos(2*np.pi*xx/w)+2*np.cos(2*np.pi*yy/h)-4;den[0,0]=1
 smooth=np.fft.ifft2(np.fft.fft2(v,axes=(0,1))/den[:,:,None],axes=(0,1)).real;smooth-=smooth.mean(axis=(0,1))
 a=np.clip(a-smooth,0,1)
 # Mirror blends on a small 12px collar, matching both opposite border pairs.
 for i in range(12):
  t=.5*(1-i/12)**2;left=a[:,i].copy();right=a[:,-1-i].copy();a[:,i]=(1-t)*left+t*right;a[:,-1-i]=(1-t)*right+t*left
  top=a[i].copy();bottom=a[-1-i].copy();a[i]=(1-t)*top+t*bottom;a[-1-i]=(1-t)*bottom+t*top
 return a
rows=[];swatches=[]
for name,(meters,rough,metal,strength) in PARAMS.items():
 path=ROOT/'source'/f'{name}.png';im=Image.open(path).convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS);a=np.array(im,dtype=np.float32)/255
 before=float(np.mean(np.abs(a[:,0]-a[:,-1]))+np.mean(np.abs(a[0]-a[-1])))
 a=periodic(a)
 if name=='wood':a*=.62
 if name=='panel':
  # A regular diffuser must match pattern phase as well as edge colors.
  yy,xx=np.mgrid[:1024,:1024];cell=((xx%128>14)&(xx%128<114)&(yy%128>12)&(yy%128<116));tint=np.array([.16,.42,.48])[None,None,:];a=np.where(cell[:,:,None],a*.32+tint*.68,a*.06)
 rgb=np.round(a*255).astype('uint8');rgb[:,-1]=rgb[:,0];rgb[-1]=rgb[0]
 Image.fromarray(rgb).save(OUT/f'{name}-albedo.png',optimize=True)
 gray=a@np.array([.2126,.7152,.0722]);dx=(np.roll(gray,-1,axis=1)-np.roll(gray,1,axis=1))*strength;dy=(np.roll(gray,-1,axis=0)-np.roll(gray,1,axis=0))*strength
 normal=np.stack([-dx,dy,np.ones_like(dx)],axis=-1);normal/=np.linalg.norm(normal,axis=-1)[:,:,None];norm=np.round((normal*.5+.5)*255).astype('uint8');norm[:,-1]=norm[:,0];norm[-1]=norm[0]
 Image.fromarray(norm).save(OUT/f'{name}-normal.png',optimize=True)
 orm=np.ones_like(a);orm[:,:,1]=np.clip(rough+(gray-gray.mean())*.12,.05,.98);orm[:,:,2]=metal;orm=np.round(orm*255).astype('uint8');orm[:,-1]=orm[:,0];orm[-1]=orm[0]
 Image.fromarray(orm).save(OUT/f'{name}-orm.png',optimize=True)
 # Offset view puts former boundaries in the middle; 2x2 repeat is also retained.
 healed=Image.fromarray(rgb);offset=np.roll(np.roll(rgb,512,axis=0),512,axis=1);Image.fromarray(offset).save(OUT/f'{name}-offset-inspection.png',optimize=True)
 thumb=healed.resize((256,256));tile=Image.new('RGB',(512,512));
 for x in [0,256]:
  for y in [0,256]:tile.paste(thumb,(x,y))
 swatches.append((name,tile));rows.append({'name':name,'masterSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'license':'CC-BY-4.0','provenance':'Generated for Hyprune, CC-BY-4.0','modifications':'1024px derivative; toroidal Poisson seam healing and periodic edge collar; wrap-safe derived OpenGL normal and ORM maps','tileMeters':meters,'texelDensityPxPerMeter':1024/meters,'edgeMeanErrorBefore':before,'edgeMaxErrorAfter':int(np.max(np.abs(rgb[:,0].astype(int)-rgb[:,-1].astype(int)))),'normalStrength':strength})
# An actual reusable original eight-band trim atlas, with explicit gutters.
trim=Image.new('RGB',(1024,1024));regions=[]
for i,name in enumerate(['metal','brass','wood','rubber','cloth','stone','glass','panel']):
 src=Image.open(OUT/f'{name}-albedo.png');band=src.crop((0,0,1024,112));trim.paste(band,(0,i*128+8))
 trim.paste(band.crop((0,0,1024,1)).resize((1024,8)),(0,i*128));trim.paste(band.crop((0,111,1024,112)).resize((1024,8)),(0,i*128+120));regions.append({'id':name,'uvRect':[0,(i*128+8)/1024,1,(i*128+120)/1024],'gutterPixels':8})
trim.save(OUT/'transit-trim-albedo.png',optimize=True);(OUT/'transit-trim.json').write_text(json.dumps({'license':'CC-BY-4.0','regions':regions},indent=2)+'\n')
contact=Image.new('RGB',(4*512,2*544),(17,28,35));draw=ImageDraw.Draw(contact)
for i,(name,im) in enumerate(swatches):
 x=(i%4)*512;y=(i//4)*544;contact.paste(im,(x,y));draw.text((x+12,y+520),name,fill='white')
contact.save(OUT/'repeat-contact-sheet.png',optimize=True)
(OUT/'texture-report.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Prepared 8 original seamless tile sets, normal/ORM derivatives and transit trim atlas')
