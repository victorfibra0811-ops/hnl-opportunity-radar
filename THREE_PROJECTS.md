# Three distinct HNL products (MVP)

1. **Ffiber Research** (separate private GitHub repository): compliant discovery of prime contractors, subcontractors, and electric utilities; exports JSONL from approved public sources.
2. **HNL Project Catalog** (`catalog/`): import research JSONL, deduplicate companies/projects, record stages `unknown/planning/auction/bid_open/awarded/mobilizing/in_progress/completed/cancelled`, and *only* mark a lead actionable after explicit crew demand confirmation with evidence. Auctions are retained for intelligence, NOT active sales prospects.
3. **HNL Sales & Billing** (`sales/`): separate contract, work quantity/rate, invoice and payment ledger in integer cents. Supports partial payments and checks overpayment. Contractors can be registered manually without relying on pipeline entries.

## Demo locally (no credentials)
```bash
python -m unittest discover -s tests -v
python -m catalog.cli import discoveries.jsonl
python -m catalog.cli list
```

## Safety/deployment status
The two modules are isolated in subfolders for now because a third GitHub repository cannot be provisioned through the current integration. **These SQLite implementations are local prototypes, not the shared production database.** They do not implement authentication, concurrent multi-user access or production deployments. Neon PostgreSQL remains the planned shared storage. Never commit live customer, payment, secret or invoice data into this public repo. Deploy only after migrating to Neon and enforcing authentication/access control for Victor and Mauro. The pre-existing cloud v0.4 has not been independently recovered or deployed.

## Integration contract
Ffiber Research outputs JSONL; the catalog accepts it using `python -m catalog.cli import discoveries.jsonl`. The catalog is separate from sales; no speculative project is turned into a payable work order automatically. Only approved contract records belong in billing.
