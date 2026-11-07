# 7didan Marketing Command Centre

## Open

Double-click `7didan_Command_Centre.pbip`. It opens directly in Power BI Desktop with five finished dashboard pages. Keep the `.pbip`, `.Report`, and `.SemanticModel` items together.

## First refresh

1. Start and prepare the local stack from the repository root: `python scripts/setup.py`.
2. Generate synthetic demo data if required: `python scripts/seed_demo.py 40`.
3. In Power BI Desktop choose **Home > Refresh**.
4. When prompted, choose **Database** credentials:
   - Username: `powerbi_reader`
   - Password: `POWERBI_READER_PASSWORD` from `.env`
5. Set the source privacy level to **Organizational**.

The connection parameter is `DidanOdbcConnectionString` and defaults to:

```text
Driver={PostgreSQL Unicode(x64)};Server=localhost;Port=5433;Database=7didan;sslmode=disable;
```

Change it through **Transform data > Manage parameters** if the database host, port, or name changes. Credentials are never stored in this project.

## Pages

- Executive overview
- Conversation funnel
- Lead quality
- CRM integration
- Processing & controls

All report values are based on `reporting.v_conversations`, `reporting.v_opportunities`, and `reporting.v_transactions`. The report clearly labels the data as synthetic and the system as an academic prototype.
