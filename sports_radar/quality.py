"""Filtros conservadores para campeonatos dinamarqueses (evitam falsos positivos noruegueses).

Uma pesquisa Google News com hl=da não confirma o idioma, país ou competição
do artigo. O classificador usa título e domínio da publicação original.
Não processa texto completo nem consulta paywalls.
"""
import re
from urllib.parse import urlsplit

NORDIC_SECTIONS = {"superliga-dinamarquesa", "campeonato-dinamarques"}

NORWEGIAN_PUBLISHERS = re.compile(
    r"(?:sportsidioten(?:\.no)?|nettavisen|norges\s+håndballforbund|"
    r"norsk\s+topphåndball|handball\.no|vg\.no|dagbladet|nrk(?:\.no)?)", re.I)
NORWEGIAN_LANGUAGE = re.compile(
    r"\b(?:håndball|kvinner|menn|etter|kaptein|lagoppstilling|"
    r"uttak|innledende|rullestolhåndball|kvalifisering|tidenes|"
    r"skape|norsk|norges|fjellhammer|elverum|iceserien|"
    r"veldig|gledelig|sinnssykt|ære)\b", re.I)
NON_DOMESTIC = re.compile(
    r"\b(?:uefa|ehf|ihf|fifa|champions[\s-]+league|"
    r"conference[\s-]+league|europa[\s-]+league|european[\s-]+league|"
    r"europapokal|world[\s-]+cup|world[\s-]+championship|"
    r"europamesterskab|landskamp|landshold|landslaget|"
    r"euro[\s-]+cup|em[\s-]+kvalifisering|nm[\s-]+rullestol)\b", re.I)
FOOTBALL_LEAGUE = re.compile(r"\b(?:3f\s+superliga(?:en)?|superliga(?:en)?)\b", re.I)
HANDBALL_LEAGUE = re.compile(
    r"\b(?:betoro|bambuni|herreligaen|kvindeligaen|"
    r"herrehåndboldligaen|kvindehåndboldligaen|håndboldligaen|"
    r"håndboldliga)\b", re.I)
NOT_TOP_DIVISION = re.compile(
    r"\b(?:1\.\s*division|2\.\s*division|u1[579]|u2[01]|"
    r"pokalturnering|final4\s+pokal)\b", re.I)

FOOTBALL_TEAMS = (
    r"f\.?\s*c\.?\s*københavn", r"brøndby(?:\s+if)?", r"f\.?\s*c\.?\s*midtjylland",
    r"randers(?:\s+fc)?", r"fc\s+nordsjælland", r"nordsjælland",
    r"agf", r"aarhus\s+gf", r"silkeborg", r"viborg",
    r"sønderjyske", r"lyngby", r"ob", r"odense\s+boldklub",
    r"ac\s+horsens", r"fc\s+fredericia", r"vejle",
)
HANDBALL_TEAMS = (
    r"aalborg", r"gog", r"skjern", r"odense(?:\s+håndbold)?",
    r"team\s+esbjerg", r"ikast", r"nykøbing", r"nf[h]?",
    r"bjerringbro", r"silkeborg", r"ringkøbing", r"viborg\s+hk",
    r"mors.thy", r"tms\s+ringsted", r"ribe.esbjerg",
    r"høj(?:\s+elite)?", r"horsens", r"skanderborg",
    r"sønderjyske(?:\s+kvindehåndbold)?",
)
HANDBALL_CONTEXT = re.compile(
    r"\b(?:håndbold|håndboldklub|målvogter|håndboldspiller|"
    r"spiller|træner|kontrakt|forlænger|sejr|vinder|"
    r"taber|slår|mesterskab|rundens\s+hold|match\s+of\s+the\s+round)\b", re.I)
FOOTBALL_CONTEXT = re.compile(
    r"\b(?:fodbold|football|spiller|træner|kamp|sejr|"
    r"vinder|taber|mål|resultat|runde|transfer|optakt|"
    r"preview|slår)\b", re.I)

def publisher_hostname(article):
    raw=article.get("publisher_url","") or article.get("publisher_domain","")
    if not raw: return ""
    if "://" not in raw: raw="https://"+raw
    try: return (urlsplit(raw).hostname or "").lower().removeprefix("www.")
    except ValueError: return ""

def _clubs(text,patterns):
    return sum(bool(re.search(r"(?<!\w)(?:"+p+r")(?!\w)",text,re.I)) for p in patterns)

def nordic_rejection(article):
    """None=aceitar; caso contrário devolve uma razão estável de exclusão."""
    section=article.get("section","")
    if section not in NORDIC_SECTIONS: return None
    title=(article.get("title") or "").strip()
    publisher=article.get("publisher") or ""
    domain=publisher_hostname(article)

    if (domain.endswith(".no") or NORWEGIAN_PUBLISHERS.search(publisher)
        or NORWEGIAN_LANGUAGE.search(title)):
        return "origem_norueguesa"
    # "TV 2 Play" also exists in Norway. Do not trust ambiguous legacy items.
    if publisher.strip().casefold()=="tv 2 play" and not domain:
        return "origem_indeterminada"
    if NON_DOMESTIC.search(title):
        return "outra_competicao"

    if section=="superliga-dinamarquesa":
        if FOOTBALL_LEAGUE.search(title): return None
        if _clubs(title,FOOTBALL_TEAMS)>=2: return None
        if _clubs(title,FOOTBALL_TEAMS)>=1 and FOOTBALL_CONTEXT.search(title):
            return None
        return "sem_ligacao_a_liga"

    if NOT_TOP_DIVISION.search(title): return "outra_competicao"
    if HANDBALL_LEAGUE.search(title): return None
    if domain in ("tophaandbold.dk","danskhaandbold.dk"):
        if _clubs(title,HANDBALL_TEAMS)>=1 or HANDBALL_CONTEXT.search(title):
            return None
    if _clubs(title,HANDBALL_TEAMS)>=2: return None
    if _clubs(title,HANDBALL_TEAMS)>=1 and HANDBALL_CONTEXT.search(title):
        return None
    return "sem_ligacao_a_liga"

def filter_nordic(items):
    kept=[]; removed=[]
    for item in items:
        reason=nordic_rejection(item)
        if reason:
            removed.append({"id":item.get("id",""),"reason":reason,
                            "title":item.get("title","")[:150]})
        else:
            kept.append(item)
    return kept,removed
