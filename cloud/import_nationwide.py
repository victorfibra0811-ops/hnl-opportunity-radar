"""Import nationwide candidate leads into the HNL Neon PostgreSQL catalog.

Requires: pip install 'psycopg[binary]>=3.2,<4'
DATABASE_URL must be set as a secret in the execution environment.
This is a trusted CLI import, NOT a public API or unauthenticated dashboard.
"""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

STAGES = {"unknown","planning","auction","bid_open","awarded","mobilizing",
          "in_progress","completed","cancelled"}
STATES = dict(zip(
 ("Alabama Alaska Arizona Arkansas California Colorado Connecticut Delaware Florida Georgia "
  "Hawaii Idaho Illinois Indiana Iowa Kansas Kentucky Louisiana Maine Maryland Massachusetts "
  "Michigan Minnesota Mississippi Missouri Montana Nebraska Nevada New_Hampshire New_Jersey "
  "New_Mexico New_York North_Carolina North_Dakota Ohio Oklahoma Oregon Pennsylvania "
  "Rhode_Island South_Carolina South_Dakota Tennessee Texas Utah Vermont Virginia "
  "Washington West_Virginia Wisconsin Wyoming").split(),
 "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
))
STATES={k.replace("_"," "):v for k,v in STATES.items()}

def canonical(url):
    p=urlsplit(url.strip())
    if p.scheme not in ("https","http") or not p.hostname:
        raise ValueError("Invalid source URL")
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path or "/", "", ""))

def parse_row(row):
    source=canonical(row["source_url"])
    title=(row.get("title") or row.get("page_title") or "").strip()
    if not title: raise ValueError("Missing lead title")
    stage=row.get("stage") or "unknown"
    if stage not in STAGES: raise ValueError("Invalid stage")
    region=row.get("state")
    state_code=STATES.get(region)
    if region is not None and state_code is None: raise ValueError("Invalid state")
    return {"url":source,"title":title[:400],"stage":stage,"state_code":state_code,
            "excerpt":(row.get("evidence_excerpt") or row.get("summary") or "")[:1800],
            "observed_at":row.get("observed_at") or datetime.now(timezone.utc).isoformat()}

def import_file(path, dsn):
    import psycopg
    inserted=0
    # One transaction for the whole import. Invalid rows roll everything back.
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            with open(path,encoding="utf-8") as input_file:
                for number,line in enumerate(input_file,1):
                    if not line.strip(): continue
                    try: row=parse_row(json.loads(line))
                    except (ValueError, KeyError, TypeError) as exc:
                        raise ValueError(f"Invalid JSONL row {number}: {exc}") from exc
                    cur.execute("""INSERT INTO hnl.opportunities
                        (title,state_code,source_url,observed_at,project_stage)
                        VALUES (%s,%s,%s,%s,%s)
                        ON CONFLICT(source_url) DO UPDATE SET
                          observed_at=EXCLUDED.observed_at
                        RETURNING id""",
                        (row["title"],row["state_code"],row["url"],
                         row["observed_at"],row["stage"]))
                    opportunity_id=cur.fetchone()[0]
                    cur.execute("""INSERT INTO hnl.opportunity_sources
                        (opportunity_id,url,excerpt)
                        VALUES (%s,%s,%s)
                        ON CONFLICT(opportunity_id,url) DO NOTHING""",
                        (opportunity_id,row["url"],row["excerpt"]))
                    inserted+=1
    return inserted

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("file",help="JSONL produced by Ffiber Research")
    a=parser.parse_args()
    dsn=os.getenv("DATABASE_URL")
    if not dsn:parser.error("DATABASE_URL is missing; configure it privately")
    print(f"Imported {import_file(a.file,dsn)} candidate records. Manual review still required.")

if __name__=="__main__":main()
