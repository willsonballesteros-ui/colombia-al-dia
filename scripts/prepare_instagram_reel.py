"""Validate the public site and immutable video before handing an edition to Meta."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

SITE = "https://colombia-al-dia.pages.dev"


def download(url):
    for attempt in range(3):
        try:
            with urlopen(url, timeout=30) as response:
                return response.read()
        except HTTPError as error:
            if error.code not in {408, 429, 500, 502, 503, 504} or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def caption_for(manifest, site):
    sources = manifest["sources"]
    ids = [source["id"] for source in sources]
    photos = {
        photo["newsId"] for photo in manifest["photos"]
        if photo["credit"] and photo["license"]
        and urlsplit(photo["sourceUrl"]).scheme == "https"
    }
    if len(ids) != 5 or len(set(ids)) != 5 or set(ids) != photos:
        raise ValueError("La edición requiere cinco fotografías con procedencia, licencia y crédito")

    notes = [
        note for note in site["news"]
        if note.get("date") == manifest["date"]
        and note.get("editionSlot") == manifest["slot"]
        and note.get("verification") == "editorial_verified"
    ]
    notes.sort(key=lambda note: note.get("instagramReelOrder", note.get("priority", 999)))
    public_sources = [
        (note["id"], note["title"], note["sources"][0]["url"]) for note in notes
    ]
    if public_sources != [(s["id"], s["title"], s["url"]) for s in sources]:
        raise ValueError("El sitio público y el Reel difieren en noticias, orden o fuentes")

    return build_caption(manifest)


def build_caption(manifest):
    sources = manifest["sources"]
    lines = [f"ORBIUNO | {manifest['date']} · {manifest['slot']}", ""]
    for index, source in enumerate(sources, 1):
        title = " ".join(source["title"].split())
        lines.extend([f"{index}. {title}", source["url"]])
    lines.extend(["", "👇 Síguenos en colombia-al-dia.pages.dev y escucha en voz alta la noticia que más te interese. Enlace en el perfil."])
    return "\n".join(lines)


def main():
    directory = Path(os.environ["EDITION_DIR"])
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if sys.argv[1:] == ["--caption-only"]:
        (directory / "descripcion_instagram.txt").write_text(
            build_caption(manifest) + "\n", encoding="utf-8"
        )
        return
    site = json.loads(download(f"{SITE}/noticias.json"))
    caption = caption_for(manifest, site)
    video_url = (
        "https://raw.githubusercontent.com/"
        f"{os.environ['GITHUB_REPOSITORY']}/{os.environ['ARCHIVE_SHA']}/{os.environ['ARCHIVE_PATH']}"
    )
    if hashlib.sha256(download(video_url)).hexdigest() != manifest["sha256"]:
        raise ValueError("El MP4 público no corresponde al manifiesto")
    edition_key = f"ORBIUNO-{manifest['date']}-{manifest['slot'].replace(':', '')}"
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"video_url={video_url}\nedition_key={edition_key}\n")
        output.write(f"caption<<ORBIUNO_CAPTION\n{caption}\nORBIUNO_CAPTION\n")


if __name__ == "__main__":
    main()
