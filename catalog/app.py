"""Project catalog: evidence-led intake; never auto-promote scraped leads."""
import hashlib
import json
import sqlite3
from urllib.parse import urlsplit,urlunsplit

STAGES=("unknown","planning","auction","bid_open","awarded","mobilizing","in_progress","completed","cancelled")
def canonical(url):
    p=urlsplit(url.strip())
    if p.scheme not in ("http","https") or not p.hostname:raise ValueError("Invalid URL")
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path or "/", "", ""))
def connect(path):
    db=sqlite3.connect(path,timeout=30)
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("""CREATE TABLE IF NOT EXISTS companies(
      id TEXT PRIMARY KEY,name TEXT NOT NULL,website TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS projects(
      id TEXT PRIMARY KEY,company_id TEXT NOT NULL REFERENCES companies(id),
      stage TEXT NOT NULL,source_url TEXT NOT NULL,observed_at TEXT NOT NULL,
      services TEXT NOT NULL,evidence TEXT,confirmed INTEGER NOT NULL DEFAULT 0,
      actionable INTEGER NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '')""")
    db.commit()
    return db
def import_research(db,filename):
    imported=0
    with open(filename,encoding="utf-8") as stream:
        for lineno,line in enumerate(stream,1):
            if not line.strip():continue
            r=json.loads(line)
            for field in ("company_name","source_url","observed_at"):
                if not r.get(field):raise ValueError(f"line {lineno}: missing {field}")
            stage=r.get("stage","unknown")
            if stage not in STAGES:raise ValueError("Invalid stage")
            source=canonical(r["source_url"])
            name=r["company_name"].strip()
            website=r.get("website","")
            is_unknown=name.lower().startswith("unverified")
            # Unknown news publisher is NOT a known subcontractor company.
            identity="unverified:"+source if is_unknown else (urlsplit(website).netloc.lower() if website else name.casefold())
            cid="org_"+hashlib.sha256(identity.encode()).hexdigest()[:16]
            pid="lead_"+hashlib.sha256(source.encode()).hexdigest()[:20]
            with db:
                db.execute("""INSERT INTO companies(id,name,website) VALUES(?,?,?)
                  ON CONFLICT(id) DO NOTHING""",(cid,name,website))
                db.execute("""INSERT INTO projects(id,company_id,stage,source_url,observed_at,services,evidence)
                  VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                    observed_at=excluded.observed_at,
                    services=excluded.services
                  """,(pid,cid,stage,source,r["observed_at"],
                        json.dumps(r.get("services",[])),r.get("evidence_excerpt","")))
            imported+=1
    return imported
def confirm(db,project_id,stage,crew_demand=False,evidence_url=""):
    if stage not in STAGES:raise ValueError("Invalid stage")
    if crew_demand:
        if not evidence_url:raise ValueError("Explicit crew demand requires evidence")
        evidence_url=canonical(evidence_url)
    ready=int(bool(crew_demand) and stage in ("mobilizing","in_progress") and bool(evidence_url))
    with db:
        existing=db.execute("SELECT evidence FROM projects WHERE id=?",(project_id,)).fetchone()
        if existing is None:raise KeyError("Project not found")
        evidence=evidence_url or existing[0]
        db.execute("""UPDATE projects SET stage=?,confirmed=?,evidence=?,actionable=?
          WHERE id=?""",(stage,int(bool(crew_demand)),evidence,ready,project_id))
