#!/usr/bin/env python3
"""Validaciones esenciales: no aceptar links falsos, noticias duplicadas o etiquetas engañosas."""
import json
import sys
from datetime import date
from urllib.parse import urlsplit


def check(data):
    assert isinstance(data, dict) and isinstance(data.get('news'), list)
    assert data.get('editionDate'), 'No debe desaparecer la última edición verificada'
    seen = set()
    for x in data['news']:
        assert x.get('id') not in seen, f"ID repetido: {x.get('id')}"
        seen.add(x.get('id'))
        assert date.fromisoformat(x['date'])
        assert len(x.get('title', '')) >= 10
        assert isinstance(x.get('sources'), list) and x['sources']
        for s in x['sources']:
            u = urlsplit(s['url'])
            assert u.scheme == 'https' and u.netloc, f"URL de fuente no segura: {s['url']}"
        if x.get('verification') == 'source_only':
            assert 'Pendiente' in x['level'], 'La importación automática jamás equivale a noticia editorialmente verificada'
    return True

if __name__ == '__main__':
    f = sys.argv[1] if len(sys.argv) > 1 else 'noticias.json'
    check(json.load(open(f, encoding='utf-8')))
    print('JSON válido, %s entradas' % len(json.load(open(f, encoding='utf-8'))['news']))
