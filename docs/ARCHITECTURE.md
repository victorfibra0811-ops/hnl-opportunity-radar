# Cloud deployment design

Status: DESIGN / NOT LIVE.

- Source repo: GitHub; private recommended before CRM data or business records enter workflows.
- Database: Neon project **winter-river-99160988**, PostgreSQL database **hnl_radar** (credentials are not documented here).
- Tables provisioned: leads, activities, changes. Data not migrated from desktop.
- Future deployment: Streamlit Community Cloud, restricted users Victor and Mauro. Never deploy before secure authentication and DB secret setup.
- GitHub Actions workflows: daily source collection and Monday reporting; configure DATABASE_URL as secret and implement verified code before enabling schedules.
- Google Drive backups: not enabled.

## Implementation milestones
1. Publish and test application source with cloud DB connection.
2. Configure CI, application authentication and secrets.
3. Deploy Streamlit Community Cloud and validate both-user access.
4. Validate daily ingestion and suppression rules for stale/irrelevant leads.
5. Activate weekly report and Google Drive archival.
6. Migrate local SQLite records after backing up, deduplicating and verifying.
