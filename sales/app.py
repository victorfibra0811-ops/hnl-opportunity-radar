"""HNL Sales: precise monetary accounting with invoice allocation safeguards.

Local prototype only. Deploy PostgreSQL for concurrent users.
"""
import sqlite3
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

def decimal_value(value):
    try: d=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError): raise ValueError("Invalid decimal")
    if not d.is_finite(): raise ValueError("Non-finite decimal")
    return d

def cents(value):
    d=decimal_value(value)
    if d<0: raise ValueError("Negative money")
    return int((d*100).quantize(Decimal("1"),rounding=ROUND_HALF_UP))

def connect(path):
    db=sqlite3.connect(path,timeout=30,isolation_level=None)
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=30000")
    db.executescript("""CREATE TABLE IF NOT EXISTS contracts(
      id TEXT PRIMARY KEY, client TEXT NOT NULL, project TEXT NOT NULL,
      stage TEXT NOT NULL DEFAULT 'negotiation');
    CREATE TABLE IF NOT EXISTS work_items(
      id INTEGER PRIMARY KEY, contract_id TEXT NOT NULL REFERENCES contracts(id),
      description TEXT NOT NULL, quantity TEXT NOT NULL, unit TEXT NOT NULL,
      unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents>=0),
      amount_cents INTEGER NOT NULL CHECK(amount_cents>=0), work_date TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS invoices(
      id TEXT PRIMARY KEY, contract_id TEXT NOT NULL REFERENCES contracts(id),
      issued_on TEXT NOT NULL,due_on TEXT NOT NULL,
      amount_cents INTEGER NOT NULL CHECK(amount_cents>=0));
    CREATE TABLE IF NOT EXISTS payments(
      id INTEGER PRIMARY KEY,invoice_id TEXT NOT NULL REFERENCES invoices(id),
      paid_on TEXT NOT NULL,amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
      reference TEXT);
    """)
    return db

def contract(db,id,client,project):
    with db:db.execute("INSERT INTO contracts(id,client,project) VALUES(?,?,?)",(id,client,project))

def work(db,contract_id,description,quantity,unit,unit_price,date):
    q=decimal_value(quantity);price=decimal_value(unit_price)
    if q<=0 or price<0:raise ValueError("Invalid quantity or price")
    # Unit price has cent precision in this MVP. Preserve financial arithmetic exactly.
    price_cents=cents(price)
    amount=cents(q*Decimal(price_cents)/100)
    with db:
        db.execute("""INSERT INTO work_items(contract_id,description,quantity,unit,unit_price_cents,amount_cents,work_date)
                      VALUES(?,?,?,?,?,?,?)""",
                   (contract_id,description,str(q),unit,price_cents,amount,date))
    return amount

def invoice(db,id,contract_id,issued,due,amount):
    amount_cents=cents(amount)
    if amount_cents<=0:raise ValueError("Invoice must be positive")
    with db:
        db.execute("INSERT INTO invoices VALUES(?,?,?,?,?)",(id,contract_id,issued,due,amount_cents))

def payment(db,invoice_id,paid_on,amount,reference=""):
    value=cents(amount)
    if value<=0:raise ValueError("Payment must be positive")
    # BEGIN IMMEDIATE serializes concurrent payment writers on local SQLite.
    db.execute("BEGIN IMMEDIATE")
    try:
        row=db.execute("SELECT amount_cents FROM invoices WHERE id=?",(invoice_id,)).fetchone()
        if not row:raise KeyError("Invoice does not exist")
        paid=db.execute("SELECT COALESCE(SUM(amount_cents),0) FROM payments WHERE invoice_id=?",(invoice_id,)).fetchone()[0]
        if paid+value>row[0]:raise ValueError("Payment exceeds unpaid balance")
        db.execute("INSERT INTO payments(invoice_id,paid_on,amount_cents,reference) VALUES(?,?,?,?)",
                   (invoice_id,paid_on,value,reference))
        db.commit()
    except BaseException:
        db.rollback()
        raise

def balances(db):
    return db.execute("""SELECT i.id,c.client,i.amount_cents,
      COALESCE(SUM(p.amount_cents),0),
      i.amount_cents-COALESCE(SUM(p.amount_cents),0),i.due_on
      FROM invoices i JOIN contracts c ON c.id=i.contract_id
      LEFT JOIN payments p ON p.invoice_id=i.id
      GROUP BY i.id,c.client,i.amount_cents,i.due_on ORDER BY i.due_on""").fetchall()
