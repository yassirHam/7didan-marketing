-- Least-privilege database roles. psql variables: dbname, logger_password, reader_password.
-- n8n_logger:     writes the n8n transaction log, nothing else.
-- powerbi_reader: reads the reporting schema (tables and views), never Odoo's own tables.

SELECT format('CREATE ROLE n8n_logger LOGIN PASSWORD %L', :'logger_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'n8n_logger') \gexec
SELECT format('CREATE ROLE powerbi_reader LOGIN PASSWORD %L', :'reader_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'powerbi_reader') \gexec

ALTER ROLE n8n_logger PASSWORD :'logger_password';
ALTER ROLE powerbi_reader PASSWORD :'reader_password';

GRANT CONNECT ON DATABASE :"dbname" TO n8n_logger, powerbi_reader;
GRANT USAGE ON SCHEMA reporting TO n8n_logger, powerbi_reader;

-- n8n's Postgres insert uses RETURNING, which needs SELECT on the same table.
GRANT INSERT, SELECT ON reporting.crm_transactions TO n8n_logger;
GRANT USAGE ON SEQUENCE reporting.crm_transactions_id_seq TO n8n_logger;

GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO powerbi_reader;
