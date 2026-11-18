#!/usr/bin/env python3
"""Genera página web editorial de ORBIUNO alineada al Reel de las 08:00 (18/11).
Cada audio reproduce el ARTÍCULO EDITORIAL PROPIO completo, sin recortes.
"""
import html,json,shutil,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"build"/"am_18nov"
edition=json.loads((ROOT/"editions"/"preview_media_2026-11-18-am.json").read_text(encoding="utf-8"))
news=edition["orbiuno"]["news"]
credits=json.loads((OUT/"orbiuno"/"credits.json").read_text(encoding="utf-8"))
report=json.loads((OUT/"orbiuno"/"audio"/"audio_report.json").read_text(encoding="utf-8"))
assert report["status"]=="ok" and len(report["segments"])==8
assert len(news)==len(credits)==6
h=lambda s:html.escape(str(s),quote=True)
# Voz Salomé: cada MP3 reproduce exactamente el artículo original que aparece en la web.
voice_input=OUT/"orbiuno"/"web_articles_input.json"
full_voice=OUT/"orbiuno"/"web-audio"
assert all(len(n.get("article",""))>=700 and "\n\n" in n["article"] for n in news), "BLOCKED: artículos íntegros insuficientes"
voice_input.write_text(json.dumps({"segments":[{"id":f"n{i:02d}","text":n["article"]} for i,n in enumerate(news,1)]},ensure_ascii=False,indent=2),encoding="utf-8")
subprocess.run([sys.executable,str(ROOT/"scripts"/"generate_voice.py"),"--input",str(voice_input),"--out",str(full_voice)],check=True)
audio_report=json.loads((full_voice/"audio_report.json").read_text(encoding="utf-8"))
assert audio_report["status"]=="ok" and len(audio_report["segments"])==6
assert (full_voice/"full.mp3").stat().st_size>10000
parts=[]
for i,(n,c) in enumerate(zip(news,credits),1):
    assert c["source"]==n["url"] and c["image_title"] and c["license"] and c["author"]
    rel="media/2026-11-18/orbiuno-am/"
    photo=rel+c["image_file"]
    audio=rel+"web-audio/n%02d.mp3"%i
    icon=(f'<img class="source-icon" src="{h(rel+c["source_icon"])}" alt="Icono de {h(n["source"])}">' if c.get("source_icon") else "")
    article_html="".join("<p>"+h(p)+"</p>" for p in n["article"].split("\n\n") if p.strip())
    parts.append(f'''<article class="news" id="noticia-{i}">
<div class="photo"><img loading="lazy" src="{h(photo)}" alt="Fotografía de contexto verificada para {h(n["title"])}"></div>
<div class="story"><span class="kicker">NOTICIA {i} DE 6 · 18 NOV 2026</span>
<h2>{h(n["title"])}</h2>
{article_html}
<div class="media"><span class="sourcename">{icon}{h(n["source"])}</span><a href="{h(n["url"])}" target="_blank" rel="noopener">Fuente original y ampliación</a></div>
<label for="audio{i}">Escuchar la noticia completa en español colombiano</label><audio id="audio{i}" controls preload="none" src="{h(audio)}"></audio>
<small>Fotografía: {h(c["author"])} · {h(c["license"])} · <a href="{h(c["commons"])}" target="_blank" rel="noopener">origen y licencia</a>. Imagen de contexto documental.</small>
</div></article>''')
content=f'''<!doctype html><html lang="es-CO"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="ORBIUNO Noticias: seis noticias de Colombia y el mundo, 18 de noviembre de 2026, 8:00 a. m. Lee, escucha las noticias completas y consulta fuentes originales.">
<title>ORBIUNO · Seis noticias verificadas · 18 noviembre 2026 · 8:00 a. m.</title>
<style>
:root{{--bg:#08192f;--panel:#112d44;--teal:#3ce0d2;--gold:#f2ca68;--ink:#fff;}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 system-ui,-apple-system,sans-serif}}
header,main,footer{{max-width:1024px;margin:auto;padding:20px}}
header{{padding-top:35px}}header h1{{font-weight:900;letter-spacing:-1px;font-size:clamp(34px,8vw,66px);margin:6px 0}}
header p{{max-width:800px}} .chip{{color:var(--gold);font-weight:800}}a{{color:#9ff4e9}}
.news{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);margin:26px 0;overflow:hidden;background:var(--panel);border:1px solid #2b4b64;border-radius:22px}}
.photo img{{width:100%;height:100%;min-height:330px;object-fit:cover;display:block}}.story{{padding:24px}}.story h2{{font-size:clamp(25px,4.5vw,38px);line-height:1.15;margin:9px 0 14px}}
.kicker{{font-weight:900;color:var(--teal);font-size:13px}}.media{{display:flex;align-items:center;gap:12px;justify-content:space-between;flex-wrap:wrap;border-top:1px solid #456073;padding:12px 0;margin:14px 0}}.sourcename{{font-weight:900;font-size:19px;display:flex;gap:10px;align-items:center}}.source-icon{{height:37px;width:37px;object-fit:contain}}
label{{display:block;color:var(--gold);font-weight:800;margin-bottom:6px}}audio{{width:100%}}small{{display:block;color:#c4d8e2;margin-top:12px}}
.cta{{background:#0c3949;border-radius:14px;padding:16px;margin-top:24px}}@media(max-width:680px){{.news{{grid-template-columns:1fr}}.photo img{{height:300px;min-height:0}}}}
</style></head><body><header><div class="chip">18 DE NOVIEMBRE DE 2026 · 8:00 A. M. · COLOMBIA</div>
<h1>ORBIUNO Noticias</h1><p>Seis noticias verificadas de Colombia y el mundo, con fotografías reales acreditadas, artículos propios completos narrados con la voz Salomé y enlaces originales de las fuentes.</p>
<div class="cta">▶ <a href="media/2026-11-18/orbiuno-am/ORBIUNO_18_NOV_2026_0800_REEL_PUBLICAR.mp4">Ver el Reel completo de hoy</a> · Voz sintética en español colombiano a 1,25×<label for="fullaudio">Escuchar toda la edición completa</label><audio id="fullaudio" controls preload="none" src="media/2026-11-18/orbiuno-am/web-audio/full.mp3"></audio></div>
</header><main>{''.join(parts)}</main><footer><p>Edición de ORBIUNO @resumen.noticias · Fotos históricas o de contexto, no imágenes del acontecimiento salvo indicación expresa. Cada audio reproduce íntegramente la redacción propia de ORBIUNO presentada en esta página; la fuente original permanece enlazada.</p><p><a href="/">Volver a colombia-al-dia.pages.dev</a></p></footer></body></html>'''
(OUT/"edicion-2026-11-18-0800.html").write_text(content,encoding="utf-8")
print("ORBIUNO_WEB_PREVIEW",len(content),len(news),flush=True)
