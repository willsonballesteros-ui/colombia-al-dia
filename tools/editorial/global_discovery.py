#!/usr/bin/env python3
"""Descubrimiento internacional para ORBIUNO y MyCar. Nunca publica candidatos."""
from __future__ import annotations
import argparse
import html
import json
import math
import re
import unittest
import unicodedata
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MAX_AGE = 48
MAX_BYTES = 2_000_000
MOTOR = (
    ("Motor1", "https://www.motor1.com/", "https://www.motor1.com/rss/news/all/"),
    ("InsideEVs", "https://insideevs.com/", "https://insideevs.com/rss/news/all/"),
    ("Electrek", "https://electrek.co/", "https://electrek.co/feed/"),
    ("Autocar", "https://www.autocar.co.uk/", ""),
    ("Car and Driver", "https://www.caranddriver.com/", ""),
    ("Carscoops", "https://www.carscoops.com/", "https://www.carscoops.com/feed/"),
    ("Auto Express", "https://www.autoexpress.co.uk/", ""),
    ("El Carro Colombiano", "https://www.elcarrocolombiano.com/", "https://www.elcarrocolombiano.com/feed/"),
    ("Autocosmos México", "https://noticias.autocosmos.com.mx/", ""),
    ("Autocosmos Colombia", "https://noticias.autocosmos.com.co/", ""),
    ("Stellantis Media", "https://www.media.stellantis.com/", ""),
    ("Toyota Global", "https://global.toyota/en/newsroom/", ""),
    ("Nissan Global", "https://global.nissannews.com/", ""),
    ("BMW PressClub", "https://www.press.bmwgroup.com/global/", ""),
    ("Hyundai News", "https://www.hyundainews.com/", ""),
)
FEEDS = {
    "BBC": "https://feeds.bbci.co.uk/news/rss.xml",
    "CNN": "https://rss.cnn.com/rss/edition.rss",
    "The Guardian": "https://www.theguardian.com/international/rss",
    "NASA": "https://www.nasa.gov/news-release/feed/",
    "MIT News": "https://news.mit.edu/rss/feed",
    "Variety": "https://variety.com/feed/",
    "Billboard": "https://www.billboard.com/feed/",
    "Euronews": "https://es.euronews.com/rss",
}
MOTOR_TERMS = re.compile(r"\b(auto(?:s|motive|movil(?:es)?)?|car(?:s)?|vehicle(?:s)?|vehiculo(?:s)?|ev|electric vehicle|suv|pickup|camioneta|automotriz|formula 1|f1|tesla|toyota|ford|renault|nissan|byd|hyundai|kia|bmw|volkswagen|porsche|honda|stellantis|mercedes|geely|volvo|ferrari)\b", re.I)
POSITIVE = re.compile(r"\b(advance|breakthrough|discover\w*|innov\w*|record|launch\w*|success\w*|win\w*|award\w*|recover\w*|avanc\w*|descubr\w*|logr\w*|premi\w*|lanz\w*|crec\w*|gan\w*|inaugur\w*|mejor\w*|recuper\w*)\b", re.I)
STOP = set("a al an and ante con de del el en for from in la las lo los of on or para por que se the to un una with y".split())


def normalized(s):
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in unicodedata.normalize("NFKD", html.unescape(str(s)).lower()) if not unicodedata.combining(c))))


def canonical(url):
    try:
        p = urlsplit(url)
        if p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in (443, None):
            return ""
        if p.hostname in {"localhost", "127.0.0.1", "news.google.com"} or len(p.path.strip("/")) < 3:
            return ""
        q = [(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith("utm_") and k.lower() not in {"fbclid","gclid"}]
        return urlunsplit(("https",p.netloc.lower(),p.path.rstrip("/"),urlencode(q),""))
    except ValueError:
        return ""


def same_domain(a, b):
    x, y = urlsplit(a).hostname or "", urlsplit(b).hostname or ""
    x, y = x.removeprefix("www."), y.removeprefix("www.")
    return x == y or x.endswith("." + y) or y.endswith("." + x)


def date_of(value):
    if not value:
        return None
    try:
        d = datetime.fromisoformat(value.replace("Z","+00:00"))
    except (TypeError, ValueError):
        try:
            d = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    return d.astimezone(timezone.utc) if d and d.tzinfo else None


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.feeds, self.scripts, self._parts = [], [], []
        self._json = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and "alternate" in (a.get("rel") or "").lower() and any(x in (a.get("type") or "").lower() for x in ("rss","atom")) and a.get("href"):
            self.feeds.append(a["href"])
        if tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self._json, self._parts = True, []

    def handle_data(self, data):
        if self._json:
            self._parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._json:
            self.scripts.append("".join(self._parts))
            self._json = False


def fetch(url):
    req = Request(url, headers={"User-Agent":"NewsroomDiscovery/1.0 (public RSS and structured headlines)", "Accept":"application/rss+xml, application/atom+xml, application/xml, text/html"})
    with urlopen(req, timeout=12) as response:
        raw = response.read(MAX_BYTES+1)
        if len(raw) > MAX_BYTES:
            raise ValueError("response too large")
        if response.status != 200 or not response.geturl().startswith("https://"):
            raise ValueError("invalid response")
        return raw, response.geturl()


def entries(raw):
    root = ET.fromstring(raw)
    def local(tag):
        return tag.rsplit("}",1)[-1]
    for idx, row in enumerate(x for x in root.iter() if local(x.tag) in {"item","entry"}):
        if idx >= 40:
            break
        parts = {}
        for c in row:
            name = local(c.tag)
            if name == "link" and c.attrib.get("rel","alternate") != "alternate":
                continue
            if name in {"title","link","pubDate","published","date","updated"} and name not in parts:
                parts[name] = "".join(c.itertext()).strip() or c.attrib.get("href","")
        yield parts.get("title",""), parts.get("link",""), parts.get("pubDate") or parts.get("published") or parts.get("date") or parts.get("updated"), idx


def article_nodes(obj):
    if isinstance(obj,list):
        for v in obj:
            yield from article_nodes(v)
    elif isinstance(obj,dict):
        types = obj.get("@type",[])
        types = [types] if isinstance(types,str) else types
        if any(t in {"NewsArticle","Article","ReportageNewsArticle","BlogPosting"} for t in types):
            u = obj.get("url") or obj.get("mainEntityOfPage") or ""
            if isinstance(u,dict):
                u = u.get("@id","")
            yield obj.get("headline",""),u,obj.get("datePublished"),0
        for v in obj.values():
            if isinstance(v,(dict,list)):
                yield from article_nodes(v)


def candidate(row, name, home, now, motor=False):
    title,url,raw_date,position = row
    if not isinstance(title,str) or not isinstance(url,str):
        return None
    title = " ".join(html.unescape(re.sub("<[^>]*>"," ",title)).split())
    url, dt = canonical(urljoin(home,url)), date_of(raw_date)
    if not url or not same_domain(url,home) or not dt or not 18 <= len(title) <= 230:
        return None
    age = (now-dt).total_seconds()/3600
    if age < 0 or age > MAX_AGE:
        return None
    return {"title":title,"url":url,"source":name,"publishedAt":dt.isoformat(),
            "ageHours":round(age,2),"position":position,"motor":bool(motor or MOTOR_TERMS.search(normalized(title))),
            "positiveSignal":bool(POSITIVE.search(normalized(title))),"verification":"source_only"}


def collect(source, now):
    name, home, supplied, motor = source
    found, failures = [], []
    feed_urls = [supplied] if supplied else []
    try:
        raw, final = fetch(home)
        page = Page()
        page.feed(raw.decode("utf-8",errors="replace"))
        feed_urls += [urljoin(final, u) for u in page.feeds if same_domain(urljoin(final,u),home)]
        for script in page.scripts:
            try:
                for row in article_nodes(json.loads(script)):
                    found.append(row)
            except (ValueError,TypeError,RecursionError):
                continue
    except (OSError,ValueError,TimeoutError) as exc:
        failures.append(type(exc).__name__)
    for url in list(dict.fromkeys(u for u in feed_urls if u and u.startswith("https://")))[:2]:
        try:
            raw,_ = fetch(url)
            found.extend(entries(raw))
        except (OSError,ValueError,ET.ParseError,TimeoutError) as exc:
            failures.append(type(exc).__name__)
    items = [c for row in found if (c:=candidate(row,name,home,now,motor))]
    return {"source":name,"candidates":items,"errors":failures}


def ranked(items, brand):
    # O(n log n + n*k), k <= 30. Exact URL deduplication, then near-title suppression.
    unique = {}
    for c in items:
        if brand == "mycar" and not c["motor"]:
            continue
        key = c["url"]
        if key not in unique or c["position"] < unique[key]["position"]:
            unique[key] = c
    pool = list(unique.values())
    def score(c):
        return round(55*math.exp(-c["ageHours"]/24) + 25/(1+c["position"]/5) + (20 if brand=="orbiuno" and c["positiveSignal"] else 0),2)
    selected, words = [], []
    for c in sorted(pool,key=lambda x:(-score(x),x["url"])):
        terms = set(normalized(c["title"]).split())-STOP
        if any(len(terms & t)/max(1,len(terms | t))>=.65 for t in words):
            continue
        words.append(terms)
        selected.append({**c,"attentionProxy":score(c),"rank":len(selected)+1,
                         "views":None,"requiresEditorialVerification":True,"requiresPhotoRights":True})
        if len(selected)==30:
            break
    return selected


def sources(path):
    rows=json.loads(path.read_text(encoding="utf-8"))["sources"]
    if len(rows)!=80 or len({r["url"] for r in rows})!=80:
        raise ValueError("Se requieren las 80 fuentes maestras sin repetir")
    return [(r["source"],r["url"],FEEDS.get(r["source"],""),False) for r in rows]+[(n,h,f,True) for n,h,f in MOTOR]


class Tests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,23,20,tzinfo=timezone.utc)
    def test_global(self):
        rows=[candidate(("Toyota launches electric SUV worldwide","https://example.org/auto/a","2026-11-23T19:00:00Z",0),"Example","https://example.org/",self.now,True),
              candidate(("Scientists discover new method for water purification","https://other.org/science/a","2026-11-23T18:00:00Z",1),"Other","https://other.org/",self.now)]
        self.assertEqual(len(ranked(rows,"orbiuno")),2)
        self.assertEqual(len(ranked(rows,"mycar")),1)
        self.assertIsNone(ranked(rows,"mycar")[0]["views"])
        self.assertEqual(len(ranked(rows+rows,"orbiuno")),2)
    def test_date_and_host(self):
        self.assertIsNone(candidate(("An interesting headline from elsewhere","https://bad.org/news/a","2026-11-23T19:00:00Z",0),"Example","https://example.org/",self.now))
        self.assertIsNone(candidate(("An old headline not suitable for today","https://example.org/news/a","2026-11-20T19:00:00Z",0),"Example","https://example.org/",self.now))
    def test_rss(self):
        xml=b'<rss><channel><item><title>Example headline</title><link>https://example.org/news/a</link><pubDate>Mon, 23 Nov 2026 19:00:00 GMT</pubDate></item></channel></rss>'
        self.assertEqual(list(entries(xml))[0][0],"Example headline")
    def test_catalog(self):
        self.assertEqual(len(sources(ROOT/"editorial/fuentes-maestras.json")),95)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sources",type=Path,default=ROOT/"editorial/fuentes-maestras.json")
    ap.add_argument("--out",type=Path,default=Path("dist/global-candidates.json"))
    ap.add_argument("--test",action="store_true")
    args=ap.parse_args()
    if args.test:
        return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful() else 1
    now=datetime.now(timezone.utc)
    catalog=sources(args.sources)
    with ThreadPoolExecutor(max_workers=10) as pool:
        records=list(pool.map(lambda x:collect(x,now),catalog))
    all_items=[c for r in records for c in r["candidates"]]
    report={"generatedAt":now.isoformat(),"method":"Recency and feed position proxy; no measured views or country quota",
            "publicationAuthorized":False,"sourcesAttempted":len(records),
            "sourcesWithCurrentCandidates":sum(bool(r["candidates"]) for r in records),
            "sourceResults":[{"source":r["source"],"count":len(r["candidates"]),"errors":r["errors"]} for r in records],
            "orbiuno":{"target":6,"candidates":ranked(all_items,"orbiuno")},
            "mycar":{"target":5,"candidates":ranked(all_items,"mycar")}}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(args.out)
    print(json.dumps({"sources":len(records),"usable":report["sourcesWithCurrentCandidates"],"orbiuno":len(report["orbiuno"]["candidates"]),"mycar":len(report["mycar"]["candidates"])}))
    return 0 if len(report["orbiuno"]["candidates"])>=6 and len(report["mycar"]["candidates"])>=5 else 2


if __name__=="__main__":
    raise SystemExit(main())
