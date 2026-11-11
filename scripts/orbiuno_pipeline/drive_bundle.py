#!/usr/bin/env python3
"""Download a verified edition asset ZIP from the shared Drive via service account.
Only editions/** may be extracted, with a small explicit size limit.
"""
from __future__ import annotations
import io
import json
import os
import stat
import sys
import zipfile
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

ROOT=Path(__file__).resolve().parents[1]
MAX_ZIP=300*1024*1024
MAX_UNPACKED=600*1024*1024

def download(file_id,credentials):
    info=json.loads(credentials)
    creds=service_account.Credentials.from_service_account_info(info,scopes=["https://www.googleapis.com/auth/drive.readonly"])
    api=build("drive","v3",credentials=creds,cache_discovery=False)
    request=api.files().get_media(fileId=file_id,supportsAllDrives=True)
    memory=io.BytesIO()
    downloader=MediaIoBaseDownload(memory,request,chunksize=1024*1024)
    done=False
    while not done:
        progress,done=downloader.next_chunk(num_retries=3)
        if memory.tell()>MAX_ZIP:
            raise ValueError("ZIP exceeds 300 MB")
    memory.seek(0)
    return memory

def extract(archive,root):
    names=set();total=0;files=[]
    with zipfile.ZipFile(archive) as z:
        members=z.infolist()
        if len(members)>1000:
            raise ValueError("Too many ZIP entries")
        for member in members:
            raw=member.filename
            p=Path(raw)
            if p.is_absolute() or "\\" in raw or ".." in p.parts or not p.parts or p.parts[0]!="editions":
                raise ValueError("ZIP must contain only editions/**, no escapes")
            if (member.external_attr >> 16) & 0o170000 == stat.S_IFLNK:
                raise ValueError("Symlinks not allowed")
            if raw in names:
                raise ValueError("Repeated zip path")
            names.add(raw)
            total+=member.file_size
            if total>MAX_UNPACKED:
                raise ValueError("Unpacked assets exceed 600 MB")
            target=(root/p).resolve()
            if not target.is_relative_to(root.resolve()):
                raise ValueError("ZIP path escaped repository")
            if member.is_dir():
                continue
            if target.exists():
                raise ValueError("Refusing to overwrite existing file "+raw)
            files.append((member,target))
        for member,dest in files:
            dest.parent.mkdir(parents=True,exist_ok=True)
            with z.open(member) as source,dest.open("wb") as sink:
                while True:
                    block=source.read(1024*1024)
                    if not block:break
                    sink.write(block)
    return [str(dst.relative_to(root)) for _,dst in files]

if __name__=="__main__":
    file_id=os.environ.get("ORBIUNO_DRIVE_BUNDLE_ID","").strip()
    auth=os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON","").strip()
    if not file_id or not auth:
        sys.exit("BLOCKED: Drive bundle ID and GDRIVE_SERVICE_ACCOUNT_JSON required")
    result=extract(download(file_id,auth),ROOT)
    print("Extracted "+str(len(result))+" files from authorized Drive bundle")
