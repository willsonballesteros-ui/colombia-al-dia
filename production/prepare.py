from pathlib import Path
from sys import path
import json, re
from edicion import edition_news, repo

path.insert(0, str(repo / "scripts"))
from validate_news import check

check({"editionDate": "2026-11-07", "news": edition_news()})
py = repo / "scripts/prepare_site.py"
old = py.read_text()
old = old.replace('("08:00","12:00","18:00")', '("08:00","12:00","18:00","20:00")')
old = old.replace('    sections=[]', '    if any(n.get("editionSlot") == "20:00" for n in published):\n        slots=(("20:00","8:00 p. m."),)+slots\n    sections=[]')
old = old.replace('"18:00":4}', '"18:00":4,"20:00":4}')
py.write_text(old)
index = repo / "index.html"
old = index.read_text()
old = old.replace("  const groups=slots.map", "  if(matching.some(x=>x.editionSlot==='20:00')) slots.unshift(['20:00','8:00 p. m.']);\n  const groups=slots.map")
old = old.replace("['08:00','12:00','18:00']", "['20:00','08:00','12:00','18:00']")
old = old.replace('08:00 · 12:00 · 18:00</a>', 'Ediciones y noticias</a>')
index.write_text(old)

feed = repo / "scripts/build_feed.py"
old = feed.read_text()
old = old.replace('    if len(news) != 10:', '    special = len(news) == 4 and all(item.get("editionSlot") == "20:00" for item in news)\n    if len(news) != 10 and not special:')
old = old.replace('Diez noticias contrastadas', 'Noticias contrastadas')
old = old.replace('day + "T06:00:00"', 'day + ("T20:00:00" if special else "T06:00:00")')
feed.write_text(old)
