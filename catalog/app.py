"""HNL Project Catalog: import research, keep project lifecycle distinct from sales."""
import hashlib,json,sqlite3
from urllib.parse import urlsplit,urlunsplit
STAGES=('unknown','planning','auction','bid_open','awarded','mobilizing','in_progress','completed','cancelled')
def connect(path):
 db=sqlite3.connect(path);db.execute('PRAGMA foreign_keys=ON')
 db.execute('CREATE TABLE IF NOT EXISTS companies(id TEXT PRIMARY KEY,name TEXT NOT NULL,website TEXT)')
 db.execute('''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,company_id TEXT NOT NULL REFERENCES companies(id),stage TEXT NOT NULL,source_url TEXT NOT NULL,observed_at TEXT NOT NULL,services TEXT NOT NULL,evidence TEXT,confirmed INTEGER NOT NULL DEFAULT 0,actionable INTEGER NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '')''')
 db.commit();return db
def import_research(db,filename):
 count=0
 with open(filename,encoding='utf-8') as stream:
  for line in stream:
   if not line.strip():continue
   r=json.loads(line)
   for key in ('company_name','source_url','observed_at'):
    if not r.get(key):raise ValueError('Missing '+key)
   stage=r.get('stage','unknown')
   if stage not in STAGES:raise ValueError('Invalid stage')
   website=r.get('website','')
   if r['company_name'].startswith('Unverified'):
    # News search source is not the contractor. Keep an isolated placeholder per lead.
    identity='unverified:'+r['source_url']
   else:
    identity=urlsplit(website).netloc.lower() if website else ''.join(c for c in r['company_name'].lower() if c.isalnum())
   cid='org_'+hashlib.sha256(identity.encode()).hexdigest()[:16]
   source=r['source_url'];p=urlsplit(source)
   if p.scheme not in ('http','https') or not p.netloc:raise ValueError('Invalid source URL')
   source=urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path or '/', '', ''))
   pid='lead_'+hashlib.sha256((cid+'|'+source).encode()).hexdigest()[:20]
   with db:
    db.execute('INSERT INTO companies VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name',(cid,r['company_name'],website))
    # Preserve analyst edits when the same lead is rediscovered.
    db.execute('''INSERT INTO projects(id,company_id,stage,source_url,observed_at,services,evidence) VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET observed_at=excluded.observed_at,services=excluded.services,evidence=excluded.evidence''',(pid,cid,stage,source,r['observed_at'],json.dumps(r.get('services',[])),r.get('evidence_excerpt','')))
   count+=1
 return count
def confirm(db,project_id,stage,crew_demand=False,evidence_url=''):
 if stage not in STAGES:raise ValueError('Invalid stage')
 if crew_demand and not evidence_url:raise ValueError('Proof URL required')
 ready=int(crew_demand and stage in ('mobilizing','in_progress') and bool(evidence_url))
 with db:
  c=db.execute('UPDATE projects SET stage=?,confirmed=?,evidence=?,actionable=? WHERE id=?',(stage,int(crew_demand),evidence_url,ready,project_id))
  if c.rowcount==0:raise KeyError('Project not found')
