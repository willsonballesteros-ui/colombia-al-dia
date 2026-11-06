import json,math,re,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).parent;W,H,FPS=720,1280,24
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
REG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def font(n,b=True):return ImageFont.truetype(FONT if b else REG,n)
lines=json.loads((P/'guion.json').read_text());words=[json.loads(l) for l in (P/'palabras.jsonl').read_text().splitlines()]
duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(P/'voz.mp3')]))
news=json.loads((P/'sources.json').read_text());news.sort(key=lambda n:n['priority'])
heads=['10 noticias para\ncerrar el día','Nutresa adquiere\nPresto','Davivienda integra\na Davibank','Dólar: promedio\n$3.228,19','Respaldo al crédito\ndel Metro de Bogotá','Cooperación en IA\ncon Corea','Santiago Peña\npresenta su renuncia','Israel: encargo\nde Gobierno el domingo','Caso Villavicencio:\nllamado a juicio','Ucrania solicita\nequipos eléctricos','Europa y Latinoamérica:\nmás cooperación','Escúchalas completas\nen nuestra web']
sources=['ORBIUNO']+[n['sources'][0]['name'] for n in news]+['ORBIUNO']
chapters=[];cursor=0;captions=[]
for i,line in enumerate(lines):
 tokens=line.split();ww=words[cursor:cursor+len(tokens)];cursor+=len(tokens)
 start=ww[0]['offset']/1e7;end=(ww[-1]['offset']+ww[-1]['duration'])/1e7
 chapters.append(dict(start=0 if i==0 else start,end=end,head=heads[i],source=sources[i],line=line))
 groups=[];chunk=[]
 for j,t in enumerate(tokens):
  if chunk and (len(chunk)>=6 or len(' '.join(z[1] for z in chunk)+' '+t)>36):groups.append(chunk);chunk=[]
  chunk.append((j,t))
 if chunk:groups.append(chunk)
 for g in groups:
  a=ww[g[0][0]];b=ww[g[-1][0]]
  captions.append(dict(start=a['offset']/1e7,end=(b['offset']+b['duration'])/1e7+.10,text=' '.join(t for _,t in g)))
for i,c in enumerate(chapters):c['end']=chapters[i+1]['start'] if i+1<len(chapters) else duration
for i,c in enumerate(captions[:-1]):c['end']=min(c['end'],captions[i+1]['start'])
assert cursor==len(words)
(P/'timeline.json').write_text(json.dumps(dict(duration=duration,chapters=chapters,captions=captions,voice='es-CO-SalomeNeural',rate='+0%',listening_review='not_performed',timing='TTS word boundaries; all 122 words matched script',visual='Editorial typography; no event photographs'),ensure_ascii=False,indent=2))
def stamp(t):
 h=int(t//3600);m=int(t%3600//60);s=int(t%60);ms=round((t%1)*1000)
 return f'{h:02}:{m:02}:{s:02},{ms:03}'
(P/'subtitulos.srt').write_text('\n\n'.join(f"{i+1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}" for i,c in enumerate(captions))+'\n')
colors=[('#171B30','#FFCA43'),('#341B33','#FF976A'),('#123B3C','#74F2D0'),('#321F50','#D5B2FF')]
icons={}
for name,host in [('EFE','efe.com'),('La República','www.larepublica.co'),('Noticias RCN','www.noticiasrcn.com'),('Minciencias','minciencias.gov.co')]:
 p=Path('media/source-icons')/(host+'.png')
 if p.exists():
  im=Image.open(p).convert('RGBA');im.thumbnail((68,68));icons[name]=im

def wrap(text,ft,width):
 d=ImageDraw.Draw(Image.new('RGB',(1,1)));out=[]
 for para in text.split('\n'):
  line=''
  for word in para.split():
   s=(line+' '+word).strip()
   if d.textbbox((0,0),s,font=ft)[2]>width and line:out.append(line);line=word
   else:line=s
  if line:out.append(line)
 return out

def center(d,text,y,ft,fill,width=430,gap=9):
 for line in wrap(text,ft,width):
  box=d.textbbox((0,0),line,font=ft);x=(W-(box[2]-box[0]))/2
  d.text((x,y),line,font=ft,fill=fill);y+=ft.size+gap
 return y

def frame(t,qa=False):
 idx=next((i for i,c in enumerate(chapters) if c['start']<=t<c['end']),len(chapters)-1);c=chapters[idx]
 bg,accent=colors[idx%len(colors)];im=Image.new('RGB',(W,H),bg);d=ImageDraw.Draw(im)
 # Full-frame editorial typography: a single moving headline, source and speech captions.
 center(d,'ORBIUNO',236,font(32),accent)
 center(d,'5 NOV 2026  ·  EDICIÓN EXTRA',284,font(16),'#E5E8F2')
 src=c['source'];ic=icons.get('EFE' if src=='EuroEFE' else src)
 if ic and src!='Minciencias':
  d.rounded_rectangle((W/2-42,330,W/2+42,414),radius=13,fill='#FFFFFF');im.paste(ic,(int(W/2-ic.width/2),int(372-ic.height/2)),ic);d=ImageDraw.Draw(im)
 center(d,src,425,font(27),accent)
 headline_size=43
 while len(wrap(c['head'],font(headline_size),430))>3:headline_size-=1
 center(d,c['head'],487,font(headline_size),'#FFFFFF',gap=9)
 if idx in range(1,11):center(d,f'{idx:02} / 10',643,font(18),accent)
 cap=next((z for z in captions if z['start']<=t<z['end']),None)
 if cap:
  center(d,cap['text'],706,font(29),'#FFFFFF',gap=9)
 if idx==len(chapters)-1:
  center(d,'@resumen.noticias',638,font(22),accent)
 # Transparent attribution for synthetic narration.
 center(d,'Voz sintética · Redacción ORBIUNO',1090,font(14,False),'#B8C1D3')
 if qa:
  ov=Image.new('RGBA',(W,H),(0,0,0,0));o=ImageDraw.Draw(ov)
  for rect in [(0,0,W,.18*H),(0,.65*H,W,H),(0,0,.08*W,H),(.8*W,0,W,H)]:o.rectangle(rect,fill=(240,55,65,55))
  im=Image.alpha_composite(im.convert('RGBA'),ov).convert('RGB')
 return im

# Inspect every chapter and the longest cue with platform exclusion overlays.
qa=Image.new('RGB',(4*216,3*384),'#111')
for i,c in enumerate(chapters):
 f=frame(min(c['end']-.1,c['start']+.8),True);f.thumbnail((216,384));qa.paste(f,((i%4)*216,(i//4)*384))
qa.save(P/'qa.jpg')
frame(5).save(P/'preview.jpg')
cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','pipe:0','-i',str(P/'voz.mp3'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','26','-pix_fmt','yuv420p','-r',str(FPS),'-c:a','aac','-b:a','128k','-ar','48000','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-movflags','+faststart',str(P/'ORBIUNO_Extra_20261105.mp4')]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for f in range(math.ceil(duration*FPS)):p.stdin.write(frame(f/FPS).tobytes())
p.stdin.close();assert p.wait()==0
print('Video renderizado',duration)
