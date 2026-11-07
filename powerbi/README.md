# 7didan Power BI dashboard

The finished report is a Power BI Project (PBIP) modeled after the Dhakira Knowledge Command Centre structure.

## Open the finished dashboard

Open:

```text
powerbi/7didan_Command_Centre/7didan_Command_Centre.pbip
```

The project contains five completed pages and 90 visuals:

1. **Executive overview** — journey, qualified leads, CRM success, processing time, services and sources.
2. **Conversation funnel** — qualification entry, completion, abandonment, abstention and funnel stages.
3. **Lead quality** — scoring, high-priority leads, field completeness, demand and opportunity detail.
4. **CRM integration** — n8n/Odoo transactions, verified creation, duplicate protection and failures.
5. **Processing & controls** — median, average and P90 latency, verification and exception records.

The semantic model includes six tables, three date relationships and 36 DAX measures. The report uses the 7didan Orange theme and labels every page as synthetic demonstration data.

## Data connection

The model imports these PostgreSQL views:

- `reporting.v_conversations`
- `reporting.v_transactions`
- `reporting.v_opportunities`

Default ODBC connection:

```text
Driver={PostgreSQL Unicode(x64)};Server=localhost;Port=5433;Database=7didan;sslmode=disable;
```

No password is stored in the report.

1. Run `python scripts/setup.py` from the repository root.
2. If the database has no demo data, run `python scripts/seed_demo.py 40`.
3. Open the `.pbip` file and refresh.
4. Select database credentials and enter user `powerbi_reader` with `POWERBI_READER_PASSWORD` from `.env`.
5. Use the Organizational privacy level.

Change the connection through the `DidanOdbcConnectionString` Power Query parameter when the host, port or database changes.

## Rebuild

Regenerate the complete PBIP project after changing the model or page definitions:

```powershell
python powerbi/build_7didan_pbip.py
```

The generator writes the report to `powerbi/7didan_Command_Centre/`.

## Verify source KPIs

```powershell
docker compose exec -T db psql -U odoo -d 7didan -c "SELECT * FROM reporting.v_kpis;"
```

The core cards match these SQL calculations when no report filters are applied. Additional DAX measures provide filtered trends, funnel ratios, lead scoring, duplicate-attempt analysis and processing-time percentiles.
