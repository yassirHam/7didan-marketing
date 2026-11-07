-- 7didan reporting schema, created inside the Odoo database so Power BI needs one connection.
-- Odoo never reads or writes this schema. Applied by scripts/setup.py (idempotent).
-- psql variables: logger_password, reader_password.

CREATE SCHEMA IF NOT EXISTS reporting;

-- One row per request handled by the n8n workflow (written by n8n).
CREATE TABLE IF NOT EXISTS reporting.crm_transactions (
    id                   bigserial PRIMARY KEY,
    received_at          timestamptz NOT NULL,
    submission_id        text,
    outcome              text NOT NULL CHECK (outcome IN (
                             'created', 'duplicate', 'invalid', 'consent_declined', 'unauthorized',
                             'crm_auth_failed', 'crm_unavailable', 'crm_error', 'verification_failed',
                             'crm_not_configured')),
    http_status          integer NOT NULL,
    crm_id               integer,
    verified             boolean NOT NULL DEFAULT false,
    service_category     text,
    qualification_status text,
    lead_score           integer,
    duration_ms          integer,
    error                text,
    is_synthetic         boolean NOT NULL DEFAULT true
);
CREATE INDEX IF NOT EXISTS crm_transactions_submission_idx ON reporting.crm_transactions (submission_id);

-- Conversation funnel events (written by the FastAPI backend).
CREATE TABLE IF NOT EXISTS reporting.conversation_events (
    id              bigserial PRIMARY KEY,
    conversation_id text NOT NULL,
    event           text NOT NULL CHECK (event IN (
                        'started', 'answered', 'abstained', 'qualification_started',
                        'qualification_completed', 'abandoned')),
    occurred_at     timestamptz NOT NULL DEFAULT now(),
    is_synthetic    boolean NOT NULL DEFAULT true
);
CREATE INDEX IF NOT EXISTS conversation_events_conv_idx ON reporting.conversation_events (conversation_id);

-- Database-level idempotency: two concurrent identical submissions cannot both create an opportunity.
CREATE UNIQUE INDEX IF NOT EXISTS crm_lead_x_submission_id_uniq
    ON public.crm_lead (x_submission_id) WHERE x_submission_id IS NOT NULL;
