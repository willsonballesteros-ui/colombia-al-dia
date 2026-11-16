#!/usr/bin/env python3
"""Produce MP4 with Gonzalo only; never publish or overwrite source."""
import asyncio,json,subprocess,tempfile,shutil,hashlib
from pathlib import Path
import edge_tts
ROOT=Path(__file__).resolve().parents[1]
DAY="2026-11-15"; SLOT="19:00"
SRC=ROOT/"media"/DAY/"ORBIUNO_2026-11-15_1900_6_NOTICIAS.mp4"
OUT=ROOT/"media"/DAY/"ORBIUNO_2026-11-15_1900_GONZALO_FINAL.mp4"
def cmd(*a):
 return subprocess.run(a,check=True,text=True,capture_output=True).stdout
def probe(p):
 return json.loads(cmd("ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,codec_name,width,height","-of","json",str(p)))
async def main():
 db=json.loads((ROOT/"noticias.json").read_text())
 notes=sorted([n for n in db["news"] if n.get("date")==DAY and n.get("editionSlot")==SLOT and n.get("verification")=="editorial_verified"],key=lambda n:n.get("priority",999))
 assert len(notes)==6 and len({n["id"] for n in notes})==6, "Se requieren seis noticias"
 assert SRC.is_file(),"Falta MP4 original"
 sentences=["Seis noticias de Colombia y el mundo. Edición de las siete de la noche."]
 sentences += [str(n.get("reelLine") or n["summary"]).strip() for n in notes]
 sentences += ["Escucha las noticias completas en nuestra página web, colombia al día punto pages punto dev."]
 with tempfile.TemporaryDirectory() as td:
  tmp=Path(td); audio=tmp/"gonzalo.mp3"
  await edge_tts.Communicate(text=" ".join(sentences),voice="es-CO-GonzaloNeural",rate="+20%").save(str(audio))
  assert audio.stat().st_size>10000,"No se genero voz Gonzalo"
  vd=float(probe(SRC)["format"]["duration"]);ad=float(probe(audio)["format"]["duration"])
  if ad>vd-0.3: raise RuntimeError(f"Audio {ad:.2f}s supera video {vd:.2f}s: no recortar")
  video=tmp/"result.mp4"
  cmd("ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(SRC),"-i",str(audio),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","160k","-af",f"apad=whole_dur={vd:.3f}","-t",f"{vd:.3f}","-movflags","+faststart",str(video))
  info=probe(video)
  assert any(s.get("codec_type")=="video" and s.get("width")==1080 and s.get("height")==1920 for s in info["streams"])
  assert any(s.get("codec_type")=="audio" and s.get("codec_name")=="aac" for s in info["streams"])
  assert abs(float(info["format"]["duration"])-vd)<0.4
  shutil.copy2(video,OUT)
  manifest={"edition":DAY,"slot":SLOT,"voice":"es-CO-GonzaloNeural","rate":"+20%","newsIds":[n["id"] for n in notes],"duration":vd,"audioDuration":ad,"sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),"published":False,"audioListeningVerified":False}
  (OUT.parent/"orbiuno_1900_gonzalo_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
  print("GENERADO",OUT,"audio",ad,"video",vd,"requiere revision auditiva")
if __name__=="__main__": asyncio.run(main())
