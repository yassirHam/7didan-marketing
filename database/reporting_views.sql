-- Reporting views for Power BI and for validating dashboard figures.
-- Odoo stores translatable names as jsonb ({"en_US": "..."}); label() handles jsonb and text.

CREATE OR REPLACE FUNCTION reporting.label(v anyelement) RETURNS text
LANGUAGE sql IMMUTABLE AS $$ SELECT COALESCE(to_jsonb(v) ->> 'en_US', to_jsonb(v) #>> '{}') $$;

-- Opportunities created by 7didan (one row per Odoo record, archived ones included).
CREATE OR REPLACE VIEW reporting.v_opportunities AS
SELECT l.id                        AS crm_id,
       l.create_date               AS created_at,
       l.x_submission_id           AS submission_id,
       l.name                      AS opportunity,
       reporting.label(s.name)     AS stage,
       reporting.label(src.name)   AS source,
       l.x_service_interest        AS service_interest,
       l.x_qualification_status    AS qualification_status,
       l.x_lead_score              AS lead_score,
       (l.x_budget <> 'Unknown')::int + (l.x_requirements <> 'Unknown')::int + (l.x_timeline <> 'Unknown')::int
           + (l.x_service_interest IS NOT NULL)::int + (l.x_need IS NOT NULL)::int AS fields_populated,
       5                           AS fields_expected,
       l.active                    AS is_active,
       true                        AS is_synthetic
FROM public.crm_lead l
LEFT JOIN public.crm_stage s    ON s.id = l.stage_id
LEFT JOIN public.utm_source src ON src.id = l.source_id
WHERE l.x_submission_id IS NOT NULL;

-- Transaction log with the flags the KPIs need.
CREATE OR REPLACE VIEW reporting.v_transactions AS
SELECT t.*,
       t.received_at::date                                             AS received_date,
       t.outcome NOT IN ('invalid', 'consent_declined', 'unauthorized') AS is_valid_submission,
       t.outcome = 'created' AND t.verified                            AS is_verified_creation
FROM reporting.crm_transactions t;

-- Conversation funnel, one row per conversation.
CREATE OR REPLACE VIEW reporting.v_conversations AS
SELECT conversation_id,
       min(occurred_at)                                          AS started_at,
       bool_or(event = 'qualification_started')                 AS entered_qualification,
       bool_or(event = 'qualification_completed')               AS completed_qualification,
       bool_or(event = 'abandoned')                             AS abandoned,
       bool_or(event = 'abstained')                             AS had_abstention,
       bool_and(is_synthetic)                                   AS is_synthetic
FROM reporting.conversation_events
GROUP BY conversation_id;

-- The project KPIs computed in SQL. The Power BI measures must return the same numbers
-- (see powerbi/README.md, "Validate the figures"). NULL means "no data yet".
CREATE OR REPLACE VIEW reporting.v_kpis AS
WITH c AS (SELECT * FROM reporting.v_conversations),
     t AS (SELECT * FROM reporting.v_transactions),
     o AS (SELECT * FROM reporting.v_opportunities)
SELECT
    (SELECT count(*) FROM c)                                                      AS conversations,
    (SELECT count(*) FILTER (WHERE completed_qualification) FROM c)               AS completed_qualifications,
    (SELECT count(*) FILTER (WHERE completed_qualification)::numeric
            / NULLIF(count(*) FILTER (WHERE entered_qualification), 0) FROM c)   AS qualification_completion,
    (SELECT count(*) FILTER (WHERE qualification_status = 'qualified') FROM o)    AS leads_meeting_criteria,
    (SELECT sum(fields_populated)::numeric / NULLIF(sum(fields_expected), 0) FROM o) AS field_completeness,
    (SELECT count(DISTINCT submission_id) FILTER (WHERE is_verified_creation)::numeric
            / NULLIF(count(DISTINCT submission_id) FILTER (WHERE is_valid_submission), 0) FROM t) AS crm_success_rate,
    (SELECT (count(*) - count(DISTINCT submission_id))::numeric / NULLIF(count(*), 0) FROM o) AS duplicate_rate,
    (SELECT count(*) FILTER (WHERE outcome = 'duplicate') FROM t)                 AS duplicates_blocked,
    (SELECT count(*) FILTER (WHERE outcome IN ('invalid', 'consent_declined')) FROM t) AS rejected_submissions,
    (SELECT count(*) FILTER (WHERE outcome IN ('crm_auth_failed', 'crm_unavailable', 'crm_error', 'verification_failed', 'crm_not_configured')) FROM t) AS crm_failures,
    (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) FILTER (WHERE is_verified_creation) FROM t) AS median_processing_ms;
