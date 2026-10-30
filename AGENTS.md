# HNL Opportunity Radar — Engineering Instructions

Develop a real production-oriented, cloud-first Python application. The shared PostgreSQL database is the sole writable source of truth. Victor and Mauro must see the same CRM history across devices.

## Non-negotiable acceptance criteria
1. Only execution-ready fiber construction opportunities enter the actionable pipeline: confirmed crew requests and contracted projects actively mobilizing. Record evidence URL, publication date, crawl timestamp, work state, service categories, prime contractor, geography, confidence and expiration.
2. Separate confirmed B2B crew demand from speculative leads requiring human verification. Exclude individual jobs, future auctions, unawarded bids and planning-only projects.
3. Cover every US state via modular, compliant collectors. Do not claim national coverage based only on an initial handful of sources. Respect robots.txt, rate limits, terms, paywalls and authentication.
4. Include aerial, underground, MST, splicing, restoration, fiber blowing/jetting, drop bury/drop burial.
5. Shared CRM includes owner, pipeline stage, contact details, touchpoints, next follow-up, change audit and optimistic concurrency or transactions.
6. Weekly report on Mondays in America/New_York must summarize prior Mon-Sun week; clearly distinguish retrieved opportunities from verified open contracts. Store and archive reports without leaking customer information.
7. Secrets in environment/GitHub Actions/Streamlit secrets ONLY; never in repository. Protect application authentication, sessions and authorization. Use parameterized SQL and least-privilege DB credentials.
8. Write failing regression tests before fixes (red/green/refactor). Tests cover false positives, dedupe, concurrency, report date ranges and authorization.
9. Require CI tests before deployment. Use small, reviewable changes and clear ADRs for architectural decisions.

## Recommended external engineering references
Matt Pocock's public skills repository (https://github.com/mattpocock/skills) documents TDD, debugging and architecture practices. Review skills before adopting; do not install external code or automatically execute unreviewed instructions.
