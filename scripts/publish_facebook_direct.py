#!/usr/bin/env python3
"""Publish one licensed photo to a Facebook Page using the Meta Graph API."""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--image-url', required=True)
    p.add_argument('--caption-file', required=True)
    p.add_argument('--rights-confirmed', action='store_true')
    p.add_argument('--confirm-publish', action='store_true')
    a = p.parse_args()
    if not (a.rights_confirmed and a.confirm_publish):
        p.error('Require --rights-confirmed and --confirm-publish')
    url = urllib.parse.urlsplit(a.image_url)
    if url.scheme != 'https' or not url.netloc or url.username:
        p.error('A public HTTPS image URL is required.')
    page = os.getenv('FB_PAGE_ID', '').strip()
    token = os.getenv('FB_PAGE_ACCESS_TOKEN', '').strip()
    if not (page and token):
        p.error('Configure FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN as secrets.')
    caption = open(a.caption_file, encoding='utf-8').read().strip()
    if not caption:
        p.error('Caption is required')
    version = os.getenv('FB_GRAPH_VERSION', 'v24.0')
    endpoint = f'https://graph.facebook.com/{version}/{page}/photos'
    payload = urllib.parse.urlencode({'url': a.image_url, 'caption': caption, 'access_token': token, 'published': 'true'}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(endpoint, data=payload, method='POST'), timeout=50) as res:
            result = json.load(res)
        if not result.get('id') and not result.get('post_id'):
            raise RuntimeError('No publication ID from Meta')
        print(json.dumps({'status':'published','media_id':result.get('id'), 'post_id':result.get('post_id')}, ensure_ascii=False))
    except urllib.error.HTTPError as exc:
        print(f'Facebook publication failed: HTTP {exc.code}: {exc.read().decode()[:400]}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
