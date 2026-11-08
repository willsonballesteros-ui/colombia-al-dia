"""Lógica común de una edición ORBIUNO: validación, guion de narración y pie de foto.

Fuente de datos: noticias.json -> clave "editions" (ver editions/_plantilla-*.json) que
referencia noticias existentes por id. No crea otra base de datos.
"""
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

EDITION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(0800|1200|1800)$")
ROLES = ["principal", "principal", "breve", "breve"]
WORDS = {"principal": (35, 60), "breve": (18, 35)}
SLOT_PHRASE = {"0800": "Edición de las ocho de la mañana",
               "1200": "Edición del mediodía",
               "1800": "Edición de las seis de la tarde"}
SLOT_LABEL = {"0800": "8:00 a. m.", "1200": "12:00 m.", "1800": "6:00 p. m."}
DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]
NUM = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
       "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
       "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
       "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho",
       "veintinueve", "treinta", "treinta y uno"]
REQUIRED_NEWS = ["id", "date", "title", "category", "sources", "verification",
                 "reelShort", "reelNarrationEs"]
WEB_BASE = "https://colombia-al-dia.pages.dev"


class EditionError(Exception):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


def words(text):
    return len(re.findall(r"\w+", text or ""))


def long_date(iso):
    d = date.fromisoformat(iso)
    day = "primero" if d.day == 1 else NUM[d.day]
    return f"{DAYS[d.weekday()]} {day} de {MONTHS[d.month - 1]}"


def direct_article(url):
    u = urlsplit(url or "")
    if u.scheme != "https" or not u.netloc:
        return False
    if u.netloc.endswith("news.google.com"):
        return False  # redirección de agregador, no artículo original
    return len(u.path.strip("/")) >= 8 or bool(u.query)


def validate_edition(data, edition_id, require_approved=True):
    """Devuelve (edición, [4 noticias en orden]) o lanza EditionError con TODOS los problemas."""
    problems = []
    m = EDITION_RE.match(edition_id or "")
    if not m:
        raise EditionError([f"editionId inválido: {edition_id!r}"])
    day, slot = m.group(1), m.group(2)
    ed = next((e for e in data.get("editions", []) if e.get("editionId") == edition_id), None)
    if ed is None:
        raise EditionError([f"No existe la edición {edition_id} en noticias.json"])
    if ed.get("date") != day:
        problems.append("date de la edición no coincide con editionId")
    ids = ed.get("newsIds") or []
    if len(ids) != 4 or len(set(ids)) != 4:
        problems.append(f"se requieren exactamente 4 noticias distintas (hay {len(ids)})")
    if ed.get("roles") != ROLES:
        problems.append(f"roles deben ser exactamente {ROLES} en ese orden")
    by_id = {n.get("id"): n for n in data.get("news", [])}
    news = []
    for i, nid in enumerate(ids):
        n = by_id.get(nid)
        if n is None:
            problems.append(f"noticia inexistente: {nid}")
            continue
        news.append(n)
        role = ROLES[i] if i < 4 else "breve"
        for k in REQUIRED_NEWS:
            if not n.get(k):
                problems.append(f"{nid}: falta {k}")
        if n.get("date") != day:
            problems.append(f"{nid}: fecha {n.get('date')} distinta de la edición {day}")
        if n.get("verification") != "editorial_verified":
            problems.append(f"{nid}: no está editorial_verified")
        srcs = n.get("sources") or []
        if not srcs or not srcs[0].get("name") or not direct_article(srcs[0].get("url")):
            problems.append(f"{nid}: sin enlace directo al artículo original")
        lo, hi = WORDS[role]
        w = words(n.get("reelNarrationEs"))
        if n.get("reelNarrationEs") and not lo <= w <= hi:
            problems.append(f"{nid}: narración de {w} palabras; {role} exige {lo}-{hi}")
        src_name = (srcs[0].get("name") if srcs else "") or ""
        if src_name and n.get("reelNarrationEs") and src_name.lower() not in n["reelNarrationEs"].lower():
            problems.append(f"{nid}: la narración debe pronunciar la fuente «{src_name}»")
        if "TODO" in json.dumps(n, ensure_ascii=False):
            problems.append(f"{nid}: contiene marcadores TODO")
    if require_approved:
        rv = ed.get("review") or {}
        if rv.get("status") != "approved" or not rv.get("by") or not rv.get("at"):
            problems.append("edición sin aprobación humana (review.status/by/at)")
    if problems:
        raise EditionError(problems)
    return ed, news


def narration_segments(ed, news):
    """Seis textos: introducción, 4 noticias, cierre. Cada uno se sintetiza por separado."""
    slot = ed["editionId"][-4:]
    shorts = [n["reelShort"].strip().rstrip(".") for n in news]
    intro = (f"Orbiuno, las noticias de Colombia y el mundo. {long_date(ed['date']).capitalize()}. "
             f"{SLOT_PHRASE[slot]}. Hoy: {shorts[0]}; {shorts[1]}; {shorts[2]}; y {shorts[3]}.")
    body = [n["reelNarrationEs"].strip() for n in news]
    outro = "Escucha cada noticia en la web: enlace del perfil. Orbiuno, las noticias más importantes, en un solo lugar."
    return [intro] + body + [outro]


def build_caption(ed, news, limit=2200):
    slot = ed["editionId"][-4:]
    lines = [f"ORBIUNO · {long_date(ed['date']).capitalize()} · {SLOT_LABEL[slot]}", ""]
    for i, n in enumerate(news, 1):
        lines.append(f"{i}. {n['title']} (Fuente: {n['sources'][0]['name']})")
    lines += ["", "Escucha cada noticia en la web: enlace del perfil @resumen.noticias", f"[ORB-{ed['editionId']}]"]
    text = "\n".join(lines)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def web_ready(n):
    """Regla WEB PRIMERO: reportaje propio de 3-4 párrafos, firmado y revisado."""
    problems = []
    paras = [p for p in re.split(r"\n\s*\n|\n", n.get("originalArticleTextEs") or "") if p.strip()]
    if len(paras) < 3:
        problems.append(f"{n.get('id')}: reportaje propio con {len(paras)} párrafos (mínimo 3)")
    if not n.get("originalArticleByline"):
        problems.append(f"{n.get('id')}: falta originalArticleByline")
    if n.get("originalArticleReviewed") is not True:
        problems.append(f"{n.get('id')}: originalArticleReviewed no es true")
    return problems


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
