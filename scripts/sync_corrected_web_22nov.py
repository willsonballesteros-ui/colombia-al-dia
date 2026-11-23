#!/usr/bin/env python3
"""Sincronizar páginas web con los Reels corregidos ya publicados. No llama Meta."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/"media/2026-11-22/correcciones-v2"
ORBIUNO="ORBIUNO_2026-11-22_1800_6_NOTICIAS_CORREGIDA_V2.mp4"
MYCAR="MYCAR_2026-11-22_1800_5_NOTICIAS_CORREGIDA_V2.mp4"
def main():
    for file in (ORBIUNO,MYCAR):
        if not (FOLDER/file).is_file():
            raise SystemExit("Falta MP4 corregido "+file)
    page=ROOT/"mycar-2026-11-22-1800.html"
    raw=page.read_text(encoding="utf-8")
    old="/media/2026-11-22/mycar-pm-5/MYCAR_22_NOV_2026_NOCHE_5_NOTICIAS.mp4"
    new="/media/2026-11-22/correcciones-v2/"+MYCAR
    if old not in raw and new not in raw:
        raise SystemExit("Página MyCar no contiene enlace a MP4 esperado")
    raw=raw.replace(old,new)
    raw=raw.replace("MYCAR Noticias 22 noviembre 2026 18:00",
                    "MYCAR Noticias 22 noviembre 2026 18:00 | edición corregida")
    page.write_text(raw,encoding="utf-8")
    # La portada de ORBIUNO muestra únicamente publicaciones del día.
    # Enlazar el Reel corregido dentro del menú del 22/11 sin añadir banners
    # históricos que persistan de un día al siguiente.
    template=ROOT/"scripts/prepare_site.py"
    source=template.read_text(encoding="utf-8")
    target='    if not badges:\n'
    insertion=(
        '    if day == "2026-11-22" and (ROOT / "media/2026-11-22/correcciones-v2/'
        +ORBIUNO+'").is_file():\n'
        '        badges += (\'<p style="margin:9px 0 0;font-size:14px">\'\n'
        '                   \'<a style="color:#a3f7ed" href="./media/2026-11-22/correcciones-v2/'
        +ORBIUNO+'">\'\n'
        '                   \'▶ Ver video ORBIUNO corregido de las 6:00 p. m.</a></p>\')\n'
    )
    if insertion not in source:
        if target not in source:
            raise SystemExit("No se encuentra sección de noticias del día")
        source=source.replace(target,insertion+target,1)
        template.write_text(source,encoding="utf-8")
    # Generar el índice a partir de sus datos sin cambiar los artículos.
    from scripts.prepare_site import main as update_main
    update_main()
    print("CORRECTED_WEB_SYNC_OK")
if __name__=="__main__":
    main()
