#!/usr/bin/env python3
"""Facebook Pages Reels via official Meta Graph API, not ads or Metricool.
Manual opt-in; safe preflight; no unpublished claims; no bypass of restrictions.
"""
import argparse, json, os, subprocess, urllib.error, urllib.parse, urllib.request
from pathlib import Path

GRAPH="https://graph.facebook.com/v27.0"
BRANDS={
 "orbiuno":{"id":"1516359454884058","stem":"ORBIUNO-2026-11-13_19H_6_NOTICIAS.mp4",
            "token":"ORBIUNO_FB_PAGE_ACCESS_TOKEN","page":"ORBIUNO_FB_PAGE_ID",
            "key":"ORBIUNO-FB-20261113-1900","expected":6},
 "mycar":{"id":"100141169648736","stem":"MYCAR-2026-11-13_19H_4_NOTICIAS.mp4",
          "token":"MYCAR_FB_PAGE_ACCESS_TOKEN","page":"MYCAR_FB_PAGE_ID",
          "key":"MYCAR-FB-20261113-1900","expected":4},
}
def call(url,token,params=None,method="GET",headers=None):
    data=urllib.parse.urlencode(params).encode() if params is not None else None
    req=urllib.request.Request(url,data=data,method=method,headers={
        "Authorization":"Bearer "+token, **(headers or {})})
    try:
        with urllib.request.urlopen(req,timeout=75) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        # Never print tokens, headers or full HTTP body.
        raise RuntimeError("Meta denied operation: HTTP %s" % e.code)
def verify_video(path):
    if not path.is_file():raise RuntimeError("Missing video")
    meta=json.loads(subprocess.check_output(
        ["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(path)]))
    video=next((s for s in meta["streams"] if s["codec_type"]=="video"),None)
    audio=next((s for s in meta["streams"] if s["codec_type"]=="audio"),None)
    if not video or not audio or video.get("width")!=720 or video.get("height")!=1280:
        raise RuntimeError("Video/audio or aspect ratio not validated")
    if not 4<=float(meta["format"]["duration"])<=60:
        raise RuntimeError("Reel duration is out of validated range")
    return path.stat().st_size
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--brand",choices=BRANDS,required=True)
    p.add_argument("--publish",action="store_true")
    args=p.parse_args()
    b=BRANDS[args.brand]
    path=Path("media/2026-11-13-1900")/b["stem"]
    size=verify_video(path)
    credits=json.loads((path.parent/(args.brand+"-credits.json")).read_text(encoding="utf8"))
    if len(credits.get("stories",[]))!=b["expected"] or len(credits.get("license_photos",[]))!=b["expected"]:
        raise RuntimeError("Source/rights count mismatch")
    page=os.environ.get(b["page"],"")
    token=os.environ.get(b["token"],"")
    print("REEL_READY",args.brand,"bytes",size,"page_id_matches_expected",page==b["id"])
    print("PAGE_CREDENTIALS", "CONFIGURED" if page and token else "MISSING")
    if not page or not token or page!=b["id"]:
        raise RuntimeError("Page token or verified Page ID is not configured; NO POST")
    # Only an authenticated Page's own token. We do not assume Windsor credentials
    # are available as GitHub secrets.
    profile=call(f"{GRAPH}/{page}?fields=id,name",token)
    if str(profile.get("id"))!=b["id"]:raise RuntimeError("Token belongs to another Page")
    print("META_AUTH_OK",args.brand,profile.get("name",""))
    # A pre-publication GET to avoid a duplicate. Absent list permission
    # is a fail-closed condition, never a justification to post blindly.
    listing=call(f"{GRAPH}/{page}/video_reels?fields=id,description&limit=100",token)
    ids=[x for x in listing.get("data",[]) if b["key"] in str(x.get("description",""))]
    if ids:
        print("ALREADY_PUBLISHED",args.brand,ids[0]["id"])
        return
    if not args.publish:
        print("PREFLIGHT_OK_NO_PUBLICATION",args.brand)
        return
    title="ORBIUNO Noticias | 6 noticias" if args.brand=="orbiuno" else "MyCar | 4 noticias"
    lines=["🌎 ORBIUNO — Edición 13 de noviembre 7:00 p. m." if args.brand=="orbiuno"
           else "🚗 MyCar — Edición 13 de noviembre 7:00 p. m."]
    lines += [f"{i}. {entry['title']}" for i,entry in enumerate(credits["stories"],1)]
    lines += ["Fuentes: "+", ".join(dict.fromkeys(x["source"] for x in credits["stories"])),
              "Fotografías auténticas de archivo; no necesariamente del evento actual.",
              "Créditos: "+", ".join(x["photo"]["artist"]+" ("+x["photo"]["license"]+")"
                                  for x in credits["license_photos"]),
              "ORBIUNO: https://colombia-al-dia.pages.dev/" if args.brand=="orbiuno"
                 else "Busco Autos: https://busco-autos.pages.dev/", b["key"]]
    caption="\n".join(lines)
    # Meta POST START; error 368 or 200 leaves Reel unpublished.
    start=call(f"{GRAPH}/{page}/video_reels",token,{"upload_phase":"start"},method="POST")
    reel_id=str(start.get("video_id",""))
    upload_url=start.get("upload_url","")
    if not reel_id or not upload_url.startswith("https://rupload.facebook.com/"):
        raise RuntimeError("Meta did not return verified Reel session")
    req=urllib.request.Request(upload_url,data=path.read_bytes(),method="POST",
        headers={"Authorization":"OAuth "+token,"offset":"0","file_size":str(size),
                 "Content-Type":"application/octet-stream"})
    try:
        with urllib.request.urlopen(req,timeout=120) as response: uploaded=json.load(response)
    except urllib.error.HTTPError as e:
        raise RuntimeError("Meta Reel upload denied HTTP "+str(e.code))
    if uploaded.get("success") is False:raise RuntimeError("Upload not accepted by Meta")
    result=call(f"{GRAPH}/{page}/video_reels",token,
        {"upload_phase":"finish","video_id":reel_id,"video_state":"PUBLISHED",
         "description":caption,"title":title},method="POST")
    if not result.get("success"):raise RuntimeError("Meta did not confirm final publishing")
    print("META_FINISH_ACCEPTED",args.brand,"video_id",reel_id,
          "post_id",result.get("post_id",""),"PROCESSING_CONFIRMATION_PENDING")
    # A successful FINISH can still be transcoding; do not claim visible until checked.
    status=call(f"{GRAPH}/{reel_id}?fields=status",token)
    print("META_VIDEO_STATUS",json.dumps(status.get("status",{}),ensure_ascii=False))
if __name__=="__main__":
    main()
