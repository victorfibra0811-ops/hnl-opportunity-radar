"""Import verified source-file structure into Neon; never mark records as confirmed."""
import csv, argparse, hashlib
from datetime import datetime, timezone
import psycopg

def as_lead(row):
    url=(row.get("url_fonte") or "").strip()
    ident=(row.get("id") or "").strip()
    if not ident or not url:
        raise ValueError("Each opportunity requires an id and source URL")
    cls=row.get("classificacao") or ""
    stage={
      "demanda_anunciada":"UNVERIFIED_CREW_REQUEST",
      "cadastro_fornecedores":"VENDOR_REGISTRATION",
      "obra_identificada_demanda_nao_confirmada":"AWARDED_OR_IDENTIFIED_UNVERIFIED",
      "contratado_individual":"EXCLUDED_INDIVIDUAL",
    }.get(cls,"UNVERIFIED")
    return {
      "id":"source-20261031-"+ident,
      "project":row.get("empresa") or ("Unknown contractor "+ident),
      "company":row.get("empresa"),
      "state":row.get("estados") or "UNKNOWN",
      "city":row.get("local"),
      "service":row.get("servicos"),
      "stage":stage,
      "source_url":url,
      "source_name":"HNL Base 2026-10-31",
      "evidence":row.get("evidencia"),
      "published_at":row.get("publicado_em"),
      "deadline":row.get("expira_em"),
      "contact":row.get("contato_nome"),
      "notes":row.get("observacoes"),
      "score":0,
      "pipeline":"NEW" if cls=="demanda_anunciada" else "RESEARCH" if cls!="contratado_individual" else "EXCLUDED",
      "first_seen":row.get("consultado_em") or "2026-10-31",
      "last_seen":row.get("consultado_em") or "2026-10-31",
      "updated_at":datetime.now(timezone.utc).isoformat()
    }

def migrate(path,dburl,dry_run=False):
    with open(path,encoding="utf-8-sig",newline="") as f:
        data=list(csv.DictReader(f))
    records=[as_lead(row) for row in data]
    ids=[r["id"] for r in records]
    if len(ids)!=len(set(ids)):
        raise ValueError("Duplicate source IDs")
    if dry_run:
        return {"total":len(records),"excluded":sum(r["pipeline"]=="EXCLUDED" for r in records)}
    with psycopg.connect(dburl,connect_timeout=20) as conn:
        with conn.cursor() as cur:
            for r in records:
                fields=list(r)
                columns=",".join(fields)
                placeholders=",".join(["%s"]*len(fields))
                # Avoid resetting manually advanced CRM pipeline on an existing record.
                updates=",".join(f"{name}=EXCLUDED.{name}" for name in fields if name not in ("id","pipeline","first_seen"))
                cur.execute(f"INSERT INTO leads ({columns}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}",[r[k] for k in fields])
    return {"total":len(records),"excluded":sum(r["pipeline"]=="EXCLUDED" for r in records)}

if __name__=="__main__":
    import os
    p=argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--dry-run",action="store_true")
    args=p.parse_args()
    db=os.environ.get("DATABASE_URL","")
    if not args.dry_run and not db:
        raise SystemExit("DATABASE_URL environment variable required")
    print(migrate(args.csv,db,args.dry_run))
