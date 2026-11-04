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
        # La narración ampliada es síntesis propia y nunca una copia del medio.
        if x.get('audioFullTextEs'):
            assert x.get('verification') in ('editorial_verified', 'editorial_superseded'), 'Audio requiere revisión previa o archivo editorial sustituido'
            assert x.get('sourceLanguage') in ('en', 'es'), 'Idioma de origen sin identificar'
            assert x.get('audioIsFullPublisherArticle') is False, 'Prohibido almacenar artículo íntegro de prensa como audio propio'
            assert len(x['audioFullTextEs']) > len(x.get('executiveSummary') or ''), 'Audio ampliado demasiado corto'
        if x.get('audioFullTextEn'):
            assert x.get('englishAudioRightsVerified') is True, 'No reproducir texto extranjero sin derechos comprobados'
        # Leer íntegramente un artículo de un tercero exige autorización
        # de reproducción y, si se traduce del inglés, permiso de traducción.
        if x.get('fullArticleTextEs') or x.get('fullArticleRightsVerified'):
            assert x.get('verification') == 'editorial_verified', 'Artículo completo requiere edición'
            assert isinstance(x.get('fullArticleTextEs'), str) and len(x['fullArticleTextEs'].strip()) >= 300, 'Texto completo insuficiente'
            assert x.get('fullArticleRightsVerified') is True, 'No hay autorización de reproducción del artículo íntegro'
            assert x.get('fullArticleIsVerbatimSource') is True, 'El modo completo exige el texto original autorizado'
            assert x.get('fullArticleLicense'), 'Falta licencia documentada'
            assert x.get('fullArticleSourceUrl') in [s['url'] for s in x['sources']], 'No coincide la fuente del artículo completo'
            if x.get('sourceLanguage') == 'en':
                assert x.get('fullArticleTranslationAuthorized') is True, 'Traducción íntegra no autorizada'
        # Texto completo redactado en ORBIUNO, con fuentes y revisión
        # verificables. No equivale a transcribir íntegramente el periódico.
        if x.get('originalArticleTextEs') or x.get('originalArticleReviewed'):
            assert x.get('verification') == 'editorial_verified', 'Artículo ORBIUNO necesita noticia verificada'
            assert x.get('originalArticleByline') == 'Redacción ORBIUNO', 'Autor propio no identificado'
            assert isinstance(x.get('originalArticleTextEs'), str) and len(x['originalArticleTextEs'].strip()) >= 1000, 'Artículo ORBIUNO insuficiente'
            assert isinstance(x.get('originalArticleSourceUrls'), list) and x['originalArticleSourceUrls'], 'Reportaje sin fuentes'
            assert all(url in [s['url'] for s in x['sources']] for url in x['originalArticleSourceUrls']), 'Fuente de artículo propio no coincide'
            assert x.get('originalArticleIsPublisherVerbatim') is False, 'Prohibido transcribir artículo ajeno como propio'
            if x.get('originalArticleReviewed') is not True:
                assert x.get('originalArticleReviewed') is False, 'Estado de revisión desconocido'
                assert x.get('originalArticleReviewStatus') == 'pendiente_validacion_editorial', 'Borrador debe quedar pendiente'
            else:
                assert x.get('originalArticleReviewStatus') != 'pendiente_validacion_editorial', 'No publicar texto pendiente como completo'
        # Protección editorial: nada generado ni sin atribución documental.
        if x.get('imageUrl') or x.get('imageType'):
            assert x.get('imageType') in {
                'official_photo', 'licensed_press_photo', 'official_document'
            }, f"Tipo de imagen no editorial: {x.get('id')}"
            assert x.get('imageRightsVerified') is True, 'Derechos de imagen sin verificar'
            assert x.get('imageCredit'), 'Imagen sin crédito'
            assert x.get('imageLicense'), 'Imagen sin licencia'
            assert str(x.get('imageSourceUrl', '')).startswith('https://'), 'Sin enlace de procedencia'
            assert (str(x.get('imageUrl','')).startswith('https://') or
                    str(x.get('imageUrl','')).startswith('./media/')), 'Ruta de imagen no válida'
        if x.get('verification') == 'source_only':
            assert 'Pendiente' in x['level'], 'La importación automática jamás equivale a noticia editorialmente verificada'
    return True

if __name__ == '__main__':
    f = sys.argv[1] if len(sys.argv) > 1 else 'noticias.json'
    check(json.load(open(f, encoding='utf-8')))
    print('JSON válido, %s entradas' % len(json.load(open(f, encoding='utf-8'))['news']))
