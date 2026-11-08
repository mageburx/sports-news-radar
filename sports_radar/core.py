"""Funções sem dependências para RSS, IDs estáveis e janela de 30 dias."""
from __future__ import annotations
import hashlib, html, re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

def utcnow():
    return datetime.now(timezone.utc)

def iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")

def date(value):
    if not value: return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (ValueError, TypeError): return None

def clean(value):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]*>"," ",value or ""))).strip()

def news_url(source):
    if source.get("kind")=="rss": return source["url"]
    return "https://news.google.com/rss/search?"+urlencode({"q":source["query"],"hl":source["hl"],"gl":source["gl"],"ceid":source["ceid"]})

def canonical(url):
    try:
        p=urlsplit(url)
        if p.scheme not in ("http","https") or not p.hostname: return ""
        q=urlencode([(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith("utm_") and k.lower() not in ("gclid","fbclid")])
        return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip("/") or "/",q,""))
    except ValueError: return ""

def identifier(section,publisher,title,url):
    norm=re.sub(r"[^\w]+"," ",(title or "").casefold()).strip()
    return hashlib.sha256(("\x1f".join((section,publisher.casefold(),norm or canonical(url)))).encode()).hexdigest()[:20]

def merge(existing,incoming,now=None):
    now=now or utcnow()
    byid={a["id"]:a for a in existing if a.get("id")}
    for a in incoming:
        if a["id"] in byid:
            prev=byid[a["id"]]
            prev["official"]=prev.get("official",False) or a.get("official",False)
        else: byid[a["id"]]=a
    lower,upper=now-timedelta(days=30),now+timedelta(hours=3)
    return sorted((a for a in byid.values() if (d:=date(a.get("published_at"))) and lower<=d<=upper),key=lambda a:a["published_at"],reverse=True)
