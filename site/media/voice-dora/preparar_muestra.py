from pathlib import Path
from kokoro_onnx import Kokoro
import soundfile as sf
import json
import onnxruntime as ort
import numpy as np
import re
p=Path(__file__).parent
text='''Estas son las diez noticias para cerrar el cinco de noviembre. La República informa: Nutresa cerró la compra de Presto, Davivienda incorporó clientes de Davibank y una garantía respalda crédito para el Metro de Bogotá. Noticias RCN: el dólar promedió tres mil doscientos veintiocho pesos con diecinueve. Minciencias propone cooperación con Corea en inteligencia artificial. Según EFE, Santiago Peña presentó su renuncia en Paraguay; Herzog anunciará el domingo el encargo de Gobierno en Israel; en Ecuador, José Serrano fue llamado a juicio por el caso Villavicencio: no es una condena; y Zelenski pide equipos para reparar la red eléctrica de Ucrania. EuroEFE: António Costa pide reforzar la cooperación con Latinoamérica. ¡La noticia no termina aquí! Escucha cada noticia completa, una por una, en voz alta en nuestra web. Toca arroba resumen punto noticias y abre el enlace del perfil.'''
(p/'guion.txt').write_text(text,encoding='utf-8')
options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1;options.enable_cpu_mem_arena=False;options.enable_mem_pattern=False;options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
session=ort.InferenceSession('/tmp/kokoro-v1.0.int8.onnx',sess_options=options,providers=['CPUExecutionProvider'])
k=Kokoro.from_session(session,'/tmp/voices-v1.0.bin')
pieces=[]
for i,line in enumerate(re.split(r'(?<=[.!?;])\s+',text)):
 if not line.strip():continue
 segment,sr=k.create(line,'ef_dora',speed=1.0,lang='es',sentence_pause=.16,clause_pause=.08)
 pieces.extend([segment,np.zeros(int(sr*.12),dtype=np.float32)])
 print('Frase',i+1,'lista',flush=True)
a=np.concatenate(pieces)
sf.write(str(p/'dora_original.wav'),a,sr,subtype='PCM_16')
(p/'voz.json').write_text(json.dumps({'engine':'kokoro-onnx 0.6.1','voice':'ef_dora','language':'es','originalRate':1.0,'finalSpeed':1.5,'referenceEvidence':'Repositorio a43a5b19288bb9e7f2a7d36dafeaa8d14cd3fe20 scripts/render_narrated.py y media/2026-11-04/boletin-narrado.json','publication':False,'purpose':'Muestra del resumen del 5 de noviembre y cierre con enlace del perfil'},ensure_ascii=False,indent=2))
print('Voz Dora generada',len(a)/sr,'segundos',flush=True)
