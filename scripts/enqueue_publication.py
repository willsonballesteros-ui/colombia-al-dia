#!/usr/bin/env python3
"""Append a verified, licensed media post to the scheduling queue."""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from publishing_queue import load,save,validate,when

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--id",required=True)
    p.add_argument("--platform",choices=["instagram","facebook"],required=True)
    p.add_argument("--media-url",required=True)
    p.add_argument("--source-url",required=True)
    p.add_argument("--caption-file",required=True)
    p.add_argument("--scheduled-at",required=True)
    p.add_argument("--rights-confirmed",action="store_true")
    p.add_argument("--queue",default="data/publishing_queue.json")
    args=p.parse_args()
    if not args.rights_confirmed:p.error("Media rights confirmation required")
    post={"id":args.id,"account":"orbiuno","platform":args.platform,"media_url":args.media_url,
          "source_url":args.source_url,"caption":Path(args.caption_file).read_text(encoding="utf-8"),
          "rights_confirmed":True,"scheduled_at":args.scheduled_at,"status":"scheduled"}
    validate(post)
    data=load(args.queue)
    if any(p["id"]==post["id"] for p in data["posts"]):
        raise ValueError("Duplicate post ID: "+post["id"])
    data["posts"].append(post)
    save(args.queue,data)
    print(json.dumps({"status":"queued_not_published","id":post["id"],"scheduled_at":post["scheduled_at"]}))

if __name__=="__main__":main()
