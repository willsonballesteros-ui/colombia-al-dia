import json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from kokoro_onnx import Kokoro
import onnxruntime as ort
import numpy as np
OUT=Path('dist/orbiuno-2026-11-11-cierre');OUT.mkdir(parents=True,exist_ok=True)
STORIES=[
('ECONOMÍA','DÓLAR CIERRA EN 3.295 PESOS','El dólar cerró las operaciones del miércoles once de noviembre alrededor de tres mil doscientos noventa y cinco pesos. Finalizó por debajo de la tasa representativa del mercado del día, de tres mil doscientos noventa y siete pesos.','Semana / BVC','https://www.semana.com/economia/macroeconomia/articulo/dolar-cerro-a-la-baja-y-finalizo-la-jornada-del-miercoles-11-de-noviembre-mas-barato/202606/'),
('COLOMBIA','HACIENDA RADICA LEY DE RESCATE ECONÓMICO','El Ministerio de Hacienda informó que radicó ante el Congreso el proyecto de Ley de Rescate Económico. Según el Gobierno, la iniciativa contempla devolver el IVA a diecinueve millones de colombianos. Aún es una propuesta legislativa, no una ley aprobada.','Ministerio de Hacienda','https://www.minhacienda.gov.co/home'),
('TECNOLOGÍA','CHIPS DE NVIDIA LLEGAN A UNIVERSIDAD SANCIONADA','Reuters revisó registros de compras que muestran que una universidad china incluida en una lista restrictiva de Estados Unidos adquirió chips de inteligencia artificial Nvidia H doscientos a través de proveedores locales. El hallazgo reabre el debate sobre los controles de exportación.','Reuters','https://www.reuters.com/world/pla-linked-chinese-university-bought-nvidia-h200-chips-despite-us-blacklist-2026-11-11/'),
('MEDIOAMBIENTE','ALERTAS TEMPRANAS FRENTE A RIESGOS CLIMÁTICOS','Un análisis divulgado por Reuters muestra que los sistemas de alerta por desastres todavía tienen vacíos de cobertura. Según un borrador de Naciones Unidas citado en el informe, sesenta y cuatro países cumplen las cuatro áreas esenciales de alerta y preparación.','Reuters / Naciones Unidas','https://www.reuters.com/sustainability/cop/disaster-warning-systems-race-keep-pace-with-galloping-climate-risks-2026-11-11/')
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
 d.text((58,158),'MIÉRCOLES 11 NOV 2026 · 22:00',font=font(19,False),fill='#67e6db')
 if kind=='intro':
  block(d,'CIERRE DEL DÍA: 4 NOTICIAS',55,405,font(55),'white',600)
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
scenes=[('intro',None,'ORBIUNO. Cierre del día del miércoles once de noviembre. Estas son cuatro noticias de Colombia y el mundo.')]+[('news',s,s[2]+' Fuente: '+s[3]+'.') for s in STORIES]+[('outro',None,'Más noticias y sus fuentes en Colombia al día. Encuentra nuestra web desde el perfil de ORBIUNO.')]
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
 video=OUT/'ORBIUNO_2026-11-11_CIERRE.mp4'
 run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(txt),'-c','copy','-movflags','+faststart',str(video)])
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_type,width,height','-of','json',str(video)],text=True))
assert float(probe['format']['duration'])>=35 and any(s.get('codec_type')=='audio' for s in probe['streams'])
(OUT/'fuentes.json').write_text(json.dumps({'fecha':'2026-11-11','edicion':'cierre_22h','stories':[{'title':s[1],'source':s[3],'url':s[4]} for s in STORIES],'probe':probe},ensure_ascii=False,indent=2))
print('VIDEO_LISTO',video,probe['format']['duration'],flush=True)
