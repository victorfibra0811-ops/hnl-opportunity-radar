CREATE OR REPLACE VIEW hnl.actionable_opportunities AS
SELECT id,contractor_id,title,state_code,source_url,observed_at,published_at,
project_stage,crew_demand_evidence,notes,updated_at
FROM hnl.opportunities
WHERE review_status='verified'
  AND crew_demand_confirmed=true
  AND crew_demand_evidence IS NOT NULL
  AND project_stage IN ('mobilizing','in_progress');
