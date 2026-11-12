import json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from kokoro_onnx import Kokoro
import onnxruntime as ort
import numpy as np
OUT=Path('dist/orbiuno-2026-11-11-2200');OUT.mkdir(parents=True,exist_ok=True)
STORIES=[
('ECONOMÍA · COLOMBIA','DÓLAR CIERRA EN $3.295,68','El dólar cerró este miércoles en tres mil doscientos noventa y cinco pesos con sesenta y ocho centavos. Quedó ligeramente por debajo de la tasa representativa del día.','La República','https://www.larepublica.co/finanzas/precio-del-dolar-y-del-petroleo-hoy-11-de-noviembre-4522342'),
('INDUSTRIA · COLOMBIA','LUZ STELLA MURGAS DIRIGIRÁ LA ANDI','La Asociación Nacional de Empresarios eligió a Luz Stella Murgas como nueva presidenta. Sus retos incluyen competitividad, inversión y empleo formal.','ANDI · comunicado oficial','https://andi.com.co/Home/Noticia/18107-luz-stella-murgas-es-la-nueva-president'),
('TECNOLOGÍA · MUNDO','TSMC APRUEBA INVERSIONES EN IA','La fabricante de chips T S M C aprobó invertir hasta quinientos millones de dólares en OpenAI y otros quinientos millones en Anthropic.','Reuters','https://www.reuters.com/world/china/tsmc-invest-up-1-billion-anthropic-openai-2026-11-10/'),
('AMBIENTE · MUNDO','COP31: LLAMADO A ACELERAR ACCIÓN CLIMÁTICA','En la COP treinta y uno, en Turquía, líderes mundiales pidieron reducir emisiones y reforzar la cooperación frente al cambio climático.','Reuters','https://www.reuters.com/sustainability/cop/world-leaders-speak-cop31-climate-conference-2026-11-11/')
]

PHOTO_INFO=[
('US_Dollar_banknotes.jpg','Milad Mosapoor · dominio público'),
('Avenida_Chile_-_centro_comercial_Bogota.JPG','Felipe Restrepo Acosta · CC BY-SA 4.0'),
('Tsmc_factory_hsinchu.JPG','Arusanov · dominio público'),
('Expo2016_Tower_in_Antalya-Turkey.jpg','Ahzaryamed · CC BY-SA 4.0')
]
PHOTO_CACHE={}
def source_photo(index):
 if index in PHOTO_CACHE:return PHOTO_CACHE[index]
 from urllib.request import Request,urlopen
 from urllib.parse import quote
 from io import BytesIO
 name,credit=PHOTO_INFO[index]
 url='https://commons.wikimedia.org/wiki/Special:FilePath/'+quote(name,safe='')
 try:
  with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 (ORBIUNO editorial archival photograph)'}),timeout=12) as resp: raw=resp.read(4000000)
  photo=Image.open(BytesIO(raw)).convert('RGB')
  PHOTO_CACHE[index]=photo
  print('FOTO_ARCHIVO_OK',index,len(raw),flush=True)
  return photo
 except Exception as e:
  print('FOTO_ARCHIVO_NO_DISPONIBLE',index,type(e).__name__,flush=True)
  PHOTO_CACHE[index]=None
  return None
W,H=720,1280
def font(n,b=True):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if b else '')+'.ttf',n)
def fit(d,s,f,w):
 out=[];line=''
 for word in s.split():
  trial=(line+' '+word).strip()
  if d.textbbox((0,0),trial,font=f)[2]<=w:line=trial
  else:
   if line:out.append(line)
   line=word
 if line:out.append(line)
 return out
def block(d,s,x,y,f,color,w):
 for line in fit(d,s,f,w):
  d.text((x,y),line,font=f,fill=color)
  y+=f.size+12
def slide(i,kind,story,path):
 im=Image.new('RGB',(W,H),'#08182E');d=ImageDraw.Draw(im)
 d.rectangle((0,0,W,15),fill='#67e6db')
 d.rounded_rectangle((35,62,685,208),radius=20,fill='#173659')
 d.text((58,78),'ORBIUNO',font=font(60),fill='white')
 d.text((58,158),'MIÉRCOLES 11 NOV 2026 · 22:00',font=font(19,False),fill='#67e6db')
 if kind=='intro':
  block(d,'EDICIÓN DE LAS 10:00 P. M.',55,405,font(55),'white',600)
  block(d,'Colombia · Economía · Tecnología · Clima',55,750,font(30,False),'#c8d8ed',600)
 elif kind=='outro':
  block(d,'MÁS INFORMACIÓN',55,400,font(55),'white',600)
  block(d,'Las fuentes originales están en nuestra web. Enlace en la bio.',55,670,font(33,False),'#c8d8ed',600)
 else:
  tag,title,voice,source,url=story
  d.text((50,275),tag,font=font(28),fill='#67e6db')
  block(d,title,50,375,font(48),'white',625)
  from PIL import ImageOps
  pic=source_photo(i-1)
  if pic is not None:
   im.paste(ImageOps.fit(pic,(628,310),method=Image.Resampling.LANCZOS),(46,650))
   d=ImageDraw.Draw(im)
   d.rectangle((46,932,674,962),fill='#08182E')
   d.text((53,938),'ARCHIVO REFERENCIAL · '+PHOTO_INFO[i-1][1][:48],font=font(14,False),fill='white')
  else:
   d.rounded_rectangle((46,635,674,958),radius=25,fill='#173659')
   d.text((69,705),'NOTICIA VERIFICADA',font=font(27),fill='#67e6db')
   block(d,title,69,774,font(28),'#fff',535)
  d.text((55,1010),'FUENTE: '+source,font=font(23,False),fill='white')
  d.text((55,1054),'11 NOVIEMBRE 2026',font=font(22,False),fill='#67e6db')
 d.rectangle((0,1170,W,H),fill='#173659')
 d.text((45,1190),'@resumen.noticias',font=font(25),fill='white')
 d.text((45,1230),'colombia-al-dia.pages.dev',font=font(21,False),fill='#67e6db')
 im.save(path)
def run(a,**kwargs):subprocess.run(a,check=True,stdout=subprocess.DEVNULL,**kwargs)
sess=ort.SessionOptions();sess.intra_op_num_threads=2;sess.inter_op_num_threads=1
k=Kokoro.from_session(ort.InferenceSession('/tmp/kokoro-v1.0.onnx',sess_options=sess,providers=['CPUExecutionProvider']),'/tmp/voices-v1.0.bin')
scenes=[('intro',None,'ORBIUNO. Resumen de las diez de la noche del once de noviembre. Cuatro noticias verificadas.')]+[('news',s,s[2]+' Fuente: '+s[3]+'.') for s in STORIES]+[('outro',None,'Más noticias y sus fuentes en Colombia al día. Encuentra nuestra web desde el perfil de ORBIUNO.')]
with tempfile.TemporaryDirectory() as td:
 td=Path(td);parts=[]
 for i,(kind,story,voice) in enumerate(scenes):
  png=td/f'{i}.png';wav=td/f'{i}.wav';mp4=td/f'{i}.mp4'
  slide(i,kind,story,png)
  sound,sr=k.create(voice,'ef_dora',speed=1.25,lang='es',sentence_pause=.12,clause_pause=.05)
  run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(sr),'-ac','1','-i','pipe:0','-ar','48000','-ac','2',str(wav)],input=np.asarray(sound,dtype=np.float32).tobytes())
  run(['ffmpeg','-v','error','-y','-loop','1','-framerate','24','-i',str(png),'-i',str(wav),'-shortest','-vf','format=yuv420p','-c:v','libx264','-preset','ultrafast','-crf','27','-r','24','-c:a','aac','-b:a','128k',str(mp4)])
  parts.append(mp4)
 txt=td/'concat.txt';txt.write_text(''.join("file '"+str(p)+"'\\n" for p in parts).replace('\\n','\n'))
 video=OUT/'ORBIUNO_2026-11-11_2200.mp4'
 run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(txt),'-c','copy','-movflags','+faststart',str(video)])
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_type,width,height','-of','json',str(video)],text=True))
assert 35<=float(probe['format']['duration'])<=100 and any(s.get('codec_type')=='audio' for s in probe['streams'])
(OUT/'fuentes.json').write_text(json.dumps({'fecha':'2026-11-11','franja':'22:00','publicado':False,'voz':'ef_dora','velocidad':1.25,'fotos_licencia':PHOTO_INFO,'stories':[{'title':s[1],'source':s[3],'url':s[4]} for s in STORIES],'probe':probe},ensure_ascii=False,indent=2))
(OUT/'instagram_caption.txt').write_text('📰 ORBIUNO | Resumen de las 10:00 p. m. · 11 de noviembre de 2026\n\n' + '\n'.join('• '+s[1] for s in STORIES) + '\n\nFuentes: La República, ANDI y Reuters. Imágenes de archivo referenciales con crédito visible.\nMás información: colombia-al-dia.pages.dev\n#ORBIUNO #Noticias #Colombia #Economía #Tecnología',encoding='utf-8')
print('VIDEO_LISTO',video,probe['format']['duration'],flush=True)
