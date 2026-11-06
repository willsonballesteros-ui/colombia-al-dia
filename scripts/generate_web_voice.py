"""Narración fija Dora de los reportajes propios; audio base a 1.25x."""
import hashlib,json,subprocess,os
from pathlib import Path
import numpy as np
import onnxruntime as ort
from kokoro_onnx import Kokoro
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'noticias.json').read_text());out=ROOT/'media/web-voice';out.mkdir(parents=True,exist_ok=True)
manifest={'voice':'ef_dora','baseRate':1.25,'items':{}}
old=json.loads((out/'manifest.json').read_text()) if (out/'manifest.json').exists() else {'items':{}}
manifest['items'].update(old.get('items',{}))
o=ort.SessionOptions();o.intra_op_num_threads=2;o.inter_op_num_threads=1;o.enable_cpu_mem_arena=False;o.enable_mem_pattern=False;o.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
session=ort.InferenceSession(os.environ.get('ORBIUNO_VOICE_MODEL','/tmp/kokoro-v1.0.onnx'),sess_options=o,providers=['CPUExecutionProvider'])
k=Kokoro.from_session(session,os.environ.get('ORBIUNO_VOICE_BANK','/tmp/voices-v1.0.bin'))
for n in sorted(data['news'],key=lambda x:x.get('priority',999)):
 if n.get('date')!=data['editionDate'] or n.get('verification')!='editorial_verified':continue
 text=n['title']+'. Fuente: '+n['sources'][0]['name']+'. '+n['audioFullTextEs']
 digest=hashlib.sha256(text.encode()).hexdigest();name=digest[:20]+'.mp3';p=out/name
 if not p.exists():
  audio,sr=k.create(text,'ef_dora',speed=1.25,lang='es',sentence_pause=.18,clause_pause=.09)
  subprocess.run(['ffmpeg','-y','-v','error','-f','f32le','-ar',str(sr),'-ac','1','-i','pipe:0','-c:a','libmp3lame','-b:a','64k',str(p)],input=np.asarray(audio,dtype=np.float32).tobytes(),check=True)
 manifest['items'][n['id']]={'url':'./media/web-voice/'+name,'text':text,'sha256':digest}
 (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 print(n['id'],p.stat().st_size,flush=True)
