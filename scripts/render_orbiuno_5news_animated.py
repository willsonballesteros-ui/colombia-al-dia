#!/usr/bin/env python3
"""ORBIUNO five-news render. Reads SEVEN voiced segments plus five independently
narrated headline clips; per-headline timing derives from actual ffprobe durations.
Nothing is editorially approved or uploaded by this renderer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont

W,H,FPS=1080,1920,24
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NORMAL="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
VOICE_ID="6ce26db0cb6f4e7881b85452619f7f19"
GATES=("editorialApproved","imagesApproved","voiceApproved","pronunciationApproved","webSyncApproved","finalReviewApproved")

def run(*args):
    return subprocess.run([str(x) for x in args],capture_output=True,text=True,check=True).stdout

def probe(path):
    return json.loads(run("ffprobe","-v","error","-show_format","-show_streams","-of","json",path))

def duration(path):
    return float(probe(path)["format"]["duration"])

def asset(base, rel, types):
    if not isinstance(rel,str) or not rel or rel.startswith(("/", "~")):
        raise ValueError("Invalid asset path")
    p=(base/rel).resolve()
    if not p.is_relative_to(base.resolve()) or p.suffix.lower() not in types or not p.is_file() or p.stat().st_size<1000:
        raise ValueError("Missing/unapproved asset: "+str(rel))
    return p

def face(size, bold=True):
    return ImageFont.truetype(BOLD if bold else NORMAL,size)

def lines(draw, text, maxwidth, f, maxlines=3):
    result=[]; line=""
    for word in text.split():
        candidate=(line+" "+word).strip()
        if draw.textbbox((0,0),candidate,font=f)[2] <= maxwidth:
            line=candidate
        else:
            if line: result.append(line)
            line=word
    if line: result.append(line)
    if len(result)>maxlines:
        raise ValueError("Text would be truncated, shorten editorial headline: "+text)
    return result

def background():
    im=Image.new("RGB",(W,H),(7,25,57))
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,18),fill=(59,226,207))
    d.text((60,65),"ORBIUNO",font=face(80),fill="white")
    return im

def opening(items, active, day, out):
    im=background();d=ImageDraw.Draw(im)
    d.text((60,190),"CINCO TITULARES",font=face(44),fill=(59,226,207))
    for i,item in enumerate(items):
        y=320+i*263
        selected=i==active
        d.rectangle((60,y,1020,y+235),fill=(24,68,123) if selected else (13,36,73),
                    outline=(255,220,0) if selected else (59,226,207),width=5 if selected else 2)
        d.text((90,y+12),f"{i+1:02d}  {item['category'][:28]}",font=face(27),fill=(255,220,0) if selected else (59,226,207))
        f=face(35)
        for j,line in enumerate(lines(d,item["title"],875,f,3)):
            d.text((90,y+68+j*47),line,font=f,fill="white" if selected else (160,178,207))
    d.text((65,1760),day+" · @resumen.noticias",font=face(27),fill="white")
    im.save(out)

def news_slide(item, index, day, image_path, out):
    im=background();d=ImageDraw.Draw(im)
    with Image.open(image_path) as source:
        photo=ImageOps.fit(source.convert("RGB"),(W,960),method=Image.Resampling.LANCZOS)
    im.paste(photo,(0,235));d=ImageDraw.Draw(im)
    d.rectangle((0,235,W,312),fill=(7,25,57))
    d.text((60,250),f"{index:02d}/05 · {item['category'][:30]}",font=face(30),fill="white")
    d.rectangle((0,1195,W,H),fill=(7,25,57))
    f=face(44)
    for j,line in enumerate(lines(d,item["title"],950,f,4)):
        d.text((65,1250+j*59),line,font=f,fill="white")
    d.text((65,1590),"FUENTE: "+item["source"]["name"][:48],font=face(26),fill=(59,226,207))
    d.text((65,1640),"IMAGEN: "+item["image"]["credit"][:45],font=face(24,False),fill="white")
    d.text((65,1770),day+" · @resumen.noticias",font=face(25),fill="white")
    im.save(out)

def end_slide(day, out):
    im=background();d=ImageDraw.Draw(im)
    d.text((65,610),"SÍGUENOS",font=face(72),fill="white")
    d.text((65,760),"@resumen.noticias",font=face(47),fill=(59,226,207))
    d.text((65,900),"colombia-al-dia.pages.dev",font=face(35),fill="white")
    d.text((65,1720),day,font=face(30),fill="white")
    im.save(out)

def check_manifest(m,base,release):
    news=m.get("news",[])
    voice=m.get("voice",{})
    if m.get("brand")!="ORBIUNO" or len(news)!=5 or len({x.get("id") for x in news})!=5:
        raise ValueError("Exactly five distinct news required")
    if voice.get("id")!=VOICE_ID or float(voice.get("speed",0))!=1.25 or float(voice.get("recordedAtSpeed",0)) not in (1.0,1.25):
        raise ValueError("Camila Vega source speed and ID must be evidenced")
    lead=m.get("intro",{}).get("leadAudioFile")
    headings=m.get("intro",{}).get("headlineAudioFiles",[])
    if not lead or len(headings)!=5:
        raise ValueError("Opening requires leadAudioFile and five separate voiced headline clips")
    sounds=[asset(base,lead,{".wav",".mp3",".m4a"})]
    sounds += [asset(base,p,{".wav",".mp3",".m4a"}) for p in headings]
    for i,item in enumerate(news):
        if item.get("verification")!="editorial_verified" or item.get("date")!=m.get("editionDate"):
            raise ValueError("Unverified news item "+str(i+1))
        source=item.get("source",{})
        if not source.get("name") or not source.get("url","").startswith("https://"):
            raise ValueError("Missing direct source")
        img=item.get("image",{})
        if img.get("rightsVerified") is not True or not all(img.get(x) for x in ("credit","license","sourceUrl")):
            raise ValueError("Image rights not evidenced")
        asset(base,img.get("file"),{".png",".jpg",".jpeg",".webp"})
        sounds.append(asset(base,item.get("audioFile"),{".wav",".mp3",".m4a"}))
    sounds.append(asset(base,m.get("outro",{}).get("audioFile"),{".wav",".mp3",".m4a"}))
    music=m.get("music")
    if music:
        if music.get("rightsVerified") is not True or not all(music.get(x) for x in ("credit","license","sourceUrl")):
            raise ValueError("Music rights not evidenced")
        asset(base,music.get("file"),{".mp3",".wav",".m4a"})
    if release:
        if not music or any(m.get("approval",{}).get(g) is not True for g in GATES):
            raise ValueError("Release approval gates incomplete")
    return sounds

def encode(image,audio,output,speed):
    run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
        "-loop","1","-framerate",FPS,"-i",image,"-i",audio,
        "-filter_complex",f"[1:a]atempo={speed:.5f},aresample=48000[a]",
        "-map","0:v","-map","[a]","-c:v","libx264","-preset","veryfast",
        "-crf","24","-pix_fmt","yuv420p","-r",FPS,
        "-c:a","aac","-b:a","160k","-shortest",output)

def render(manifest,output,release=False):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe required")
    manifest=Path(manifest).resolve();base=manifest.parent
    m=json.loads(manifest.read_text(encoding="utf-8"))
    audios=check_manifest(m,base,release)
    speed=1.25/float(m["voice"]["recordedAtSpeed"])
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    timeline=[];current=duration(audios[0])/speed
    with tempfile.TemporaryDirectory(prefix="orbiuno-five-") as folder:
        t=Path(folder);parts=[]
        # Lead intro uses all five titles in neutral state, not highlighted.
        for k,a in enumerate(audios):
            png=t/f"s{k:02d}.png";part=t/f"p{k:02d}.mp4"
            if k==0:
                opening(m["news"],-1,m["editionDate"],png)
            elif 1<=k<=5:
                opening(m["news"],k-1,m["editionDate"],png)
                length=duration(a)/speed
                timeline.append({"id":m["news"][k-1]["id"],"start":round(current,3),"end":round(current+length,3),"title":m["news"][k-1]["title"]})
                current+=length
            elif 6<=k<=10:
                item=m["news"][k-6]
                photo=asset(base,item["image"]["file"],{".png",".jpg",".jpeg",".webp"})
                news_slide(item,k-5,m["editionDate"],photo,png)
            else:
                end_slide(m["editionDate"],png)
            encode(png,a,part,speed);parts.append(part)
        listing=t/"concat.txt"
        listing.write_text("".join("file '"+str(p)+"'\n" for p in parts),encoding="utf-8")
        clean=t/"clean.mp4"
        run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
            "-f","concat","-safe","0","-i",listing,"-c:v","copy","-c:a","aac",
            "-b:a","160k","-movflags","+faststart",clean)
        if m.get("music"):
            music=asset(base,m["music"]["file"],{".wav",".mp3",".m4a"})
            run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-i",clean,
                "-stream_loop","-1","-i",music,"-filter_complex",
                "[0:a]aresample=48000[v];[1:a]volume=0.05,aresample=48000[b];[v][b]amix=inputs=2:duration=first[a]",
                "-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","160k",output)
        else:
            shutil.copyfile(clean,output)
    media=probe(output)
    video=next((s for s in media["streams"] if s.get("codec_type")=="video"),{})
    audio=next((s for s in media["streams"] if s.get("codec_type")=="audio"),{})
    total=float(media["format"]["duration"])
    if (video.get("width"),video.get("height"),video.get("codec_name"),audio.get("codec_name"))!=(W,H,"h264","aac"):
        output.unlink(missing_ok=True)
        raise ValueError("Wrong codecs/resolution or missing sound")
    if total<=0:
        raise ValueError("Invalid output duration")
    report={"newsIds":[x["id"] for x in m["news"]],"headlineTimings":timeline,
            "durationSec":total,"format":"1080x1920 H264/AAC","sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
            "status":"RELEASE_GATE_PASSED" if release else "PREVIEW_ONLY_NOT_APPROVED"}
    output.with_suffix(".report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("manifest",type=Path);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--release",action="store_true");a=p.parse_args()
    try:print(json.dumps(render(a.manifest,a.output,a.release),ensure_ascii=False,indent=2))
    except Exception as e:p.exit(2,"BLOQUEO: "+str(e)+"\n")
