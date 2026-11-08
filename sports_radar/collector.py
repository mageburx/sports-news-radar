"""Coleta RSS público de notícias, nunca conteúdos de artigos protegidos."""
from __future__ import annotations
import json, os, time
import xml.etree.ElementTree as ET
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urljoin
from bs4 import BeautifulSoup
import re
from datetime import datetime
import requests
from .core import utcnow,iso,date,clean,canonical,identifier,merge,news_url
from .quality import filter_nordic

ROOT=Path(__file__).resolve().parents[1]
SOURCES=ROOT/"config"/"sources.json"
NEWS=ROOT/"docs"/"data"/"news.json"
STATUS=ROOT/"docs"/"data"/"status.json"
UA="SportsNewsRadar/1.0 (+https://github.com/mageburx/sports-news-radar; public RSS metadata)"

def read(path,default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError,ValueError): return default

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(path)

def local(tag):
    return tag.rsplit("}",1)[-1].lower()

def entry_text(entry,*names):
    for e in entry:
        if local(e.tag) in names and e.text: return e.text.strip()
    return ""

def feed_parse(payload,source,now=None):
    now=now or utcnow()
    root=ET.fromstring(payload)
    items=[e for e in root.iter() if local(e.tag) in ("item","entry")]
    if not items and local(root.tag) not in ("rss","feed","rdf"): raise ValueError("Não é um RSS ou Atom")
    result=[]
    for e in items[:70]:
        p=next((child for child in e if local(child.tag)=="source"),None)
        pub=clean(entry_text(e,"source") or source["name"])
        orig=clean(entry_text(e,"title"))
        title=orig.removesuffix(" - "+pub).strip()
        link=entry_text(e,"link")
        if not link:
            node=next((child for child in e if local(child.tag)=="link" and child.get("href")),None)
            link=node.get("href","") if node is not None else ""
        link=canonical(link)
        if not title or not link: continue
        raw=entry_text(e,"pubdate","published","updated","date")
        try:
            published=parsedate_to_datetime(raw) if raw else now
            if published.tzinfo is None: published=published.replace(tzinfo=timezone.utc)
        except (ValueError,TypeError):
            published=date(raw) or now
        if not now-timedelta(days=30)<=published<=now+timedelta(hours=3): continue
        desc=clean(entry_text(e,"description","summary"))[:450]
        if desc.casefold()==orig.casefold(): desc=""
        domain=source.get("official_domain","")
        publisher_url=p.get("url","") if p is not None else ""
        src_host=urlsplit(p.get("url","")).hostname if p is not None else ""
        official=bool(domain and src_host and (src_host==domain or src_host.endswith("."+domain)))
        result.append({
           "id":identifier(source["section"],pub,title,link),"sport":source["sport"],
           "section":source["section"],"title":title[:300],"summary":desc,
           "publisher":pub[:120],"publisher_url":publisher_url,
           "source":source["name"],"source_id":source["id"],
           "url":link,"published_at":iso(published),"first_seen_at":iso(now),
           "official":official,"language":source["language"],"translated_title":"",
           "translation_status":"original","last_translation_attempt_at":""
        })
    return result


DANISH_MONTHS={"jan":1,"feb":2,"mar":3,"apr":4,"maj":5,"jun":6,
               "jul":7,"aug":8,"sep":9,"okt":10,"nov":11,"dec":12}

def listing_date(text):
    """Parse dates visibly printed in official Danish league news indexes."""
    match=re.search(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(20\d{2})(?!\d)",text)
    if match:
        try: return datetime(int(match[3]),int(match[2]),int(match[1]),tzinfo=timezone.utc)
        except ValueError: return None
    match=re.search(r"(?<!\w)(\d{1,2})\s+(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)\.?\s+(20\d{2})",text,re.I)
    if match:
        try: return datetime(int(match[3]),DANISH_MONTHS[match[2].lower()],int(match[1]),tzinfo=timezone.utc)
        except ValueError: return None
    return None

def listing_rows(html,source,now):
    """Extract only article metadata from official, publicly accessible listing cards."""
    soup=BeautifulSoup(html,"html.parser")
    host=(urlsplit(source["url"]).hostname or "").removeprefix("www.").lower()
    if host not in {"superliga.dk","tophaandbold.dk"}: raise ValueError("Not an allowed official host")
    found=[]
    seen=set()
    for anchor in soup.select("a[href]"):
        url=canonical(urljoin(source["url"],anchor.get("href","")))
        parts=urlsplit(url)
        path=parts.path
        if (parts.hostname or "").removeprefix("www.").lower()!=host: continue
        if host=="superliga.dk":
            if not path.startswith("/nyheder/"): continue
        elif not re.match(r"^/(?:herreligaen|kvindeligaen)-artikler/[^/]+",path):
            continue
        if url in seen: continue
        seen.add(url)
        heading=anchor.find(["h2","h3","h4"])
        raw=clean(heading.get_text(" ",strip=True)) if heading else clean(anchor.get_text(" ",strip=True))
        if not raw: continue
        text=clean(anchor.get_text(" ",strip=True))
        stamp=anchor.find("time")
        ts=stamp.get("datetime","") if stamp else ""
        pub=listing_date(ts) or listing_date(text)
        # Some sites put their date in a sibling of the anchor within the card.
        if not pub:
            parent=anchor.parent
            for _ in range(2):
                if parent is None: break
                nearby=clean(parent.get_text(" ",strip=True))
                if len(nearby)<700:
                    pub=listing_date(nearby)
                if pub: break
                parent=parent.parent
        if not pub: continue  # Never invent publication dates.
        if not now-timedelta(days=30)<=pub<=now+timedelta(hours=3): continue
        title=raw
        if not heading:
            title=re.sub(r"^\d{1,2}\s+(?:jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)\.?\s+","",title,flags=re.I)
            title=re.sub(r"\s+\d{1,2}\s+(?:jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)\.?\s+20\d{2}$","",title,flags=re.I)
            title=re.sub(r"\s+\d{1,2}\.\d{1,2}\.20\d{2}$","",title)
            if host=="tophaandbold.dk":
                title=re.sub(r"\s+(?:Betoro Herreligaen|Bambuni Kvindeligaen)$","",title,flags=re.I)
        title=clean(title)[:300]
        if len(title)<9: continue
        found.append({
          "id":identifier(source["section"],source["name"],title,url),
          "sport":source["sport"],"section":source["section"],"title":title,
          "summary":"","publisher":source["name"],"publisher_url":source["url"],
          "source":source["name"],"source_id":source["id"],"url":url,
          "published_at":iso(pub),"first_seen_at":iso(now),"official":True,
          "language":"da","translated_title":"","translated_summary":"",
          "translation_status":"original","last_translation_attempt_at":""
        })
    return found

def collect(session,source,now):
    url=source["url"] if source.get("kind")=="official_index" else news_url(source)
    res=session.get(url,timeout=(10,23),headers={"User-Agent":UA})
    res.raise_for_status()
    if source.get("kind")=="official_index":
        rows=listing_rows(res.content,source,now)
        if not rows: raise ValueError("No dated official news cards found; HTML may have changed")
        return rows
    return feed_parse(res.content,source,now)

def translation_target(article):
    """Keep existing EN→PT behaviour, but send Nordic-feed articles to English."""
    source=article.get("language","").lower().split("-")[0]
    return "en" if source=="da" else "pt" if source=="en" else None

def translation_source(text,source):
    """Some Danish news searches also return Norwegian titles; avoid labelling them Danish."""
    if source!="da": return source
    import re
    norwegian=r"\b(?:norge|norges|norsk|norske|kvinner|menn|kaptein|etter|lagoppstilling|uttak|fjellhammer|tidenes|skape|innledende|rullestolhåndball)\b"
    return "no" if re.search(norwegian,text,re.I) else "da"

def translate(session,text,lang,target):
    if lang==target: return text
    deepl=os.getenv("DEEPL_API_KEY","").strip()
    if deepl:
        source="NB" if lang=="no" else lang.upper()
        endpoint=os.getenv("DEEPL_API_URL","https://api-free.deepl.com/v2/translate")
        res=session.post(endpoint,data={
            "text":text[:450],"source_lang":source,
            "target_lang":"EN-GB" if target=="en" else "PT-PT"},
            headers={"Authorization":"DeepL-Auth-Key "+deepl},timeout=15)
        res.raise_for_status()
        result=res.json()["translations"][0]["text"].strip()
        if not result: raise ValueError("DeepL devolveu tradução vazia")
        return result
    params={"q":text[:450],"langpair":lang+"|"+("en" if target=="en" else "pt-PT")}
    if os.getenv("MYMEMORY_EMAIL"): params["de"]=os.environ["MYMEMORY_EMAIL"]
    res=session.get("https://api.mymemory.translated.net/get",params=params,timeout=14)
    res.raise_for_status()
    payload=res.json()
    if int(payload.get("responseStatus",0))!=200:
        raise ValueError("Quota ou serviço de tradução indisponível")
    result=(payload.get("responseData") or {}).get("translatedText","")
    if not result or result.upper().startswith("MYMEMORY WARNING"):
        raise ValueError("Tradução indisponível")
    return result.strip()

def translate_budget(session,items,status,now):
    """Prioritize Danish/Norwegian feed text to English, with quota-safe daily pacing."""
    budget=dict(status.get("translation_budget") or {})
    today=now.date().isoformat()
    if budget.get("date")!=today: budget={"date":today,"characters":0}
    budget["characters"]=int(budget.get("characters",0))
    success=failed=attempts=0
    remaining=max(0,4200-budget["characters"])
    # Preserve pre-existing English→Portuguese translations made before target tags existed.
    for old in items:
        if old.get("language")=="en" and old.get("translated_title") and not old.get("translated_lang"):
            old["translated_lang"]="pt"
    # Stable sort: Denmark-related items first; newest within each group.
    queue=sorted(items,key=lambda a:(a.get("language")!="da",))
    for a in queue:
        if attempts>=8 or failed>=2: break
        target=translation_target(a)
        if not target: continue
        source=a.get("language","").split("-")[0]
        # Old headlines were translated to Portuguese without a target-language tag.
        # Never display such a title as if it were the new English translation.
        if source=="da" and a.get("translated_lang")!="en":
            a["translated_title"]=""
            a["translated_summary"]=""
            a["translation_status"]="pending"
        if source=="en" and a.get("translated_title") and not a.get("translated_lang"):
            a["translated_lang"]="pt"
        if a.get("translated_title") and a.get("translated_lang")==target: continue
        prev=date(a.get("last_translation_attempt_at"))
        if prev and now-prev<timedelta(hours=12): continue
        title=a.get("title","")[:450]
        if not title: continue
        # RSS summaries often just repeat the headline plus publisher.
        summary=a.get("summary","")[:200] if source=="da" else ""
        if summary.lower().startswith(title.lower()[:max(10,len(title)-3)]):
            summary=""
        if len(title)>remaining: continue
        lang=translation_source(title,source)
        attempts+=1
        a["last_translation_attempt_at"]=iso(now)
        budget["characters"]+=len(title)
        remaining-=len(title)
        try:
            a["translated_title"]=translate(session,title,lang,target)
            a["translated_lang"]=target
            a["translation_status"]="translated"
            success+=1
            # Translate genuine RSS excerpts only while the daily limit allows.
            if summary and len(summary)<=remaining:
                budget["characters"]+=len(summary)
                remaining-=len(summary)
                try:
                    a["translated_summary"]=translate(session,summary,lang,target)
                except Exception:
                    a["translated_summary"]=""
            else:
                a["translated_summary"]=""
        except Exception as exc:
            a["translated_title"]=""
            a["translated_summary"]=""
            a["translation_status"]="unavailable"
            a["translation_error"]=type(exc).__name__
            failed+=1
        if not os.getenv("DEEPL_API_KEY"): time.sleep(.2)
    status["translation_budget"]=budget
    status["translations_this_run"]=success
    status["translations_failed_this_run"]=failed
    status["danish_english_translated"]=sum(
        a.get("language")=="da" and a.get("translated_lang")=="en"
        and bool(a.get("translated_title")) for a in items)
    status["danish_english_pending"]=sum(
        a.get("language")=="da" and not (
          a.get("translated_lang")=="en" and a.get("translated_title"))
        for a in items)

def main():
    now=utcnow()
    sources=read(SOURCES,[])
    if not sources: raise SystemExit("Sem fontes configuradas")
    past=read(NEWS,[])
    # Decode HTML entities left by translation providers in stored headlines.
    for old_article in past:
        if old_article.get("translated_title"):
            old_article["translated_title"]=clean(old_article["translated_title"])
        if old_article.get("translated_summary"):
            old_article["translated_summary"]=clean(old_article["translated_summary"])
    old=read(STATUS,{})
    past,discarded_archive=filter_nordic(past)
    known={a["id"] for a in past if a.get("id")}
    fresh=[]; health=[]; failures=0; discarded_feeds=[]

    with requests.Session() as s:
        for source in sources:
            report={"id":source["id"],"name":source["name"],"section":source["section"],"ok":False,"count":0}
            try:
                raw=collect(s,source,now)
                accepted,excluded=filter_nordic(raw)
                fresh.extend(accepted)
                discarded_feeds.extend(excluded)
                report.update(ok=True,count=len(accepted),raw_count=len(raw),excluded=len(excluded))
            except Exception as e:
                failures+=1
                report["error"]=type(e).__name__+": "+str(e)[:140]
                print("Fonte com erro:",source["id"],report["error"])
            health.append(report)
        articles=merge(past,fresh,now)
        status={"last_run":iso(now),"first_run":old.get("first_run") or iso(now),"sources":health,
           "sources_total":len(sources),"sources_ok":len(sources)-failures,
           "articles_total":len(articles),"added":sum(a["id"] not in known for a in articles),
           "translation_budget":old.get("translation_budget",{})}
        from collections import Counter
        reasons=Counter(x["reason"] for x in discarded_archive+discarded_feeds)
        status["nordic_filter"]={
            "removed_from_archive":len(discarded_archive),
            "excluded_on_fetch":len(discarded_feeds),
            "reasons":dict(reasons),
            "samples":(discarded_archive+discarded_feeds)[:12],
        }
        translate_budget(s,articles,status,now)
    save(NEWS,articles)
    save(STATUS,status)
    print("Artigos",len(articles),"novos",status["added"],"fontes",status["sources_ok"],"/",len(sources))
    return 1 if failures==len(sources) else 0

if __name__=="__main__":
    raise SystemExit(main())
