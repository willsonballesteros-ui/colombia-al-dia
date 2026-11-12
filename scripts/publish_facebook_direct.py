#!/usr/bin/env python3
"""Facebook Page photo publishing via official Meta Graph API."""
import argparse,json,os,urllib.parse,urllib.request

def publish_photo(image_url,caption):
    page=os.environ.get("FB_PAGE_ID","")
    token=os.environ.get("FB_PAGE_ACCESS_TOKEN","")
    if not page or not token: raise RuntimeError("Missing Facebook Page credentials")
    url=urllib.parse.urlsplit(image_url)
    if url.scheme!="https" or not url.netloc or url.username: raise ValueError("Public HTTPS photo required")
    payload=urllib.parse.urlencode({"url":image_url,"caption":caption,"access_token":token,"published":"true"}).encode()
    req=urllib.request.Request(f"https://graph.facebook.com/v26.0/{page}/photos",data=payload,method="POST")
    with urllib.request.urlopen(req,timeout=40) as r: response=json.load(r)
    post_id=response.get("post_id") or response.get("id")
    if not post_id: raise RuntimeError("Meta did not confirm a post ID")
    return {"post_id":str(post_id),"media_id":str(response.get("id",""))}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--image-url",required=True)
    p.add_argument("--caption-file",required=True)
    p.add_argument("--rights-confirmed",action="store_true")
    p.add_argument("--confirm-publish",action="store_true")
    args=p.parse_args()
    if not args.rights_confirmed or not args.confirm_publish: p.error("Rights and publication confirmation required")
    with open(args.caption_file,encoding="utf-8") as file: caption=file.read()
    print(json.dumps(publish_photo(args.image_url,caption)))
