import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from catalog.app import connect as catalog_db, import_research, confirm
from sales.app import connect as sales_db, contract, work, invoice, payment, balances, cents

class CatalogTests(unittest.TestCase):
 def record(self, **changes):
  data={"company_name":"Prime Test","website":"https://prime.example",
        "source_url":"https://prime.example/project?id=1","observed_at":"2026-10-30",
        "stage":"auction","services":["aerial"],"evidence_excerpt":"original"}
  data.update(changes)
  return data
 def test_review_and_dedupe(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"leads.jsonl"
   p.write_text(json.dumps(self.record())+"\n",encoding="utf8")
   db=catalog_db(":memory:")
   import_research(db,p);import_research(db,p)
   self.assertEqual(db.execute("SELECT COUNT(*) FROM projects").fetchone()[0],1)
   pid=db.execute("SELECT id FROM projects").fetchone()[0]
   self.assertEqual(db.execute("SELECT actionable FROM projects").fetchone()[0],0)
   confirm(db,pid,"mobilizing",True,"https://prime.example/crew-request")
   self.assertEqual(db.execute("SELECT actionable FROM projects").fetchone()[0],1)
   p.write_text(json.dumps(self.record(stage="planning",evidence_excerpt="new text"))+"\n",encoding="utf8")
   import_research(db,p)
   self.assertEqual(db.execute("SELECT stage,evidence FROM projects").fetchone(),("mobilizing","https://prime.example/crew-request"))
 def test_unverified_sources_not_one_company(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"leads.jsonl"
   rows=[self.record(company_name="Unverified — research required",website="https://news.google.com",source_url="https://news.google.com/a"),
         self.record(company_name="Unverified — research required",website="https://news.google.com",source_url="https://news.google.com/b")]
   p.write_text("\n".join(json.dumps(r) for r in rows)+"\n",encoding="utf8")
   db=catalog_db(":memory:");import_research(db,p)
   self.assertEqual(db.execute("SELECT COUNT(*) FROM companies").fetchone()[0],2)
 def test_no_confirmed_auction(self):
  db=catalog_db(":memory:")
  with self.assertRaises(KeyError):confirm(db,"missing","in_progress",True,"https://example.com")
  with self.assertRaises(ValueError):confirm(db,"missing","in_progress",True,"")

class SalesTests(unittest.TestCase):
 def setUp(self):
  self.db=sales_db(":memory:")
  contract(self.db,"C1","Prime","MST")
 def test_invoice_payment_and_balance(self):
  self.assertEqual(work(self.db,"C1","MST",3,"each","14.00","2026-10-30"),4200)
  invoice(self.db,"I1","C1","2026-10-30","2026-11-10",42)
  payment(self.db,"I1","2026-10-30",12)
  self.assertEqual(balances(self.db)[0][4],3000)
  with self.assertRaises(ValueError):payment(self.db,"I1","2026-10-30",31)
  self.assertEqual(balances(self.db)[0][4],3000)
 def test_money_rejects_non_finite(self):
  for bad in ("NaN","Infinity","-Infinity","invalid",-1):
   with self.assertRaises(ValueError):cents(bad)
 def test_fractional_quantities(self):
  self.assertEqual(work(self.db,"C1","Underground",2.5,"ft",0.18,"2026-10-30"),45)
 def test_zero_payment_rejected(self):
  invoice(self.db,"I2","C1","2026-10-30","2026-11-10",100)
  with self.assertRaises(ValueError):payment(self.db,"I2","2026-10-30",0)
 def test_foreign_key_enforced(self):
  with self.assertRaises(sqlite3.IntegrityError):work(self.db,"UNKNOWN","MST",1,"each",14,"2026-10-30")
if __name__=="__main__":unittest.main()
