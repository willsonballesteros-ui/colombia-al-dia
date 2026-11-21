#!/usr/bin/env python3
"""Stage an isolated public Pages directory without changing original media.

Cloudflare Pages has a 25 MiB per-file limit. Oversized archive media remain
in the GitHub repository and Google Drive, but are excluded from /site.
Complexity: O(number of files + bytes copied).
"""
from __future__ import annotations
import argparse
import json
import shutil
import tempfile
from pathlib import Path

MAX_ASSET_BYTES = 25 * 1024 * 1024
PUBLIC_DIRS = ("media", "branding")
PUBLIC_ROOT = {
    "index.html", "noticias.json", "feed.xml", "audio-fix.js",
    "photo-viewer.js", "robots.txt", "sitemap.xml", "_headers", "_redirects",
}


def included_files(root: Path):
    for child in root.iterdir():
        if child.is_file() and not child.is_symlink() and (
            child.name in PUBLIC_ROOT or child.suffix == ".html"
        ):
            yield child
    for folder_name in PUBLIC_DIRS:
        folder = root / folder_name
        if folder.is_dir():
            for child in folder.rglob("*"):
                if child.is_file() and not child.is_symlink():
                    yield child


def build(root: Path, out: Path) -> dict:
    root, out = root.resolve(), out.resolve()
    if root == out or root not in out.parents:
        raise ValueError("Destino debe estar dentro del repositorio")
    for name in ("index.html", "noticias.json", "feed.xml", "audio-fix.js"):
        if not (root / name).is_file():
            raise ValueError("Falta componente público: " + name)
    news = json.loads((root / "noticias.json").read_text(encoding="utf-8"))
    if not isinstance(news.get("news"), list) or not news.get("editionDate"):
        raise ValueError("Noticias corruptas o sin edición")
    files = list(included_files(root))
    if len(files) > 20_000 or len(files) != len(set(files)):
        raise ValueError("Número de recursos inválido")
    selected, excluded = [], []
    for src in files:
        size = src.stat().st_size
        if size > MAX_ASSET_BYTES:
            excluded.append(src.relative_to(root).as_posix())
        else:
            selected.append(src)
    temp = Path(tempfile.mkdtemp(prefix=".orbiuno-pages-", dir=root))
    try:
        for src in selected:
            dest = temp / src.relative_to(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        if out.exists():
            shutil.rmtree(out)
        temp.rename(out)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    result = {"files": len(selected), "excluded": excluded}
    print("PAGES_STAGE_VERIFIED", json.dumps(result, ensure_ascii=False))
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--out", default="site")
    a = p.parse_args()
    build(Path(a.root), Path(a.out))


if __name__ == "__main__":
    main()
