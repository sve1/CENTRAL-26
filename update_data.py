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
    """Lê candidaturas presidenciais do EA20 (carg/agr/par/cand)."""
    found=[]
    for cargo in obj.get("carg",[]):
        if str(cargo.get("cd","1")) not in ("1","0001"):continue
        for agr in cargo.get("agr",[]):
            for par in agr.get("par",[]):
                found.extend(x for x in par.get("cand",[]) if isinstance(x,dict))
    if not found:return None
    def match(x,number,name):
        return str(x.get("n","")).strip()==number or name in normalize(x.get("nmu") or x.get("nm") or x.get("nmcan"))
    lula=next((x for x in found if match(x,"13","LULA")),None)
    flavio=next((x for x in found if match(x,"22","FLAVIO")),None)
    if lula is None or flavio is None:return None
    try:
        a=int(lula["vap"]);b=int(flavio["vap"])
        return (a,b) if a>=0 and b>=0 and a+b>0 else None
    except (TypeError,ValueError,KeyError):return None

def save(name,data):
    (ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def official_winner(data):
    """EA20 nacional: só confirma eleito com totalização final e status nominal."""
    base={"status":"pending","officialWinner":False,"winner":None,
          "source":"TSE","updated":f"{data.get('dg','')} {data.get('hg','')}".strip(),
          "sourceUrl":f"{BASE}/br/br-c0001-e006258-u.json",
          "totalization":data.get("and"),"mathematical":data.get("md")}
    if str(data.get("f","")).lower()!="o" or str(data.get("tf","")).lower()!="s" or str(data.get("and","")).lower()!="f":
        return base
    found=[]
    for cargo in data.get("carg",[]):
        if str(cargo.get("cd"))!="1":continue
        for agr in cargo.get("agr",[]):
            for party in agr.get("par",[]):
                found.extend(x for x in party.get("cand",[]) if isinstance(x,dict))
    winners=[x for x in found if normalize(x.get("st","")).strip() in ("ELEITO","ELEITA")]
    if len(winners)!=1:return base
    winner=winners[0]
    number=str(winner.get("n",""))
    if number not in ("13","22"):return base
    base.update(status="final",officialWinner=True,winner="lula" if number=="13" else "flavio",
                candidateName=winner.get("nmu"),votes=int(winner.get("vap","0")))
    return base

def collect():
    states=[];national=None
    for code in ["BR"]+UFS+["ZZ"]:
        lc=code.lower()
        url=f"{BASE}/{lc}/{lc}-c0001-e006258-u.json"
        try:
            d=json.loads(fetch(url)); votes=candidates(d)
            if votes:
                record={"code":code,"lula":votes[0],"flavio":votes[1],"updated":f"{d.get('dg','')} {d.get('hg','')}".strip(),"source":"TSE — EA20","sourceUrl":url,"partial":True}
                if code=="BR":
                    national=record
                    save("winner-official.json",official_winner(d))
                elif code!="ZZ":states.append(record)
        except Exception as exc:print(code,type(exc).__name__,str(exc)[:100])
        time.sleep(.15)
    # A confirmação só é emitida por status oficial no EA20 nacional.
    # Nunca sobrescreve resultados válidos com uma coleta vazia.
    save("results-br.json",states)
    if national:save("results-national.json",national)
    print("Estados válidos:",len(states),"Brasil:",bool(national))

# Correspondências conservadoras: somente jurisdições cujo país é inequívoco.
# Não usar nome do país como prova de que todas as seções da jurisdição estão nele.
CITY_COUNTRY={
"LISBOA":"PRT","PORTO":"PRT","FARO":"PRT","COIMBRA":"PRT",
"BOSTON":"USA","MIAMI":"USA","NOVA YORK":"USA","NEW YORK":"USA","ORLANDO":"USA","HOUSTON":"USA","LOS ANGELES":"USA","SAN FRANCISCO":"USA","CHICAGO":"USA","WASHINGTON":"USA","ATLANTA":"USA",
"TÓQUIO":"JPN","TOQUIO":"JPN","NAGOIA":"JPN","NAGÓIA":"JPN","HAMAMATSU":"JPN",
"SYDNEY":"AUS","SIDNEY":"AUS","MELBOURNE":"AUS","BRISBANE":"AUS","CANBERRA":"AUS",
"AUCKLAND":"NZL","WELLINGTON":"NZL",
"PEQUIM":"CHN","BEIJING":"CHN","XANGAI":"CHN","SHANGHAI":"CHN",
"SEUL":"KOR","SINGAPURA":"SGP","NOVA DELHI":"IND","MUMBAI":"IND",
"BERLIM":"DEU","BERLIN":"DEU","FRANKFURT":"DEU","MUNIQUE":"DEU","MUNCHEN":"DEU","HAMBURGO":"DEU",
"PARIS":"FRA","LYON":"FRA","MARSELHA":"FRA",
"LONDRES":"GBR","LONDON":"GBR","EDIMBURGO":"GBR",
"ROMA":"ITA","MILAO":"ITA","MILÃO":"ITA","NAPOLES":"ITA",
"MADRI":"ESP","MADRID":"ESP","BARCELONA":"ESP","SEVILHA":"ESP",
"BUENOS AIRES":"ARG","CORDOBA":"ARG","MENDOZA":"ARG",
"SANTIAGO":"CHL","MONTEVIDEU":"URY","MONTEVIDEO":"URY",
"TORONTO":"CAN","MONTREAL":"CAN","VANCOUVER":"CAN","OTTAWA":"CAN",
"ZURIQUE":"CHE","GENEBRA":"CHE","GENEVA":"CHE",
"AMSTERDA":"NLD","AMSTERDAM":"NLD",
"VIENA":"AUT","ESTOCOLMO":"SWE","OSLO":"NOR","COPENHAGUE":"DNK",
"TEL AVIV":"ISR","JERUSALEM":"ISR","JERUSALEM":"ISR",
}
CITY_COUNTRY={normalize(k):v for k,v in CITY_COUNTRY.items()}

def exterior():
    """EA12 lista localidades; EA20 por localidade. Ignora códigos não identificados."""
    config_urls=[
        f"https://resultados.tse.jus.br/oficial/ele2026/6258/config/mun-e006258-cm.json",
        
        "https://resultados.tse.jus.br/oficial/ele2026/6258/config/mun-e006258-cm.json",
        "https://resultados.tse.jus.br/oficial/ele2026/6258/dados/mun-e006258-cm.json",
    ]
    entries=[]
    for url in config_urls:
        try:
            obj=json.loads(fetch(url))
            def walk(node):
                if isinstance(node,dict):
                    name=node.get("nm") or node.get("nome") or node.get("nmmun") or node.get("nmu")
                    code=node.get("cd") or node.get("codigo") or node.get("cdmun") or node.get("cdi")
                    if name and code and str(code).isdigit() and len(str(code))<=5:entries.append((str(code).zfill(5),normalize(name)))
                    for val in node.values():
                        if isinstance(val,(dict,list)):walk(val)
                elif isinstance(node,list):
                    for v in node:walk(v)
            walk(obj)
            if entries:break
        except Exception as e:print("EA12",url,str(e)[:70])
    if not entries:
        save("results-world.json",[])
        save("results-world-status.json",{"status":"unavailable","updated":datetime.now(timezone.utc).isoformat(),"source":"TSE — Divulgação de Resultados","message":"Não foi possível confirmar resultados parciais oficiais por país na fonte do TSE. Nenhum país será colorido.","countries":0})
        print("Exterior: configuração EA12 indisponível; não gerar placares.")
        return
    grouped={};checked=set()
    for code,name in entries:
        country=CITY_COUNTRY.get(name)
        if not country or code in checked:continue
        checked.add(code)
        # EA20 da localidade: zz + código de município, sem inferir o país a partir do arquivo.
        url=f"{BASE}/zz/zz{code.zfill(5)}-c0001-e006258-u.json"
        try:
            data=json.loads(fetch(url));votes=candidates(data)
            if not votes:continue
            g=grouped.setdefault(country,{"code":country,"lula":0,"flavio":0,"updated":"","source":"TSE — EA20, localidades identificadas","partial":True,"localities":[]})
            g["lula"]+=votes[0];g["flavio"]+=votes[1]
            g["updated"]=f"{data.get('dg','')} {data.get('hg','')}".strip()
            g["localities"].append(name)
        except Exception as e:print("Exterior",code,str(e)[:80])
        time.sleep(.15)
    for g in grouped.values():
        g["coverage"]="Parcial oficial do TSE: somente localidades identificadas e verificadas; não representa necessariamente o total do país"
    save("results-world.json",list(grouped.values()))
    save("results-world-status.json",{"status":"partial_official" if grouped else "unavailable","updated":datetime.now(timezone.utc).isoformat(),"source":"TSE — Divulgação de Resultados","message":"Resultados parciais oficiais do TSE disponíveis para as localidades identificadas." if grouped else "Ainda não há resultados parciais oficiais do exterior disponíveis ou verificáveis nesta integração com o TSE.","countries":len(grouped)})
    print("Exterior: países com localidades verificadas:",len(grouped))

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
    exterior()
    news()
