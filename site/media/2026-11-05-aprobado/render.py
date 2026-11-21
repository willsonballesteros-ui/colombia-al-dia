import json,math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).parent; W,H,FPS=720,1280,24
font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',n)
heads=['Nutresa cerró la\ncompra de Presto','Davivienda recibe\nclientes de Davibank','Garantía para financiar\nel Metro de Bogotá','Dólar promedio:\n$3.228,19','Cooperación con Corea\nen inteligencia artificial','Santiago Peña presenta\nsu renuncia en Paraguay','Israel: encargo para\nformar Gobierno','Caso Villavicencio:\nSerrano, llamado a juicio','Ucrania pide equipos\npara reparar su red','Europa y Latinoamérica:\nreforzar la cooperación']
sources=['La República']*3+['Noticias RCN','Minciencias']+['EFE']*4+['EuroEFE']
icons={}
for name,host in [('La República','www.larepublica.co'),('Noticias RCN','www.noticiasrcn.com'),('EFE','efe.com'),('EuroEFE','efe.com')]:
 im=Image.open('media/source-icons/'+host+'.png').convert('RGBA');im.thumbnail((48,48));icons[name]=im
segments=json.loads((P/'transcripcion.json').read_text());words=[w for s in segments for w in s['words']]
duration=52.368
# Actual speech recognition boundaries, reviewed against the approved script.
def at(term,default):
 for w in words:
  if term.lower() in w['word'].lower():return w['start']
 return default
starts=[2.94,6.18,9.24,11.94,18.08,21.62,25.5,29.1,33.76,38.22]
cta=at('termina',44)
# Captions use original ASR timing; preserve the approved audio unchanged.
caps=[];group=[]
for w in words:
 if group and (len(group)>=6 or len(' '.join(x['word'].strip() for x in group)+' '+w['word'].strip())>38):
  caps.append({'start':group[0]['start'],'end':group[-1]['end'],'text':' '.join(x['word'].strip() for x in group)});group=[]
 group.append(w)
if group:caps.append({'start':group[0]['start'],'end':group[-1]['end'],'text':' '.join(x['word'].strip() for x in group)})
for c in caps:
 for a,b in [('Orbiuno','ORBIUNO'),('Orbuno','ORBIUNO'),('Minsiencias','Minciencias'),('Davibanc','Davibank')]:c['text']=c['text'].replace(a,b)
def wrap(text,ft,width):
 d=ImageDraw.Draw(Image.new('RGB',(1,1)));out=[];line=''
 for w in text.split():
  n=(line+' '+w).strip()
  if d.textbbox((0,0),n,font=ft)[2]>width and line:out.append(line);line=w
  else:line=n
 if line:out.append(line)
 return out

def frame(t):
 page=0 if t<starts[5] else 1;bg='#24182F' if page==0 else '#103A38';accent='#FFC46B' if page==0 else '#7CF0C5'
 im=Image.new('RGB',(W,H),bg);d=ImageDraw.Draw(im)
 d.rectangle((48,176,606,181),fill=accent);d.text((56,195),'ORBIUNO',font=font(36),fill=accent)
 d.text((56,243),'5 NOV 2026 · EDICIÓN EXTRA',font=font(17),fill='white')
 d.text((56,273),f'COLOMBIA Y MUNDO · {page+1}/2',font=font(16),fill=accent)
 active=max([i for i,s in enumerate(starts) if t>=s],default=-1)
 for j in range(5):
  i=page*5+j;y=315+j*103;on=active==i and t<cta
  d.rounded_rectangle((48,y,606,y+95),radius=12,fill=('#67432D' if page==0 else '#17614F') if on else ('#34233F' if page==0 else '#174743'),outline=accent if on else None,width=3)
  d.text((58,y+9),f'{i+1:02}',font=font(15),fill=accent)
  icon=icons.get(sources[i])
  if icon:
   d.rounded_rectangle((84,y+24,138,y+78),radius=8,fill='white');im.paste(icon,(int(111-icon.width/2),int(y+51-icon.height/2)),icon);d=ImageDraw.Draw(im)
  else:d.text((87,y+39),'CO',font=font(18),fill=accent)
  d.multiline_text((152,y+7),heads[i],font=font(27),fill='white',spacing=0)
  d.text((152,y+70),sources[i],font=font(15),fill=accent)
 cap=next((c for c in caps if c['start']<=t<c['end']+.04),None)
 if cap:
  lines=wrap(cap['text'],font(29),520)
  for n,l in enumerate(lines):d.text((56,854+n*37),l,font=font(29),fill='white')
 d.text((56,960),'ESCUCHA CADA NOTICIA COMPLETA',font=font(20),fill=accent)
 d.text((56,993),'@resumen.noticias → enlace del perfil',font=font(20),fill='white')
 d.text((56,1040),'Voz sintética · Redacción ORBIUNO',font=font(14),fill='#C7C9CB')
 return im
(P/'timeline.json').write_text(json.dumps({'duration':duration,'story_starts':starts,'captions':caps,'voice':'ef_dora','native_speed':1.25,'audio':'ORBIUNO_Voz_Natural_1_25x.mp3'},ensure_ascii=False,indent=2))
def stamp(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
(P/'subtitulos.srt').write_text('\n\n'.join(f"{i+1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}" for i,c in enumerate(caps)))
qa=Image.new('RGB',(720,1280))
for i,t in enumerate([5,18,30,45]):
 im=frame(t);im.thumbnail((360,640));qa.paste(im,((i%2)*360,(i//2)*640))
qa.save(P/'qa.jpg')
cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size','720x1280','-framerate','24','-i','pipe:0','-i','ORBIUNO_Voz_Natural_1_25x.mp3','-map','0:v','-map','1:a','-c:v','libx264','-preset','fast','-crf','27','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart','-shortest',str(P/'ORBIUNO_Aprobado_1_25x.mp4')]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for f in range(math.ceil(duration*FPS)):p.stdin.write(frame(f/FPS).tobytes())
p.stdin.close();assert p.wait()==0
print('Render completo')
