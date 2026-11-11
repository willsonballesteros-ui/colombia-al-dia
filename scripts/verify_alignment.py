#!/usr/bin/env python3
"""Revisar coincidencia exacta de los cuatro IDs entre Reel, JSON web y web pública.
La ausencia de respuesta de la web bloquea aprobación, no se interpreta como OK.
"""
import argparse, json, urllib.request
from pathlib import Path


def check(manifest, newsdb, html):
    m=json.loads(Path(manifest).read_text(encoding='utf-8'))
    j=json.loads(Path(newsdb).read_text(encoding='utf-8'))
    expected=[x['id'] for x in m['news']]
    actual=sorted((x for x in j['news'] if x.get('date')==m['editionDate'] and x.get('editionSlot')==m['slot'] and
                   x.get('verification')=='editorial_verified' and isinstance(x.get('instagramReelOrder'),int) and
                   not isinstance(x.get('instagramReelOrder'),bool) and x['instagramReelOrder']>0),key=lambda x:x['instagramReelOrder'])
    ids=[x['id'] for x in actual]
    if ids!=expected or [x['instagramReelOrder'] for x in actual] != [1,2,3,4]:
        raise RuntimeError(f'WEB NO SINCRONIZADA. Reel={expected}; web={ids}')
    for i,item in enumerate(m['news']):
        if actual[i].get('title')!=item['title']:
            raise RuntimeError('Titular difiere para '+item['id'])
        if item['source']['url'] not in [x.get('url') for x in actual[i].get('sources',[])]:
            raise RuntimeError('Enlace fuente difiere para '+item['id'])
        if 'noticia-'+item['id'] not in html:
            raise RuntimeError('Noticia no visible en web para '+item['id'])
    return True


def main():
    p=argparse.ArgumentParser()
    p.add_argument('manifest');p.add_argument('--newsdb',default='noticias.json')
    p.add_argument('--site',default='https://colombia-al-dia.pages.dev/')
    args=p.parse_args()
    try:
        with urllib.request.urlopen(urllib.request.Request(args.site,headers={'User-Agent':'ORBIUNO release-check/1.0'}),timeout=20) as f:
            if f.status != 200:raise RuntimeError(f'Web devolvió HTTP {f.status}')
            html=f.read(5_000_000).decode('utf-8')
        check(args.manifest,args.newsdb,html)
    except Exception as e:
        p.exit(2,'BLOQUEO DE SINCRONIZACIÓN: '+str(e)+'\n')
    print('WEB Y REEL COINCIDEN: cuatro IDs, orden, titulares, fuentes y fichas visibles.')

if __name__=='__main__':main()
