import json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from kokoro_onnx import Kokoro
import onnxruntime as ort
import numpy as np
OUT=Path('dist/orbiuno-2026-11-11');OUT.mkdir(parents=True,exist_ok=True)
STORIES=[
('ECONOMÍA','DÓLAR OFICIAL: $3.297,07','El dólar tiene una tasa representativa del mercado de tres mil doscientos noventa y siete pesos con siete centavos este miércoles. La apertura estuvo cerca de tres mil doscientos noventa y dos pesos.','El Espectador','https://www.elespectador.com/economia/dolar-hoy-en-colombia-asi-arranco-el-precio-de-la-divisa-este-miercoles-11-de-noviembre/'),
('FINANZAS PÚBLICAS','GOBIERNO DEFIENDE AJUSTE FISCAL','El vicepresidente José Manuel Restrepo defendió el ajuste fiscal y alertó por el peso de la deuda. Según sus cifras, uno de cada tres pesos del recaudo se destina a obligaciones financieras.','La República','https://www.larepublica.co/economia/gobierno-defendio-ajuste-fiscal-y-advirtio-sobre-el-peso-de-los-intereses-de-la-deuda-4522524'),
('AMBIENTE','IDEAM PREVÉ LLUVIAS EN CINCO REGIONES','El Ideam prevé lluvias de diferente intensidad en cinco regiones del país durante este miércoles. Para Bogotá pronostica tiempo mayormente seco, con temperaturas entre diez y veintiún grados.','La República / Ideam','https://www.larepublica.co/economia/ideam-advierte-sobre-lluvias-en-varias-zonas-del-pais-para-este-miercoles-11-de-noviembre-4522340'),
('TECNOLOGÍA','MEDELLÍN REÚNE EXPERTOS EN INTELIGENCIA ARTIFICIAL','Medellín desarrolla hasta el trece de noviembre el encuentro INMERXIA, dedicado a la inteligencia artificial, con conferencias y actividades para empresas, estudiantes y profesionales.','INMERXIA oficial','https://inmerxia.co/')
]
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
 d.text((58,158),'MIÉRCOLES 11 NOV 2026 · 13:30',font=font(19,False),fill='#67e6db')
 if kind=='intro':
  block(d,'CUATRO NOTICIAS VERIFICADAS',55,405,font(55),'white',600)
  block(d,'Colombia · Economía · Ambiente · Tecnología',55,750,font(30,False),'#c8d8ed',600)
 elif kind=='outro':
  block(d,'MÁS INFORMACIÓN',55,400,font(55),'white',600)
  block(d,'Las fuentes originales están en nuestra web. Enlace en la bio.',55,670,font(33,False),'#c8d8ed',600)
 else:
  tag,title,voice,source,url=story
  d.text((50,275),tag,font=font(28),fill='#67e6db')
  block(d,title,50,375,font(48),'white',625)
  d.rounded_rectangle((46,635,674,958),radius=25,fill='#173659')
  d.text((69,663),'RESUMEN INFORMATIVO',font=font(26),fill='white')
  for k in range(7):
   x=80+k*80;height=65+(k*41+i*19)%150
   d.rounded_rectangle((x,911-height,x+44,911),radius=6,fill='#5bdcda' if k%2 else '#638bc8')
  d.text((55,1010),'FUENTE: '+source,font=font(23,False),fill='white')
  d.text((55,1054),'11 NOVIEMBRE 2026',font=font(22,False),fill='#67e6db')
 d.rectangle((0,1170,W,H),fill='#173659')
 d.text((45,1190),'@resumen.noticias',font=font(25),fill='white')
 d.text((45,1230),'colombia-al-dia.pages.dev',font=font(21,False),fill='#67e6db')
 im.save(path)
def run(a,**kwargs):subprocess.run(a,check=True,stdout=subprocess.DEVNULL,**kwargs)
sess=ort.SessionOptions();sess.intra_op_num_threads=2;sess.inter_op_num_threads=1
k=Kokoro.from_session(ort.InferenceSession('/tmp/kokoro-v1.0.onnx',sess_options=sess,providers=['CPUExecutionProvider']),'/tmp/voices-v1.0.bin')
scenes=[('intro',None,'ORBIUNO. Miércoles once de noviembre. Estas son cuatro noticias verificadas.')]+[('news',s,s[2]+' Fuente: '+s[3]+'.') for s in STORIES]+[('outro',None,'Más noticias y sus fuentes en Colombia al día. Encuentra nuestra web desde el perfil de ORBIUNO.')]
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
 video=OUT/'ORBIUNO_2026-11-11_1330.mp4'
 run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(txt),'-c','copy','-movflags','+faststart',str(video)])
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_type,width,height','-of','json',str(video)],text=True))
assert float(probe['format']['duration'])>=35 and any(s.get('codec_type')=='audio' for s in probe['streams'])
(OUT/'fuentes.json').write_text(json.dumps({'fecha':'2026-11-11','stories':[{'title':s[1],'source':s[3],'url':s[4]} for s in STORIES],'probe':probe},ensure_ascii=False,indent=2))
print('VIDEO_LISTO',video,probe['format']['duration'],flush=True)
