#!/usr/bin/env python3
"""Idempotent scheduling queue for ORBIUNO. Standard library only."""
import datetime as dt
import json
import os
import re
import sys
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

def clock():
    return dt.datetime.now(dt.timezone.utc)

def when(value):
    d=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
    if not d.tzinfo: raise ValueError("A timezone offset is required")
    return d

def valid_url(url):
    p=urlsplit(url)
    return p.scheme=="https" and bool(p.netloc) and not p.username and not p.password

def validate(post):
    for field in ("id","account","platform","media_url","caption","source_url","rights_confirmed","scheduled_at","status"):
        if field not in post: raise ValueError("Missing "+field)
    if not re.fullmatch(r"[\w-]{4,80}",post["id"]): raise ValueError("Invalid ID")
    if post["account"]!="orbiuno": raise ValueError("Unknown account")
    if post["platform"] not in ("instagram","facebook"): raise ValueError("Invalid platform")
    if post["status"] not in ("draft","scheduled","publishing","published","needs_review"): raise ValueError("Invalid status")
    if not valid_url(post["media_url"]) or not valid_url(post["source_url"]): raise ValueError("A public HTTPS media and source URL are required")
    if not (20<=len(post["caption"])<=2200): raise ValueError("Invalid caption")
    if not isinstance(post["rights_confirmed"],bool): raise ValueError("rights_confirmed must be boolean")
    when(post["scheduled_at"])
    if post["status"]=="published" and not post.get("post_id"): raise ValueError("Published post requires Meta post ID")

def load(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    ids=set()
    for post in data["posts"]:
        validate(post)
        if post["id"] in ids: raise ValueError("Duplicate publication ID")
        ids.add(post["id"])
    return data

def save(path,data):
    target=Path(path)
    temp=target.with_suffix(".tmp")
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(temp,target)

def dispatch(post):
    if post["platform"]=="instagram":
        from publish_instagram_direct import publish
        return publish(post["media_url"],post["caption"],confirmed=True)
    from publish_facebook_direct import publish_photo
    return publish_photo(post["media_url"],post["caption"])

def persist_attempt(path):
    subprocess.run(["git", "add", "--", str(path)], check=True)
    subprocess.run(["git", "commit", "-m", "chore: record ORBIUNO publication attempt [skip ci]"], check=True)
    subprocess.run(["git", "push", "origin", "HEAD:refs/heads/main"], check=True)


def run(path="data/publishing_queue.json", sender=dispatch, dry_run=False, at=None,
        checkpoint=None):
    data=load(path)
    events=[]
    at=at or clock()
    for post in data["posts"]:
        if post["status"]!="scheduled" or when(post["scheduled_at"])>at: continue
        if dry_run:
            events.append({"id": post["id"], "status": "due" if post["rights_confirmed"] else "needs_review"})
            continue
        if not post["rights_confirmed"]:
            post["status"]="needs_review"
            post["error"]="Image rights not confirmed"
        else:
            # Lock and persist BEFORE network requests; fail closed if the result is ambiguous.
            post["status"]="publishing"
            post["attempted_at"]=clock().isoformat()
            save(path,data)
            if checkpoint is not None:
                checkpoint(path)
            try:
                result=sender(post)
                post_id=result.get("post_id") or result.get("media_id")
                if not post_id: raise RuntimeError("Meta did not return a publication ID")
                post["post_id"]=str(post_id)
                post["permalink"]=result.get("permalink","")
                post["status"]="published"
                post["published_at"]=clock().isoformat()
                post.pop("error",None)
            except Exception as exc:
                post["status"]="needs_review"
                post["error"]=str(exc)[:350]
        events.append({"id":post["id"],"status":post["status"],"permalink":post.get("permalink","")})
        save(path,data)
    if not dry_run: save(path,data)
    return events

if __name__=="__main__":
    events = run(
        dry_run="--dry-run" in sys.argv,
        checkpoint=persist_attempt if "--persist-attempt" in sys.argv else None,
    )
    print(json.dumps({"events":events},ensure_ascii=False))
    if any(x["status"]=="needs_review" for x in events):sys.exit(2)
