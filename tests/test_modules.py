import json,tempfile,unittest
from pathlib import Path
from catalog.app import connect as catalog_db,import_research,confirm
from sales.app import connect as sales_db,contract,work,invoice,payment,balances
class Modules(unittest.TestCase):
 def test_catalog_preserves_review_and_dedupes(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'data.jsonl';p.write_text(json.dumps(dict(company_name='Example Prime',source_url='https://example.com/bid',website='https://example.com',observed_at='2026-10-30',stage='auction'))+'\n')
   db=catalog_db(':memory:');import_research(db,p);import_research(db,p)
   self.assertEqual(db.execute('SELECT COUNT(*) FROM projects').fetchone()[0],1)
   id=db.execute('SELECT id FROM projects').fetchone()[0]
   self.assertEqual(db.execute('SELECT actionable FROM projects').fetchone()[0],0)
   confirm(db,id,'mobilizing',True,'https://example.com/proof')
   self.assertEqual(db.execute('SELECT actionable FROM projects').fetchone()[0],1)
   import_research(db,p)
   self.assertEqual(db.execute('SELECT stage FROM projects').fetchone()[0],'mobilizing')
 def test_receivables_and_overpayment(self):
  db=sales_db(':memory:');contract(db,'C1','Prime','MST');self.assertEqual(work(db,'C1','MST',3,'each','14.00','2026-10-30'),4200)
  invoice(db,'I1','C1','2026-10-30','2026-11-10',42);payment(db,'I1','2026-10-30',12)
  self.assertEqual(balances(db)[0][4],3000)
  with self.assertRaises(ValueError):payment(db,'I1','2026-10-30',31)
if __name__=='__main__':unittest.main()
