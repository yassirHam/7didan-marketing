#!/bin/sh
# Imports the 7didan workflow and its Postgres credential on every start, then runs n8n.
# The credential is generated from environment variables into a temporary file and
# deleted after import, so no secret is stored in the repository.
set -eu

CRED_FILE="$(mktemp)"
node -e '
const e = process.env;
process.stdout.write(JSON.stringify([{
  id: "7didanReportDB01", name: "7didan reporting DB (n8n_logger)", type: "postgres",
  data: { host: "db", port: 5432, database: e.REPORTING_DB, user: "n8n_logger",
          password: e.N8N_LOGGER_PASSWORD, ssl: "disable" },
}]));
' > "$CRED_FILE"
n8n import:credentials --input="$CRED_FILE"
rm -f "$CRED_FILE"

n8n import:workflow --input=/import/lead_qualification_workflow.json
n8n update:workflow --id=7didanLeadFlow01 --active=true

exec n8n start
