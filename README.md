# HNL Opportunity Radar

Cloud-first fiber-optic subcontracting prospecting and shared CRM for HNL Communication.

## Current status
- Neon PostgreSQL project provisioned (no credentials stored in Git).
- Cloud application source prepared separately; production deployment pending.
- Workflows and dashboard must be tested with credentials before enabling scheduled operation.

## Business scope
Track **execution-ready B2B** opportunities in all 50 US states: aerial fiber, OSP underground, MST installation, fiber splicing, fiber blowing / jetting, drop bury, and construction restoration.

Exclude future auctions, unawarded bids, individual jobs, stale listings, and projects without evidence of active or imminent execution. Distinguish *crew demand confirmed* from *awarded project requiring investigation*.

## Security
Never commit DATABASE_URL, credentials, private prospect information, reports or SQLite files. Publish app code only. Configure access control before connecting the shared CRM.

## Planned infrastructure
- GitHub Actions: scheduled discovery + Monday report (requires secrets)
- Neon: PostgreSQL source of truth
- Streamlit Cloud: browser-based UI for two authorized users
- Google Drive: report archive and backup once authorized

## Agent instructions
Read [AGENTS.md](AGENTS.md) before modifying this repository.
