"""Kentucky-first public opportunity monitor. No unsolicited outreach."""
import os, re, json, hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin
from pathlib import Path
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

UA = "HNLOpportunityRadar/1.0 (public project discovery; no outreach)"
INDEXES = [
 ("CABL Fiber Splicing","https://www.cabl.com/jobs/fiber-splicing/?noscript=y"),
 ("CABL Aerial","https://www.cabl.com/jobs/aerial-construction/?noscript=y"),
 ("CABL Underground","https://www.cabl.com/jobs/underground-construction/?noscript=y"),
 ("CABL Drop Bury","https://www.cabl.com/jobs/drop-bury/?noscript=y"),
]
STRATEGIC = [
 ("Ervin Cable partners","https://ervincable.com/subcontractors/"),
 ("Kenergy construction","https://www.kenergycorp.com/internet/"),
 ("Kenergy contractor FAQ","https://www.kenergycorp.com/internet-faqs/"),
 ("KentuckyWired contracts","https://kentuckywired.ky.gov/LastMilePartner/Pages/KYW%20Contracts.aspx"),
 ("Kentucky Power pole attachments","https://www.kentuckypower.com/business/b2b/pole-attachment/"),
]
CREW = re.compile(r"\\b(subcontractors?|contractors?|crews?|1099|corp.to.corp|c2c)\\b",re.I)
SERVICE = re.compile(r"\\b(fiber|fibre|splicing|aerial|underground|ftth|drop bury|osp|boring)\\b",re.I)
EXCLUDED = re.compile(r"\\b(in.house only|w-?2 only|employee only|sales|door.to.door)\\b",re.I)

def fetch(url):
    from urllib.parse import urlsplit
    p=urlsplit(url)
    robots=RobotFileParser()
    robots.set_url(p.scheme+"://"+p.netloc+"/robots.txt")
    try:
        robots.read()
        if not robots.can_fetch(UA,url):return None,"robots_blocked"
    except Exception:return None,"robots_unknown"
    try:
        r=requests.get(url,headers={"User-Agent":UA},timeout=18)
        r.raise_for_status()
        return BeautifulSoup(r.text,"html.parser"),"ok"
    except requests.RequestException as exc:return None,type(exc).__name__

def discover():
    now=datetime.now(timezone.utc).isoformat()
    results=[]
    checks=[]
    for name,url in INDEXES+STRATEGIC:
        soup,status=fetch(url)
        checks.append({"source":name,"url":url,"status":status,"checked_at":now})
        if status!="ok" or name not in dict(INDEXES):continue
        for a in soup.select("a[href]"):
            title=" ".join(a.get_text(" ",strip=True).split())
            href=urljoin(url,a.get("href",""))
            if "/jobs/" not in href or href.split("?")[0].rstrip("/")==url.split("?")[0].rstrip("/"):continue
            context=" ".join(a.parent.get_text(" ",strip=True).split())[:400]
            # Only consider an explicit KY designation, not nationwide results or keyword-only company pages.
            if not re.search(r"\\b(Kentucky|KY)\\b",context,re.I):continue
            if EXCLUDED.search(title) or not SERVICE.search(title):continue
            results.append({"id":"KY-"+hashlib.sha256(href.encode()).hexdigest()[:18],
             "project":title[:200],"company":name,"state":"KY","service":title[:200],
             "stage":"UNVERIFIED_CREW_REQUEST" if CREW.search(title) else "UNVERIFIED",
             "source_url":href,"source_name":name,
             "evidence":context,"pipeline":"RESEARCH","score":0,
             "first_seen":now,"last_seen":now,"updated_at":now})
    return list({r["source_url"]:r for r in results}.values()),checks

def persist(leads,url):
    if not url:return 0
    import psycopg
    with psycopg.connect(url,connect_timeout=20) as conn:
        with conn.cursor() as c:
            for x in leads:
                keys=list(x)
                cols=",".join(keys)
                placeholders=",".join(["%s"]*len(keys))
                c.execute(f"INSERT INTO leads({cols}) VALUES({placeholders}) ON CONFLICT(id) DO UPDATE SET last_seen=EXCLUDED.last_seen, updated_at=EXCLUDED.updated_at",
                          [x[k] for k in keys])
    return len(leads)

def main():
    leads,checks=discover()
    Path("out").mkdir(exist_ok=True)
    Path("out/kentucky-discovery.json").write_text(json.dumps({"leads":leads,"checks":checks},indent=2),encoding="utf-8")
    count=persist(leads,os.environ.get("DATABASE_URL"))
    print(json.dumps({"kentucky_candidates":len(leads),"persisted":count,"sources_checked":len(checks),"source_statuses":{x["source"]:x["status"] for x in checks}}))

if __name__=="__main__":main()
