from pathlib import Path
import numpy as np
import onnxruntime as ort
from kokoro_onnx import Kokoro
import soundfile as sf
import json
p=Path(__file__).parent
phrases=[
'Vamos con las diez noticias de este cinco de noviembre.',
'La República nos cuenta que Nutresa cerró la compra de Presto. También informa sobre la llegada de clientes de Davibank a Davivienda y una garantía para financiar el Metro de Bogotá.',
'En economía, Noticias RCN reporta un dólar promedio de tres mil doscientos veintiocho pesos con diecinueve.',
'Minciencias propone trabajar con Corea en inteligencia artificial.',
'Y en el mundo, según EFE: Santiago Peña presentó su renuncia en Paraguay. En Israel, Herzog anunciará el domingo el encargo para formar Gobierno.',
'En Ecuador, José Serrano fue llamado a juicio por el caso Villavicencio. Esto no es una condena.',
'También según EFE, Zelenski pidió equipos para reparar la red eléctrica de Ucrania.',
'Por su parte, EuroEFE recoge el llamado de António Costa a reforzar la cooperación con Latinoamérica.',
'¡La noticia no termina aquí! Escucha cada noticia completa, una por una, en voz alta en nuestra web. Toca arroba resumen punto noticias y abre el enlace del perfil.'
]
(p/'guion.txt').write_text('\n\n'.join(phrases))
o=ort.SessionOptions();o.intra_op_num_threads=2;o.inter_op_num_threads=1;o.enable_cpu_mem_arena=False;o.enable_mem_pattern=False;o.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
s=ort.InferenceSession('/tmp/kokoro-v1.0.onnx',sess_options=o,providers=['CPUExecutionProvider'])
k=Kokoro.from_session(s,'/tmp/voices-v1.0.bin');pieces=[]
for i,line in enumerate(phrases):
 a,sr=k.create(line,'ef_dora',speed=1.25,lang='es',sentence_pause=.18,clause_pause=.09)
 pieces.append(a)
 if i<len(phrases)-1:pieces.append(np.zeros(int(sr*.07),dtype=np.float32))
 print('Frase',i+1,'lista',flush=True)
a=np.concatenate(pieces);sf.write(str(p/'voz_natural.wav'),a,sr,subtype='PCM_16')
(p/'voz.json').write_text(json.dumps({'voice':'ef_dora','engine':'kokoro-onnx 0.6.1','model':'kokoro-v1.0.onnx float32','speed':1.25,'post_time_stretch':False,'durationSeconds':len(a)/sr,'script':'guion.txt','listening_review':'not_performed'},ensure_ascii=False,indent=2))
print('Duración',len(a)/sr,flush=True)
