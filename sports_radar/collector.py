"""Coleta RSS público de notícias, nunca conteúdos de artigos protegidos."""
from __future__ import annotations
import json, os, time
import xml.etree.ElementTree as ET
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit
import requests
from .core import utcnow,iso,date,clean,canonical,identifier,merge,news_url

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
        src_host=urlsplit(p.get("url","")).hostname if p is not None else ""
        official=bool(domain and src_host and (src_host==domain or src_host.endswith("."+domain)))
        result.append({
           "id":identifier(source["section"],pub,title,link),"sport":source["sport"],
           "section":source["section"],"title":title[:300],"summary":desc,
           "publisher":pub[:120],"source":source["name"],"source_id":source["id"],
           "url":link,"published_at":iso(published),"first_seen_at":iso(now),
           "official":official,"language":source["language"],"translated_title":"",
           "translation_status":"original","last_translation_attempt_at":""
        })
    return result

def collect(session,source,now):
    res=session.get(news_url(source),timeout=(10,23),headers={"User-Agent":UA})
    res.raise_for_status()
    return feed_parse(res.content,source,now)

def translate(session,text,lang):
    if lang=="pt": return text
    deepl=os.getenv("DEEPL_API_KEY","").strip()
    if deepl:
        res=session.post("https://api-free.deepl.com/v2/translate",data={"text":text,"source_lang":lang.upper(),"target_lang":"PT-PT"},
          headers={"Authorization":"DeepL-Auth-Key "+deepl},timeout=15)
        res.raise_for_status()
        return res.json()["translations"][0]["text"].strip()
    params={"q":text[:450],"langpair":lang+"|pt-PT"}
    if os.getenv("MYMEMORY_EMAIL"): params["de"]=os.environ["MYMEMORY_EMAIL"]
    res=session.get("https://api.mymemory.translated.net/get",params=params,timeout=14)
    res.raise_for_status()
    payload=res.json()
    if int(payload.get("responseStatus",0))!=200: raise ValueError("Quota ou serviço de tradução indisponível")
    target=(payload.get("responseData") or {}).get("translatedText","")
    if not target or target.upper().startswith("MYMEMORY WARNING"): raise ValueError("Tradução indisponível")
    return target.strip()

def translate_budget(session,items,status,now):
    budget=dict(status.get("translation_budget") or {})
    today=now.date().isoformat()
    if budget.get("date")!=today: budget={"date":today,"characters":0}
    success=failed=attempts=0
    for a in items:
        if attempts>=4 or failed>=2: break
        if a.get("translated_title") or a.get("language")=="pt": continue
        prev=date(a.get("last_translation_attempt_at"))
        if prev and now-prev<timedelta(hours=24): continue
        n=len(a["title"])
        if budget["characters"]+n>3000: continue
        budget["characters"]+=n
        attempts+=1
        a["last_translation_attempt_at"]=iso(now)
        try:
            a["translated_title"]=translate(session,a["title"],a["language"])
            a["translation_status"]="translated"
            success+=1
        except Exception:
            a["translation_status"]="unavailable"
            failed+=1
        if not os.getenv("DEEPL_API_KEY"): time.sleep(.2)
    status["translation_budget"]=budget
    status["translations_this_run"]=success

def main():
    now=utcnow()
    sources=read(SOURCES,[])
    if not sources: raise SystemExit("Sem fontes configuradas")
    past=read(NEWS,[])
    old=read(STATUS,{})
    known={a["id"] for a in past if a.get("id")}
    fresh=[]; health=[]; failures=0
    with requests.Session() as s:
        for source in sources:
            report={"id":source["id"],"name":source["name"],"section":source["section"],"ok":False,"count":0}
            try:
                new=collect(s,source,now)
                fresh.extend(new)
                report.update(ok=True,count=len(new))
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
        translate_budget(s,articles,status,now)
    save(NEWS,articles)
    save(STATUS,status)
    print("Artigos",len(articles),"novos",status["added"],"fontes",status["sources_ok"],"/",len(sources))
    return 1 if failures==len(sources) else 0

if __name__=="__main__":
    raise SystemExit(main())
