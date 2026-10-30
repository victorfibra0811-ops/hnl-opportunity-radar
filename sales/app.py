"""HNL Sales/Billing: private demo ledger. Never deploy SQLite as multi-user production DB."""
import sqlite3
from decimal import Decimal,ROUND_HALF_UP
def cents(x):
 d=Decimal(str(x))
 if not d.is_finite() or d<0:raise ValueError('Invalid money amount')
 return int((d*100).quantize(Decimal(1),rounding=ROUND_HALF_UP))
def connect(path):
 db=sqlite3.connect(path);db.execute('PRAGMA foreign_keys=ON')
 db.executescript('''CREATE TABLE IF NOT EXISTS contracts(id TEXT PRIMARY KEY,client TEXT NOT NULL,project TEXT NOT NULL,stage TEXT NOT NULL DEFAULT 'negotiation');
 CREATE TABLE IF NOT EXISTS work_items(id INTEGER PRIMARY KEY,contract_id TEXT NOT NULL REFERENCES contracts(id),description TEXT NOT NULL,quantity TEXT NOT NULL,unit TEXT NOT NULL,unit_price_cents INTEGER NOT NULL,amount_cents INTEGER NOT NULL,work_date TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS invoices(id TEXT PRIMARY KEY,contract_id TEXT NOT NULL REFERENCES contracts(id),issued_on TEXT NOT NULL,due_on TEXT NOT NULL,amount_cents INTEGER NOT NULL CHECK(amount_cents>=0));
 CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,invoice_id TEXT NOT NULL REFERENCES invoices(id),paid_on TEXT NOT NULL,amount_cents INTEGER NOT NULL CHECK(amount_cents>0),reference TEXT);
 ''');db.commit();return db
def contract(db,id,client,project):
 with db:db.execute('INSERT INTO contracts(id,client,project) VALUES(?,?,?)',(id,client,project))
def work(db,contract_id,description,quantity,unit,unit_price,date):
 q=Decimal(str(quantity));price=Decimal(str(unit_price))
 if not q.is_finite() or q<=0 or not price.is_finite() or price<0:raise ValueError('Invalid quantity or price')
 amount=cents(q*price)
 with db:db.execute('INSERT INTO work_items(contract_id,description,quantity,unit,unit_price_cents,amount_cents,work_date) VALUES(?,?,?,?,?,?,?)',(contract_id,description,str(q),unit,cents(price),amount,date))
 return amount
def invoice(db,id,contract_id,issued,due,amount):
 with db:db.execute('INSERT INTO invoices VALUES(?,?,?,?,?)',(id,contract_id,issued,due,cents(amount)))
def payment(db,invoice_id,paid_on,amount,reference=''):
 amount=cents(amount)
 with db:
  inv=db.execute('SELECT amount_cents FROM invoices WHERE id=?',(invoice_id,)).fetchone()
  if not inv:raise KeyError('Invoice does not exist')
  paid=db.execute('SELECT COALESCE(SUM(amount_cents),0) FROM payments WHERE invoice_id=?',(invoice_id,)).fetchone()[0]
  if amount<=0 or amount+paid>inv[0]:raise ValueError('Payment exceeds unpaid balance')
  db.execute('INSERT INTO payments(invoice_id,paid_on,amount_cents,reference) VALUES(?,?,?,?)',(invoice_id,paid_on,amount,reference))
def balances(db):
 return db.execute('''SELECT i.id,c.client,i.amount_cents,COALESCE(SUM(p.amount_cents),0),i.amount_cents-COALESCE(SUM(p.amount_cents),0),i.due_on FROM invoices i JOIN contracts c ON c.id=i.contract_id LEFT JOIN payments p ON p.invoice_id=i.id GROUP BY i.id,c.client,i.amount_cents,i.due_on ORDER BY i.due_on''').fetchall()
