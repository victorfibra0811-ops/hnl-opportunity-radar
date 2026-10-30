-- HNL v2 relational model; additive only. Existing leads/activities/changes untouched.
CREATE SCHEMA IF NOT EXISTS hnl;
CREATE TABLE IF NOT EXISTS hnl.contractors (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 name TEXT NOT NULL,
 website TEXT,
 verified BOOLEAN NOT NULL DEFAULT FALSE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hnl.opportunities (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 contractor_id BIGINT REFERENCES hnl.contractors(id),
 title TEXT NOT NULL,
 state_code CHAR(2),
 source_url TEXT NOT NULL UNIQUE,
 observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 published_at TIMESTAMPTZ,
 project_stage TEXT NOT NULL DEFAULT 'unknown'
 CHECK(project_stage IN ('unknown','planning','auction','bid_open','awarded','mobilizing','in_progress','completed','cancelled')),
 crew_demand_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
 crew_demand_evidence TEXT,
 review_status TEXT NOT NULL DEFAULT 'pending'
 CHECK(review_status IN ('pending','verified','rejected')),
 CHECK (NOT crew_demand_confirmed OR crew_demand_evidence IS NOT NULL),
 notes TEXT,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hnl.opportunity_sources(
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 opportunity_id BIGINT NOT NULL REFERENCES hnl.opportunities(id),
 url TEXT NOT NULL,
 excerpt TEXT,
 discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(opportunity_id,url)
);
CREATE TABLE IF NOT EXISTS hnl.sales_contracts(
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 contractor_id BIGINT NOT NULL REFERENCES hnl.contractors(id),
 opportunity_id BIGINT REFERENCES hnl.opportunities(id),
 reference TEXT NOT NULL UNIQUE,
 description TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'draft'
 CHECK(status IN ('draft','active','completed','cancelled')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hnl.work_items(
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 contract_id BIGINT NOT NULL REFERENCES hnl.sales_contracts(id),
 service TEXT NOT NULL,
 quantity NUMERIC(16,3) NOT NULL CHECK(quantity>0),
 unit TEXT NOT NULL,
 unit_price NUMERIC(16,4) NOT NULL CHECK(unit_price>=0),
 amount NUMERIC(18,2) GENERATED ALWAYS AS (round(quantity*unit_price,2)) STORED,
 work_date DATE NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending'
 CHECK(status IN ('pending','approved','rejected','invoiced')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hnl.invoices(
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 contract_id BIGINT NOT NULL REFERENCES hnl.sales_contracts(id),
 invoice_number TEXT NOT NULL UNIQUE,
 issued_at DATE NOT NULL,
 due_at DATE NOT NULL,
 amount NUMERIC(18,2) NOT NULL CHECK(amount>0),
 status TEXT NOT NULL DEFAULT 'draft'
 CHECK(status IN ('draft','issued','void')),
 CHECK(due_at >= issued_at)
);
CREATE TABLE IF NOT EXISTS hnl.payments(
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 invoice_id BIGINT NOT NULL REFERENCES hnl.invoices(id),
 paid_at DATE NOT NULL,
 amount NUMERIC(18,2) NOT NULL CHECK(amount>0),
 reference TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS hnl_opportunities_stage_idx ON hnl.opportunities(project_stage,review_status);
CREATE INDEX IF NOT EXISTS hnl_work_items_contract_idx ON hnl.work_items(contract_id);
CREATE INDEX IF NOT EXISTS hnl_payments_invoice_idx ON hnl.payments(invoice_id);
CREATE OR REPLACE VIEW hnl.invoice_balances AS
 SELECT i.id,i.invoice_number,i.contract_id,i.amount,
 COALESCE(SUM(p.amount),0)::numeric(18,2) AS paid,
 (i.amount-COALESCE(SUM(p.amount),0))::numeric(18,2) AS remaining,
 i.due_at,i.status
 FROM hnl.invoices i LEFT JOIN hnl.payments p ON p.invoice_id=i.id
 GROUP BY i.id;
-- Payments require an atomic balance check in transaction/service before production.
-- Access control: NO web client direct database access. Backend must authenticate users.
