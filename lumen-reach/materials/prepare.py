# SPDX-License-Identifier: MIT
"""Original generated masters -> periodic PBR tiles, trim atlas, original UI."""
from pathlib import Path
import sys,json,hashlib,math,random
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).parent;ROOT=HERE.parents[1];OUT=HERE/'tiles';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'switchyard'));from lettering import GLYPHS
PARAMS={'concrete':(2,.78,0,.45),'metal':(1,.43,.65,.18),'paving':(2,.29,0,.4),'canvas':(1,.90,0,.25),'wood':(1,.56,0,.35),'frost':(1,.65,.45,.3),'glass':(2,.18,.2,.05),'strips':(1,.3,.3,.12),'grating':(1,.48,.55,.3),'snow':(2,.88,0,.25),'rock':(4,.84,0,.7),'frost-metal-v3':(2,.48,.55,.18),'rime-crust-v3':(1,.88,0,.35),'condensation-v3':(2,.26,.18,.14)}

def periodic(a):
 h,w,_=a.shape;v=np.zeros_like(a);v[0]+=a[-1]-a[0];v[-1]+=a[0]-a[-1];v[:,0]+=a[:,-1]-a[:,0];v[:,-1]+=a[:,0]-a[:,-1]
 yy,xx=np.mgrid[:h,:w];den=2*np.cos(2*np.pi*xx/w)+2*np.cos(2*np.pi*yy/h)-4;den[0,0]=1
 smooth=np.fft.ifft2(np.fft.fft2(v,axes=(0,1))/den[:,:,None],axes=(0,1)).real;smooth-=smooth.mean(axis=(0,1));a=np.clip(a-smooth,0,1)
 for i in range(12):
  t=.5*(1-i/12)**2;l=a[:,i].copy();r=a[:,-1-i].copy();a[:,i]=(1-t)*l+t*r;a[:,-1-i]=(1-t)*r+t*l
  l=a[i].copy();r=a[-1-i].copy();a[i]=(1-t)*l+t*r;a[-1-i]=(1-t)*r+t*l
 return a

TILE_RESOLUTION=640
rows=[];swatches=[]
for name,(meters,rough,metal,strength) in PARAMS.items():
 path=HERE/'source'/f'{name}.png';a=np.array(Image.open(path).convert('RGB').resize((TILE_RESOLUTION,TILE_RESOLUTION),Image.Resampling.LANCZOS),dtype=np.float32)/255
 before=float(np.mean(abs(a[:,0]-a[:,-1]))+np.mean(abs(a[0]-a[-1])));a=periodic(a)
 if name=='wood':a*=.72
 rgb=np.round(a*255).astype('uint8');rgb[:,-1]=rgb[:,0];rgb[-1]=rgb[0];Image.fromarray(rgb).save(OUT/f'{name}-albedo.png',optimize=True)
 gray=a@np.array([.2126,.7152,.0722]);dx=(np.roll(gray,-1,axis=1)-np.roll(gray,1,axis=1))*strength;dy=(np.roll(gray,-1,axis=0)-np.roll(gray,1,axis=0))*strength
 norm=np.stack([-dx,dy,np.ones_like(dx)],axis=-1);norm/=np.linalg.norm(norm,axis=-1)[:,:,None];norm=np.round((norm*.5+.5)*255).astype('uint8');norm[:,-1]=norm[:,0];norm[-1]=norm[0];Image.fromarray(norm).save(OUT/f'{name}-normal.png',optimize=True)
 orm=np.ones_like(a);orm[:,:,1]=np.clip(rough+(gray-gray.mean())*.12,.08,.98);orm[:,:,2]=metal;orm=np.round(orm*255).astype('uint8');orm[:,-1]=orm[:,0];orm[-1]=orm[0];Image.fromarray(orm).save(OUT/f'{name}-orm.png',optimize=True)
 Image.fromarray(np.roll(np.roll(rgb,TILE_RESOLUTION//2,axis=0),TILE_RESOLUTION//2,axis=1)).save(OUT/f'{name}-offset.png',optimize=True)
 im=Image.fromarray(rgb).resize((256,256));tile=Image.new('RGB',(512,512))
 for x in [0,256]:
  for y in [0,256]:tile.paste(im,(x,y))
 swatches.append((name,tile));rows.append({'name':name,'masterSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'tileMeters':meters,'texelDensityPxPerMeter':TILE_RESOLUTION/meters,'edgeMeanErrorBefore':before,'edgeMaxErrorAfter':int(np.max(abs(rgb[:,0].astype(int)-rgb[:,-1].astype(int)))),'normalStrength':strength})
trim=Image.new('RGB',(1024,1024));regions=[]
for i,name in enumerate(['concrete','metal','canvas','wood','frost','glass','strips','grating']):
 src=Image.open(OUT/f'{name}-albedo.png').resize((1024,1024),Image.Resampling.LANCZOS);band=src.crop((0,0,1024,112));trim.paste(band,(0,i*128+8));trim.paste(band.crop((0,0,1024,1)).resize((1024,8)),(0,i*128));trim.paste(band.crop((0,111,1024,112)).resize((1024,8)),(0,i*128+120));regions.append({'id':name,'uvRect':[0,(i*128+8)/1024,1,(i*128+120)/1024],'gutterPixels':8})
trim.save(OUT/'reach-trim-albedo.png',optimize=True);(OUT/'reach-trim.json').write_text(json.dumps(regions,indent=2)+'\n')
contact=Image.new('RGB',(5*512,math.ceil(len(swatches)/5)*544),(14,23,30));d=ImageDraw.Draw(contact)
for i,(name,im) in enumerate(swatches):x=i%5*512;y=i//5*544;contact.paste(im,(x,y));d.text((x+12,y+519),name,fill='white')
contact.save(OUT/'repeat-contact-sheet.png',optimize=True);(OUT/'texture-report.json').write_text(json.dumps(rows,indent=2)+'\n')

# Own geometric alphabet and Reach mark; no font files or borrowed UI graphics.
def text(d,xy,s,color=(200,218,220),scale=2):
 x,y=xy
 for ch in s.upper():
  if ch!=' ':
   for row,bits in enumerate(GLYPHS.get(ch,GLYPHS['-'])):
    for col,b in enumerate(bits):
     if b=='1':d.rectangle((x+col*scale,y+row*scale,x+(col+1)*scale-1,y+(row+1)*scale-1),fill=color)
  x+=scale*6

def mark(d,x,y,color):
 for i in range(3):d.rectangle((x+7*i,y-9*i,x+34,y-9*i+3),fill=color)
 d.rectangle((x+32,y-24,x+36,y+4),fill=color)

def network(d,cx,cy,r,color):
 d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=color,width=2)
 for t in [.25,.5,.78]:d.ellipse((cx-r*t,cy-r,cx+r*t,cy+r),outline=color,width=1);d.ellipse((cx-r,cy-r*t,cx+r,cy+r*t),outline=color,width=1)
 rng=random.Random(240)
 points=[]
 for i in range(30):
  a=rng.random()*math.tau;rr=r*math.sqrt(rng.random());points.append((cx+math.cos(a)*rr,cy+math.sin(a)*rr))
 for i,p in enumerate(points):
  q=points[(i+7)%len(points)];d.line([p,q],fill=tuple(int(c*.6) for c in color),width=1);d.ellipse((p[0]-3,p[1]-3,p[0]+3,p[1]+3),fill=(223,187,110))

def graph(d,x,y,w,h,color):
 for i in range(5):d.line((x,y+i*h/4,x+w,y+i*h/4),fill=(27,45,58),width=1)
 rng=random.Random(x+y);pts=[]
 for i in range(70):pts.append((x+i*w/69,y+h*.7-rng.random()*h*.4-math.sin(i*.38)*h*.12))
 d.line(pts,fill=color,width=2)

NAMES=['sun-court','array-hall','rime-vault','signal-rise'];TITLES=['SUN COURT','ARRAY HALL','RIME VAULT','SIGNAL RISE']
for area,title in zip(NAMES,TITLES):
 accent=(206,139,77) if area!='rime-vault' else (236,81,37);blue=(190,111,56) if area=='rime-vault' else (96,156,182)
 for style in ['workspace','instrument','banner','map']:
  w,h=(2048,1024) if style=='workspace' else (512,1024) if style=='banner' else (1024,576)
  im=Image.new('RGB',(w,h),(9,17,25));d=ImageDraw.Draw(im);d.rectangle((10,10,w-11,h-11),outline=(65,86,102),width=2);mark(d,29,55,accent);text(d,(85,30),title,accent,4 if w>1024 else 2);text(d,(85,70),'HYPRUNE / WORKSPACE HOME' if style=='workspace' else 'HYPRUNE / INSTRUMENT',blue,2);d.line((24,103,w-24,103),fill=accent,width=2)
  if style=='banner':
   for i,label in enumerate(['ROUTES','SUN COURT','ARRAY HALL','RIME VAULT','SIGNAL RISE']):
    y=148+i*158;d.rectangle((35,y,477,y+133),outline=(52,74,88));network(d,108,y+64,39,blue);text(d,(174,y+45),label,accent,2)
   text(d,(44,965),'LUMEN REACH',blue,3)
  elif style=='map':
   menus=['OVERVIEW','SYSTEMS','MAP','DIAGNOSTICS','ARCHIVES','RESEARCH','MESSAGES']
   for i,label in enumerate(menus):
    y=137+i*43
    if i==2:d.rectangle((25,y-6,236,y+28),fill=(93,35,27))
    text(d,(39,y),label,accent if i==2 else blue,2)
   # Original terrain contour wire map.
   for k in range(18):
    pts=[]
    for i in range(40):
     x=267+i*13;y=235+k*12+math.sin(i*.2+k*.21)*45-abs(math.sin(i*.1))*100;pts.append((x,y))
    d.line(pts,fill=(58+k*3,102+k*2,126+k*2),width=1)
   for i,label in enumerate(['POWER','COOLANT','LINK HEALTH']):text(d,(800,190+i*90),label,accent,2);graph(d,800,216+i*90,175,48,blue)
  else:
   margin=30;left=int(w*.31);right=int(w*.69);top=138
   d.rectangle((margin,top,left-17,h-135),outline=(50,73,87));text(d,(margin+16,top+18),'TASKS / LOCAL',accent,2)
   labels=['ENVIRONMENTS','BUILD QUEUE','CONNECTIONS','ARCHIVES','ROUTES','POWER','COOLANT','LINK HEALTH']
   rng=random.Random(901)
   for i in range(30 if w>1024 else 18):
    y=top+56+i*(22 if w>1024 else 13);text(d,(margin+16,y),f'{i+1:02d} '+labels[i%8],(111,149,166),2 if w>1024 else 1);d.line((left-86,y+4,left-27,y+4),fill=accent if i%3==0 else blue,width=2)
   network(d,(left+right)//2,int(h*.39),int(w*.145),blue)
   for i,label in enumerate(['ENVIRONMENTS','CONNECTIONS','WORKSPACE SLOT']):
    y=top+i*int(h*.17);text(d,(right+26,y),label,accent,2);graph(d,right+26,y+34,w-right-55,int(h*.10),blue)
   graph(d,left+12,int(h*.72),right-left-27,int(h*.14),accent)
   for i,label in enumerate(['UPPER CASCADE','WATERSHED SPIRE','LUMEN REACH']):
    x=margin+i*(w-2*margin)//3;y=h-116;d.rectangle((x,y,x+(w-2*margin)//3-12,h-34),outline=(55,80,95));text(d,(x+12,y+14),label,blue,2);d.line([(x+15,h-43),(x+43,h-74),(x+65,h-55),(x+97,h-94),(x+140,h-42)],fill=accent,width=2)
  if style=='workspace':im=im.resize((1536,768),Image.Resampling.LANCZOS)
  im.save(OUT/f'ui-{area}-{style}.png',optimize=True)
print('Prepared fourteen seam-healed original PBR sets, trim sheet and sixteen original screen layouts')

# Original alpha master retained; bounded GPU derivative uses clamp sampling.
Image.open(HERE/'source/steam.png').convert('RGBA').resize((512,768),Image.Resampling.LANCZOS).save(OUT/'steam-albedo.png',optimize=True)

# Fade the top sky into the exact shared zenith paint; no stretched star row.
night=np.asarray(Image.open(HERE/'source/night-vista.png').convert('RGB').resize((1600,538),Image.Resampling.LANCZOS),dtype=np.float32)
zenith=np.array([2,28,61],dtype=np.float32)
h=night.shape[0]
for y in range(int(h*.22)):
 t=max(0,1-y/(h*.22));t=t*t*(3-2*t);night[y]=night[y]*(1-t)+zenith*t
Image.fromarray(np.round(night).astype('uint8')).save(OUT/'night-vista-albedo.png',optimize=True)
