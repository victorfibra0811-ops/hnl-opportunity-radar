"""Conservative scheduled public-source discovery. Not a substitute for verified open contracts."""
import json, re, sys, time, os, hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

UA="HNLOpportunityRadar/0.5 (public B2B evidence research; no automated outreach)"
SOURCES=[
  ("ByVerTek business partners","https://byvertek.com/business-partners/"),
  ("Whitmore construction opportunities","https://whitmoreconstruction.net/opportunities/"),
  ("Five Star fiber subcontractors","https://www.fivestarinfrastructure.com/work-with-five-star-fiber-subcontractors/"),
  ("Congruex subcontractors","https://www.congruex.com/subcontractors/"),
  ("Prince Telecom subcontractors","https://princetelecom.com/subcontractors/"),
  ("Ervin Cable subcontractors","https://ervincable.com/subcontractors/"),
]
SERVICES={
"aerial":r"\baerial\b|\blashing\b|\bpole (?:line|attachment)s?\b",
"underground":r"\bunderground\b|\bosp\b|\btrench(?:ing)?\b|\bdirectional drill(?:ing)?\b",
"splicing":r"\bsplic(?:e|er|ing|ers)\b",
"mst":r"\bmst\b|multi.service terminal",
"restoration":r"\brestoration\b|\bconcrete repair\b|\basphalt repair\b|\bturf repair\b|\bsod\b",
"fiber blowing":r"\bfib(?:er|re) (?:blow(?:ing)?|jetting)\b|\bcable blowing\b",
"drop bury":r"\bdrop bury\b|\bdrop burial\b|\bburied (?:service )?drops?\b",
}
B2B=re.compile(r"\bsubcontractors?\b|\bsub.contractors?\b|\bcrews? needed\b|\bcrews? wanted\b|\bpartner (?:with|registration|application)\b|\bcontractor (?:application|opportunities)\b",re.I)
EXCLUDE=re.compile(r"\bcareers?\b|\bapply for (?:a )?job\b|\bjob openings?\b|\bw-2 position\b|\brequest for proposal\b|\brfp\b|\bauction\b|\bbid solicitation\b",re.I)
READY=re.compile(r"\bimmediately\b|\bnow hiring crews\b|\bready to mobilize\b|\bstarting (?:this|next) (?:week|month)\b|\bcrews? needed asap\b|\bactively seeking (?:qualified )?subcontractors?\b",re.I)
def classify(text):
    compact=" ".join(text.split())
    services=[key for key,pat in SERVICES.items() if re.search(pat,compact,re.I)]
    if not services or not B2B.search(compact) or EXCLUDE.search(compact):
        return None
    return {"services":services,"stage":"UNVERIFIED","execution_ready":False,
            "potential_crew_request":bool(READY.search(compact))}
def allowed(url):
    parts=urlparse(url)
    robots=RobotFileParser()
    robots.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
    try:
        robots.read()
        return robots.can_fetch(UA,url)
    except Exception:
        return False
def persist_candidates(records, database_url):
    """Persist unverified source observations idempotently; never claim confirmed work."""
    if not database_url:
        return 0
    import psycopg
    count=0
    with psycopg.connect(database_url,connect_timeout=20) as conn:
        with conn.cursor() as cur:
            for r in records:
                if r.get("status")!="candidate_unverified":
                    continue
                ident="source-"+hashlib.sha256(r["url"].encode()).hexdigest()[:24]
                cur.execute(
                  """INSERT INTO leads(id,project,company,state,service,stage,source_url,source_name,
                  evidence,score,pipeline,first_seen,last_seen,updated_at)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                  ON CONFLICT(id) DO UPDATE SET
                    last_seen=EXCLUDED.last_seen,updated_at=EXCLUDED.updated_at
                  """,
                  (ident,r["source"],r["source"],"UNKNOWN",", ".join(r.get("services",[])),
                   "UNVERIFIED",r["url"],r["source"],"Public source-level B2B signal; project and crew availability not confirmed",
                   0,"RESEARCH",r["checked_at"],r["checked_at"],r["checked_at"]))
                count+=1
    return count

def run():
    records=[]
    for name,url in SOURCES:
        rec={"source":name,"url":url,"checked_at":datetime.now(timezone.utc).isoformat(),
             "status":"not_checked"}
        try:
            if not allowed(url):
                rec["status"]="robots_disallowed_or_unknown"
            else:
                res=requests.get(url,headers={"User-Agent":UA},timeout=15)
                res.raise_for_status()
                text=BeautifulSoup(res.text,"html.parser").get_text(" ",strip=True)[:100000]
                signal=classify(text)
                rec["status"]="candidate_unverified" if signal else "no_qualifying_b2b_signal"
                if signal:rec.update(signal)
        except requests.RequestException as e:
            rec["status"]="fetch_error"
            rec["error_type"]=type(e).__name__
        records.append(rec)
        time.sleep(1)
    folder=Path("out")
    folder.mkdir(exist_ok=True)
    (folder/"latest-discovery.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
    stored=persist_candidates(records,os.environ.get("DATABASE_URL",""))
    print(json.dumps({"checked":len(records),"candidates":sum(x["status"]=="candidate_unverified" for x in records),"persisted":stored},indent=2))
if __name__=="__main__":
    run()
