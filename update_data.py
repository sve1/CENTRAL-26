#!/usr/bin/env python3
"""CENTRAL 26: coleta pública, sem chaves; não inventa votos."""
import json, re, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE="https://resultados.tse.jus.br/oficial/ele2026/6258/dados"
UFS="AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
HEAD={"User-Agent":"Central26/1.0 (+https://github.com/sve1/CENTRAL-26)","Accept":"application/json, application/xml, text/xml, */*"}
def fetch(url):
    req=urllib.request.Request(url,headers=HEAD)
    with urllib.request.urlopen(req,timeout=18) as res:
        return res.read()
def normalize(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize("NFKD",str(s or "")) if not unicodedata.combining(c)).upper()
def candidates(obj):
    # EA20 costuma publicar candidatos em abr[].cand; aceita outras estruturas reconhecidas.
    found=[]
    def walk(node,depth=0):
        if depth>12:return
        if isinstance(node,dict):
            if isinstance(node.get("cand"),list):found.extend(x for x in node["cand"] if isinstance(x,dict))
            for k,v in node.items():
                if k!="cand" and isinstance(v,(dict,list)):walk(v,depth+1)
        elif isinstance(node,list):
            for v in node:walk(v,depth+1)
    walk(obj)
    def find(term):
        return next((x for x in found if term in normalize(x.get("nmu") or x.get("nm") or x.get("nmcan"))),None)
    a,b=find("LULA"),find("FLAVIO")
    if a is None or b is None:return None
    try:
        av=int(a["vap"]);bv=int(b["vap"])
        if av<0 or bv<0 or av+bv<=0:return None
        return av,bv
    except (ValueError,TypeError,KeyError):return None
def save(name,data):
    (ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def collect():
    states=[];national=None
    for code in ["BR"]+UFS+["ZZ"]:
        lc=code.lower()
        url=f"{BASE}/{lc}/{lc}-c0001-e006258-u.json"
        try:
            d=json.loads(fetch(url)); votes=candidates(d)
            if votes:
                record={"code":code,"lula":votes[0],"flavio":votes[1],"updated":f"{d.get('dg','')} {d.get('hg','')}".strip(),"source":"TSE — EA20","sourceUrl":url,"partial":True}
                if code=="BR":national=record
                elif code!="ZZ":states.append(record)
        except Exception as exc:print(code,type(exc).__name__,str(exc)[:100])
        time.sleep(.15)
    # Nunca sobrescreve resultados válidos com uma coleta vazia.
    if states:save("results-br.json",states)
    if national:save("results-national.json",national)
    print("Estados válidos:",len(states),"Brasil:",bool(national))
def news():
    query=urllib.parse.quote('"eleições 2026" (apuração OR votação OR TSE) after:2026-10-24 before:2026-10-27')
    url=f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    try:
        root=ET.fromstring(fetch(url))
        items=[]
        for el in root.findall("./channel/item"):
            title=(el.findtext("title") or "").strip()
            link=(el.findtext("link") or "").strip()
            date=(el.findtext("pubDate") or "").strip()
            if not title or not link:continue
            # Filtro textual e temporal: notícias publicadas no dia da eleição.
            from email.utils import parsedate_to_datetime
            try:
                dt=parsedate_to_datetime(date).astimezone(timezone.utc)
                if dt.date().isoformat() not in ("2026-10-25","2026-10-26"):continue
            except Exception:continue
            if not re.search(r'eleiç|apuraç|votaç|tse|presiden',title,re.I):continue
            items.append({"title":title,"url":link,"published":dt.isoformat(),"source":"Google Notícias RSS"})
            if len(items)>=18:break
        if items:save("news.json",{"updated":datetime.now(timezone.utc).isoformat(),"items":items})
        print("Notícias:",len(items))
    except Exception as exc:print("RSS:",type(exc).__name__,str(exc)[:150])
if __name__=="__main__":
    collect()
    news()
