"""Usage: python -m catalog.cli import research.jsonl | list | status ID STAGE URL"""
import argparse,os
from .app import connect,import_research,confirm
p=argparse.ArgumentParser();p.add_argument('command',choices=['import','list','status']);p.add_argument('args',nargs='*');a=p.parse_args()
db=connect(os.environ.get('HNL_CATALOG_DB','hnl_catalog.sqlite'))
if a.command=='import':print('Imported',import_research(db,a.args[0]))
elif a.command=='list':
 for r in db.execute('SELECT p.id,c.name,p.stage,p.actionable,p.source_url FROM projects p JOIN companies c ON c.id=p.company_id ORDER BY p.observed_at DESC'):print(*r,sep=' | ')
else:
 if len(a.args)<2:raise SystemExit('status PROJECT_ID STAGE [EVIDENCE_URL]')
 confirm(db,a.args[0],a.args[1],len(a.args)>2,a.args[2] if len(a.args)>2 else '')
