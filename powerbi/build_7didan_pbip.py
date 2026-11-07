"""Generate the ready-to-open 7didan Power BI Project (PBIP)."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / "7didan_Command_Centre"
REPORT = ROOT / "7didan_Command_Centre.Report"
MODEL = ROOT / "7didan_Command_Centre.SemanticModel"
PAGES = REPORT / "definition" / "pages"
RESOURCES = REPORT / "StaticResources" / "RegisteredResources"


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def literal(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def color(value: str) -> dict:
    return {"solid": {"color": literal(f"'{value}'")}}


def column(entity: str, prop: str, label: str | None = None) -> dict:
    ref = f"{entity}.{prop}"
    return {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "queryRef": ref,
        "nativeQueryRef": label or prop,
    }


def measure(name: str, label: str | None = None) -> dict:
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}}, "Property": name}},
        "queryRef": f"_Measures.{name}",
        "nativeQueryRef": label or name,
    }


def container(title: str) -> dict:
    return {
        "title": [{"properties": {
            "show": literal("true"), "text": literal(f"'{title}'"), "fontSize": literal("12D"),
            "fontColor": color("#1E1712"), "titleWrap": literal("true")
        }}],
        "background": [{"properties": {
            "show": literal("true"), "color": color("#FFFFFF"), "transparency": literal("0D")
        }}],
        "border": [{"properties": {
            "show": literal("true"), "color": color("#E8E1DA"), "radius": literal("12D")
        }}],
    }


def visual_base(name: str, x: float, y: float, w: float, h: float, tab: int, z: int | None = None) -> dict:
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": z if z is not None else tab, "width": w, "height": h, "tabOrder": tab},
    }


def textbox(name: str, x: float, y: float, w: float, h: float, tab: int, text: str,
            size: int = 12, text_color: str = "#1E1712", bold: bool = False,
            family: str = "Segoe UI", background: str | None = None) -> dict:
    out = visual_base(name, x, y, w, h, tab)
    run = {"value": text, "textStyle": {"fontSize": f"{size}pt", "color": text_color, "fontFamily": family}}
    if bold:
        run["textStyle"]["fontWeight"] = "bold"
    vis: dict = {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": [run], "horizontalTextAlignment": "left"}]}}]},
        "drillFilterOtherVisuals": True,
    }
    if background:
        vis["visualContainerObjects"] = {
            "background": [{"properties": {"show": literal("true"), "color": color(background), "transparency": literal("0D")}}],
            "border": [{"properties": {"show": literal("false")}}],
        }
    out["visual"] = vis
    return out


def navigator(name: str, tab: int = 3) -> dict:
    out = visual_base(name, 16, 136, 168, 310, tab)
    out["visual"] = {
        "visualType": "pageNavigator",
        "objects": {
            "fill": [{"properties": {"show": literal("true"), "fillColor": color("#1E1712")}}],
            "text": [{"properties": {"fontColor": color("#FFFFFF"), "fontSize": literal("10D"), "fontFamily": literal("'Segoe UI Semibold'")}}],
        },
        "drillFilterOtherVisuals": True,
    }
    return out


def card(name: str, x: float, y: float, w: float, title: str, measure_name: str, tab: int) -> dict:
    out = visual_base(name, x, y, w, 105, tab)
    out["visual"] = {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [measure(measure_name)]}}},
        "objects": {
            "labels": [{"properties": {"color": color("#FF7900"), "fontSize": literal("27D"), "fontFamily": literal("'Segoe UI Bold'")}}],
            "categoryLabels": [{"properties": {"show": literal("false")}}],
        },
        "visualContainerObjects": container(title),
        "drillFilterOtherVisuals": True,
    }
    return out


def chart(name: str, visual_type: str, x: float, y: float, w: float, h: float, title: str,
          category: dict, values: list[dict], tab: int, sort_field: dict | None = None) -> dict:
    out = visual_base(name, x, y, w, h, tab)
    query: dict = {"queryState": {"Category": {"projections": [category]}, "Y": {"projections": values}}}
    if sort_field:
        query["sortDefinition"] = {"sort": [{"field": sort_field["field"], "direction": "Descending"}], "isDefaultSort": True}
    out["visual"] = {
        "visualType": visual_type, "query": query, "visualContainerObjects": container(title),
        "drillFilterOtherVisuals": True,
    }
    return out


def table(name: str, x: float, y: float, w: float, h: float, title: str,
          fields: list[dict], tab: int, sort_field: dict | None = None) -> dict:
    out = visual_base(name, x, y, w, h, tab)
    query: dict = {"queryState": {"Values": {"projections": fields}}}
    if sort_field:
        query["sortDefinition"] = {"sort": [{"field": sort_field["field"], "direction": "Descending"}], "isDefaultSort": True}
    out["visual"] = {
        "visualType": "tableEx", "query": query, "visualContainerObjects": container(title),
        "drillFilterOtherVisuals": True,
    }
    return out


def sidebar(page_id: str) -> list[dict]:
    return [
        textbox(f"{page_id}01", 0, 0, 200, 800, 0, " ", 9, "#1E1712", background="#1E1712"),
        textbox(f"{page_id}02", 20, 26, 164, 44, 1, "7didan", 22, "#FFFFFF", True, "Segoe UI Semibold"),
        textbox(f"{page_id}03", 20, 72, 164, 42, 2, "Marketing Command Centre", 9, "#FF7900", False, "Segoe UI"),
        navigator(f"{page_id}04", 3),
        textbox(f"{page_id}05", 18, 652, 164, 58, 4, "Orange Maroc Business\nacademic prototype", 9, "#D4CCC5", False, "Segoe UI"),
        textbox(f"{page_id}06", 18, 716, 164, 52, 5, "SYNTHETIC DEMO DATA", 8, "#FFB06E", True, "Segoe UI Semibold"),
    ]


def heading(page_id: str, title: str, subtitle: str) -> list[dict]:
    return [
        textbox(f"{page_id}07", 216, 18, 760, 45, 6, title, 22, "#1E1712", True, "Segoe UI Semibold"),
        textbox(f"{page_id}08", 216, 63, 930, 34, 7, subtitle, 10, "#7C7168", False, "Segoe UI"),
    ]


def write_page(page_id: str, title: str, subtitle: str, visuals: list[dict]) -> None:
    write(PAGES / page_id / "page.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
        "name": page_id, "displayName": title, "displayOption": "FitToPage", "height": 800, "width": 1280,
        "objects": {
            "background": [{"properties": {"color": color("#F7F5F2"), "transparency": literal("0D")}}],
            "displayArea": [{"properties": {"verticalAlignment": literal("'Top'")}}],
        },
    })
    for item in sidebar(page_id) + heading(page_id, title, subtitle) + visuals:
        write(PAGES / page_id / "visuals" / item["name"] / "visual.json", item)


def source_column(name: str, data_type: str, hidden: bool = False, fmt: str | None = None) -> dict:
    c: dict = {"name": name, "dataType": data_type, "sourceColumn": name, "summarizeBy": "none"}
    if hidden:
        c["isHidden"] = True
    if fmt:
        c["formatString"] = fmt
    c["annotations"] = [{"name": "SummarizationSetBy", "value": "Automatic"}]
    return c


def calculated_column(name: str, data_type: str, expression: str, hidden: bool = False, fmt: str | None = None) -> dict:
    c: dict = {"type": "calculated", "name": name, "dataType": data_type, "expression": expression,
               "isDataTypeInferred": True, "summarizeBy": "none"}
    if hidden:
        c["isHidden"] = True
    if fmt:
        c["formatString"] = fmt
    c["annotations"] = [{"name": "SummarizationSetBy", "value": "Automatic"}]
    return c


def import_table(name: str, columns: list[dict], sql: str, transforms: str) -> dict:
    return {
        "name": name,
        "columns": columns,
        "partitions": [{
            "name": name, "mode": "import",
            "source": {"type": "m", "expression": [
                "let",
                f"    Source = Odbc.Query(DidanOdbcConnectionString, {json.dumps(sql)}),",
                f"    #\"Changed Type\" = Table.TransformColumnTypes(Source, {transforms})",
                "in",
                "    #\"Changed Type\"",
            ]},
        }],
        "annotations": [{"name": "PBI_ResultType", "value": "Table"}],
    }


def calc_table(name: str, expression: str, columns: list[dict], measures: list[dict] | None = None) -> dict:
    t: dict = {
        "name": name, "columns": columns,
        "partitions": [{"name": name, "mode": "import", "source": {"type": "calculated", "expression": expression}}],
    }
    if measures:
        t["measures"] = measures
    return t


def calc_table_column(name: str, data_type: str, hidden: bool = False, fmt: str | None = None, sort_by: str | None = None) -> dict:
    c: dict = {"type": "calculatedTableColumn", "name": name, "dataType": data_type,
               "isNameInferred": True, "isDataTypeInferred": True, "sourceColumn": f"[{name}]", "summarizeBy": "none"}
    if hidden:
        c["isHidden"] = True
    if fmt:
        c["formatString"] = fmt
    if sort_by:
        c["sortByColumn"] = sort_by
    c["annotations"] = [{"name": "SummarizationSetBy", "value": "Automatic"}]
    return c


def dax_measure(name: str, expression: str, fmt: str = "#,0", folder: str | None = None, description: str | None = None) -> dict:
    m: dict = {"name": name, "expression": expression, "formatString": fmt,
               "annotations": [{"name": "PBI_FormatHint", "value": "{\"isGeneralNumber\":false}"}]}
    if folder:
        m["displayFolder"] = folder
    if description:
        m["description"] = description
    return m


def build_model() -> None:
    conv_cols = [
        source_column("conversation_id", "string", True), source_column("started_at", "dateTime", False, "General Date"),
        source_column("entered_qualification", "boolean"), source_column("completed_qualification", "boolean"),
        source_column("abandoned", "boolean"), source_column("had_abstention", "boolean"), source_column("is_synthetic", "boolean"),
        calculated_column("Started Date", "dateTime", "DATE ( YEAR ( v_conversations[started_at] ), MONTH ( v_conversations[started_at] ), DAY ( v_conversations[started_at] ) )", True, "Long Date"),
        calculated_column("Journey Status", "string", "SWITCH ( TRUE (), v_conversations[completed_qualification], \"Completed\", v_conversations[abandoned], \"Abandoned\", v_conversations[entered_qualification], \"In qualification\", \"Information only\" )"),
    ]
    conv_sql = 'SELECT conversation_id::text, started_at::timestamp, entered_qualification, completed_qualification, abandoned, had_abstention, is_synthetic FROM reporting.v_conversations'
    conv_types = '{{"conversation_id", type text}, {"started_at", type datetime}, {"entered_qualification", type logical}, {"completed_qualification", type logical}, {"abandoned", type logical}, {"had_abstention", type logical}, {"is_synthetic", type logical}}'

    tx_cols = [
        source_column("id", "int64", True), source_column("received_at", "dateTime", False, "General Date"),
        source_column("submission_id", "string", True), source_column("outcome", "string"), source_column("http_status", "int64"),
        source_column("crm_id", "int64", True), source_column("verified", "boolean"), source_column("service_category", "string"),
        source_column("qualification_status", "string"), source_column("lead_score", "int64"), source_column("duration_ms", "int64"),
        source_column("error", "string"), source_column("is_synthetic", "boolean"), source_column("received_date", "dateTime", True, "Long Date"),
        source_column("is_valid_submission", "boolean"), source_column("is_verified_creation", "boolean"),
        calculated_column("Duration (s)", "double", "DIVIDE ( v_transactions[duration_ms], 1000 )", False, "0.00"),
        calculated_column("Outcome Group", "string", "SWITCH ( TRUE (), v_transactions[outcome] = \"created\", \"Success\", v_transactions[outcome] = \"duplicate\", \"Protected duplicate\", v_transactions[outcome] IN { \"invalid\", \"consent_declined\", \"unauthorized\" }, \"Rejected\", \"CRM failure\" )"),
    ]
    tx_sql = 'SELECT id, received_at::timestamp, submission_id::text, outcome::text, http_status, crm_id, verified, service_category::text, qualification_status::text, lead_score, duration_ms, error::text, is_synthetic, received_date::timestamp, is_valid_submission, is_verified_creation FROM reporting.v_transactions'
    tx_types = '{{"id", Int64.Type}, {"received_at", type datetime}, {"submission_id", type text}, {"outcome", type text}, {"http_status", Int64.Type}, {"crm_id", Int64.Type}, {"verified", type logical}, {"service_category", type text}, {"qualification_status", type text}, {"lead_score", Int64.Type}, {"duration_ms", Int64.Type}, {"error", type text}, {"is_synthetic", type logical}, {"received_date", type datetime}, {"is_valid_submission", type logical}, {"is_verified_creation", type logical}}'

    opp_cols = [
        source_column("crm_id", "int64", True), source_column("created_at", "dateTime", False, "General Date"),
        source_column("submission_id", "string", True), source_column("opportunity", "string"), source_column("stage", "string"),
        source_column("source", "string"), source_column("service_interest", "string"), source_column("qualification_status", "string"),
        source_column("lead_score", "int64"), source_column("fields_populated", "int64"), source_column("fields_expected", "int64"),
        source_column("is_active", "boolean"), source_column("is_synthetic", "boolean"),
        calculated_column("Created Date", "dateTime", "DATE ( YEAR ( v_opportunities[created_at] ), MONTH ( v_opportunities[created_at] ), DAY ( v_opportunities[created_at] ) )", True, "Long Date"),
        calculated_column("Score Band", "string", "SWITCH ( TRUE (), v_opportunities[lead_score] >= 75, \"High (75-100)\", v_opportunities[lead_score] >= 50, \"Medium (50-74)\", \"Low (0-49)\" )"),
    ]
    opp_sql = 'SELECT crm_id, created_at::timestamp, submission_id::text, opportunity::text, stage::text, source::text, service_interest::text, qualification_status::text, lead_score, fields_populated, fields_expected, is_active, is_synthetic FROM reporting.v_opportunities'
    opp_types = '{{"crm_id", Int64.Type}, {"created_at", type datetime}, {"submission_id", type text}, {"opportunity", type text}, {"stage", type text}, {"source", type text}, {"service_interest", type text}, {"qualification_status", type text}, {"lead_score", Int64.Type}, {"fields_populated", Int64.Type}, {"fields_expected", Int64.Type}, {"is_active", type logical}, {"is_synthetic", type logical}}'

    date_cols = [
        calc_table_column("Date", "dateTime", False, "Long Date"), calc_table_column("Year", "int64", False, "0"),
        calc_table_column("Month Number", "int64", True, "0"), calc_table_column("Month", "string", False, sort_by="Month Number"),
        calc_table_column("Year Month", "string"), calc_table_column("Quarter", "string"),
    ]
    date_expr = 'ADDCOLUMNS ( CALENDAR ( DATE ( YEAR ( TODAY () ) - 2, 1, 1 ), DATE ( YEAR ( TODAY () ) + 2, 12, 31 ) ), "Year", YEAR ( [Date] ), "Month Number", MONTH ( [Date] ), "Month", FORMAT ( [Date], "MMM" ), "Year Month", FORMAT ( [Date], "yyyy-MM" ), "Quarter", "Q" & FORMAT ( [Date], "Q" ) )'

    funnel_cols = [calc_table_column("Step", "string", False, sort_by="Sort Order"), calc_table_column("Sort Order", "int64", True, "0")]
    funnel_expr = 'DATATABLE ( "Step", STRING, "Sort Order", INTEGER, { { "Conversations", 1 }, { "Entered qualification", 2 }, { "Completed qualification", 3 }, { "Opportunities created", 4 }, { "Qualified leads", 5 } } )'

    measures = [
        dax_measure("Conversations", "COUNTROWS ( v_conversations )", folder="Conversation funnel"),
        dax_measure("Entered Qualification", "CALCULATE ( [Conversations], v_conversations[entered_qualification] = TRUE () )", folder="Conversation funnel"),
        dax_measure("Completed Qualifications", "CALCULATE ( [Conversations], v_conversations[completed_qualification] = TRUE () )", folder="Conversation funnel"),
        dax_measure("Abandoned Conversations", "CALCULATE ( [Conversations], v_conversations[abandoned] = TRUE () )", folder="Conversation funnel"),
        dax_measure("Conversations with Abstention", "CALCULATE ( [Conversations], v_conversations[had_abstention] = TRUE () )", folder="Conversation funnel"),
        dax_measure("Information-only Conversations", "CALCULATE ( [Conversations], v_conversations[entered_qualification] = FALSE () )", folder="Conversation funnel"),
        dax_measure("Qualification Entry Rate", "DIVIDE ( [Entered Qualification], [Conversations] )", "0.0%;-0.0%;0.0%", "Conversation funnel"),
        dax_measure("Qualification Completion", "DIVIDE ( [Completed Qualifications], [Entered Qualification] )", "0.0%;-0.0%;0.0%", "Conversation funnel"),
        dax_measure("Abandonment Rate", "DIVIDE ( [Abandoned Conversations], [Entered Qualification] )", "0.0%;-0.0%;0.0%", "Conversation funnel"),
        dax_measure("Abstention Rate", "DIVIDE ( [Conversations with Abstention], [Conversations] )", "0.0%;-0.0%;0.0%", "Conversation funnel"),
        dax_measure("Opportunities Created", "COUNTROWS ( v_opportunities )", folder="Lead quality"),
        dax_measure("Leads Meeting Criteria", "CALCULATE ( [Opportunities Created], v_opportunities[qualification_status] = \"qualified\" )", folder="Lead quality"),
        dax_measure("Partial Leads", "CALCULATE ( [Opportunities Created], v_opportunities[qualification_status] = \"partial\" )", folder="Lead quality"),
        dax_measure("Not Qualified Leads", "CALCULATE ( [Opportunities Created], v_opportunities[qualification_status] = \"not_qualified\" )", folder="Lead quality"),
        dax_measure("Average Lead Score", "AVERAGE ( v_opportunities[lead_score] )", "0.0", "Lead quality"),
        dax_measure("Median Lead Score", "MEDIAN ( v_opportunities[lead_score] )", "0.0", "Lead quality"),
        dax_measure("High Priority Leads", "CALCULATE ( [Opportunities Created], v_opportunities[lead_score] >= 75 )", folder="Lead quality"),
        dax_measure("Field Completeness", "DIVIDE ( SUM ( v_opportunities[fields_populated] ), SUM ( v_opportunities[fields_expected] ) )", "0.0%;-0.0%;0.0%", "Lead quality"),
        dax_measure("Opportunity Conversion", "DIVIDE ( [Opportunities Created], [Completed Qualifications] )", "0.0%;-0.0%;0.0%", "Lead quality"),
        dax_measure("Qualified Lead Rate", "DIVIDE ( [Leads Meeting Criteria], [Opportunities Created] )", "0.0%;-0.0%;0.0%", "Lead quality"),
        dax_measure("Total Transactions", "COUNTROWS ( v_transactions )", folder="CRM reliability"),
        dax_measure("Valid Unique Submissions", "CALCULATE ( DISTINCTCOUNT ( v_transactions[submission_id] ), v_transactions[is_valid_submission] = TRUE () )", folder="CRM reliability"),
        dax_measure("Verified Creations", "CALCULATE ( DISTINCTCOUNT ( v_transactions[submission_id] ), v_transactions[is_verified_creation] = TRUE () )", folder="CRM reliability"),
        dax_measure("CRM Success Rate", "DIVIDE ( [Verified Creations], [Valid Unique Submissions] )", "0.0%;-0.0%;0.0%", "CRM reliability"),
        dax_measure("Duplicates Blocked", "CALCULATE ( [Total Transactions], v_transactions[outcome] = \"duplicate\" )", folder="CRM reliability"),
        dax_measure("Duplicate Attempt Rate", "DIVIDE ( [Duplicates Blocked], [Total Transactions] )", "0.0%;-0.0%;0.0%", "CRM reliability"),
        dax_measure("Duplicate Record Rate", "DIVIDE ( [Opportunities Created] - DISTINCTCOUNT ( v_opportunities[submission_id] ), [Opportunities Created] )", "0.0%;-0.0%;0.0%", "CRM reliability"),
        dax_measure("Rejected Submissions", "CALCULATE ( [Total Transactions], v_transactions[outcome] IN { \"invalid\", \"consent_declined\" } )", folder="CRM reliability"),
        dax_measure("Unauthorized Requests", "CALCULATE ( [Total Transactions], v_transactions[outcome] = \"unauthorized\" )", folder="CRM reliability"),
        dax_measure("CRM Failures", "CALCULATE ( [Total Transactions], v_transactions[outcome] IN { \"crm_auth_failed\", \"crm_unavailable\", \"crm_error\", \"verification_failed\", \"crm_not_configured\" } )", folder="CRM reliability"),
        dax_measure("Verified Transaction Rate", "DIVIDE ( CALCULATE ( [Total Transactions], v_transactions[verified] = TRUE () ), [Total Transactions] )", "0.0%;-0.0%;0.0%", "CRM reliability"),
        dax_measure("Median Processing (s)", "DIVIDE ( CALCULATE ( MEDIAN ( v_transactions[duration_ms] ), v_transactions[is_verified_creation] = TRUE () ), 1000 )", "0.00", "Processing time"),
        dax_measure("Average Processing (s)", "DIVIDE ( CALCULATE ( AVERAGE ( v_transactions[duration_ms] ), v_transactions[is_verified_creation] = TRUE () ), 1000 )", "0.00", "Processing time"),
        dax_measure("P90 Processing (s)", "DIVIDE ( CALCULATE ( PERCENTILEX.INC ( v_transactions, v_transactions[duration_ms], 0.9 ), v_transactions[is_verified_creation] = TRUE () ), 1000 )", "0.00", "Processing time"),
        dax_measure("Maximum Processing (s)", "DIVIDE ( CALCULATE ( MAX ( v_transactions[duration_ms] ), v_transactions[is_verified_creation] = TRUE () ), 1000 )", "0.00", "Processing time"),
        dax_measure("Funnel Value", "SWITCH ( SELECTEDVALUE ( 'Funnel Stages'[Step] ), \"Conversations\", [Conversations], \"Entered qualification\", [Entered Qualification], \"Completed qualification\", [Completed Qualifications], \"Opportunities created\", [Opportunities Created], \"Qualified leads\", [Leads Meeting Criteria] )", folder="Conversation funnel"),
    ]

    tables = [
        import_table("v_conversations", conv_cols, conv_sql, conv_types),
        import_table("v_transactions", tx_cols, tx_sql, tx_types),
        import_table("v_opportunities", opp_cols, opp_sql, opp_types),
        calc_table("Date", date_expr, date_cols),
        calc_table("Funnel Stages", funnel_expr, funnel_cols),
        calc_table("_Measures", 'ROW ( "Placeholder", "7didan" )', [calc_table_column("Placeholder", "string", True)], measures),
    ]
    tables[3]["dataCategory"] = "Time"

    model = {
        "name": "7didan_Command_Centre", "compatibilityLevel": 1550,
        "model": {
            "culture": "en-US", "defaultPowerBIDataSourceVersion": "powerBI_V3", "sourceQueryCulture": "en-US",
            "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
            "expressions": [{
                "name": "DidanOdbcConnectionString", "kind": "m",
                "expression": '"Driver={PostgreSQL Unicode(x64)};Server=localhost;Port=5433;Database=7didan;sslmode=disable;" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
                "annotations": [{"name": "PBI_ResultType", "value": "Text"}],
            }],
            "tables": tables,
            "relationships": [
                {"name": "transactions_date", "fromTable": "v_transactions", "fromColumn": "received_date", "toTable": "Date", "toColumn": "Date"},
                {"name": "opportunities_date", "fromTable": "v_opportunities", "fromColumn": "Created Date", "toTable": "Date", "toColumn": "Date"},
                {"name": "conversations_date", "fromTable": "v_conversations", "fromColumn": "Started Date", "toTable": "Date", "toColumn": "Date"},
            ],
            "annotations": [
                {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
                {"name": "PBI_QueryOrder", "value": '["v_conversations", "v_transactions", "v_opportunities"]'},
            ],
        },
    }
    write(MODEL / "model.bim", model)


def build_pages() -> None:
    ids = ["executiveoverview0001", "conversationfunnel002", "leadquality000000003", "crmintegration000004", "processingcontrols005"]

    p = ids[0]
    write_page(p, "Executive overview", "Customer journey, lead quality and verified CRM delivery at a glance.", [
        card(f"{p}10", 216, 102, 196, "Conversations", "Conversations", 10),
        card(f"{p}11", 427, 102, 196, "Qualification completion", "Qualification Completion", 11),
        card(f"{p}12", 638, 102, 196, "Qualified leads", "Leads Meeting Criteria", 12),
        card(f"{p}13", 849, 102, 196, "CRM success rate", "CRM Success Rate", 13),
        card(f"{p}14", 1060, 102, 196, "Median processing", "Median Processing (s)", 14),
        chart(f"{p}20", "areaChart", 216, 223, 616, 260, "Journey activity over time", column("Date", "Date", "Date"), [measure("Conversations"), measure("Completed Qualifications")], 20),
        chart(f"{p}21", "donutChart", 847, 223, 409, 260, "Opportunity qualification mix", column("v_opportunities", "qualification_status", "Status"), [measure("Opportunities Created")], 21),
        chart(f"{p}22", "clusteredBarChart", 216, 500, 340, 276, "Opportunities by service", column("v_opportunities", "service_interest", "Service"), [measure("Opportunities Created")], 22, measure("Opportunities Created")),
        chart(f"{p}23", "clusteredBarChart", 571, 500, 330, 276, "Opportunities by source", column("v_opportunities", "source", "Source"), [measure("Opportunities Created")], 23, measure("Opportunities Created")),
        table(f"{p}24", 916, 500, 340, 276, "Lead portfolio", [column("v_opportunities", "opportunity", "Opportunity"), column("v_opportunities", "stage", "Stage"), column("v_opportunities", "service_interest", "Service"), column("v_opportunities", "lead_score", "Score")], 24, column("v_opportunities", "lead_score")),
    ])

    p = ids[1]
    write_page(p, "Conversation funnel", "Exactly three qualification questions, measured separately from CRM qualification.", [
        card(f"{p}10", 216, 102, 196, "Entered qualification", "Entered Qualification", 10),
        card(f"{p}11", 427, 102, 196, "Completed", "Completed Qualifications", 11),
        card(f"{p}12", 638, 102, 196, "Completion rate", "Qualification Completion", 12),
        card(f"{p}13", 849, 102, 196, "Abandoned", "Abandoned Conversations", 13),
        card(f"{p}14", 1060, 102, 196, "Abstention rate", "Abstention Rate", 14),
        chart(f"{p}20", "clusteredBarChart", 216, 223, 460, 260, "End-to-end marketing funnel", column("Funnel Stages", "Step", "Step"), [measure("Funnel Value")], 20),
        chart(f"{p}21", "areaChart", 691, 223, 565, 260, "Qualification activity over time", column("Date", "Date", "Date"), [measure("Entered Qualification"), measure("Completed Qualifications"), measure("Abandoned Conversations")], 21),
        chart(f"{p}22", "donutChart", 216, 500, 330, 276, "Conversation journey status", column("v_conversations", "Journey Status", "Journey status"), [measure("Conversations")], 22),
        chart(f"{p}23", "clusteredBarChart", 561, 500, 330, 276, "Qualification status", column("v_opportunities", "qualification_status", "Lead status"), [measure("Opportunities Created")], 23, measure("Opportunities Created")),
        table(f"{p}24", 906, 500, 350, 276, "Conversation controls", [column("v_conversations", "started_at", "Started"), column("v_conversations", "Journey Status", "Journey"), column("v_conversations", "had_abstention", "Abstained"), column("v_conversations", "is_synthetic", "Synthetic")], 24, column("v_conversations", "started_at")),
    ])

    p = ids[2]
    write_page(p, "Lead quality", "Transparent scoring, field completeness and service demand for synthetic opportunities.", [
        card(f"{p}10", 216, 102, 196, "Opportunities", "Opportunities Created", 10),
        card(f"{p}11", 427, 102, 196, "Qualified leads", "Leads Meeting Criteria", 11),
        card(f"{p}12", 638, 102, 196, "Average score", "Average Lead Score", 12),
        card(f"{p}13", 849, 102, 196, "High priority", "High Priority Leads", 13),
        card(f"{p}14", 1060, 102, 196, "Field completeness", "Field Completeness", 14),
        chart(f"{p}20", "clusteredBarChart", 216, 223, 420, 260, "Demand by service", column("v_opportunities", "service_interest", "Service"), [measure("Opportunities Created")], 20, measure("Opportunities Created")),
        chart(f"{p}21", "donutChart", 651, 223, 290, 260, "Lead score bands", column("v_opportunities", "Score Band", "Score band"), [measure("Opportunities Created")], 21),
        chart(f"{p}22", "clusteredColumnChart", 956, 223, 300, 260, "Average score by source", column("v_opportunities", "source", "Source"), [measure("Average Lead Score")], 22),
        chart(f"{p}23", "areaChart", 216, 500, 420, 276, "Opportunity creation trend", column("Date", "Date", "Date"), [measure("Opportunities Created"), measure("Leads Meeting Criteria")], 23),
        table(f"{p}24", 651, 500, 605, 276, "Opportunity detail", [column("v_opportunities", "opportunity", "Opportunity"), column("v_opportunities", "service_interest", "Service"), column("v_opportunities", "qualification_status", "Status"), column("v_opportunities", "lead_score", "Score"), column("v_opportunities", "stage", "CRM stage"), column("v_opportunities", "source", "Source")], 24, column("v_opportunities", "lead_score")),
    ])

    p = ids[3]
    write_page(p, "CRM integration", "Verified n8n-to-Odoo outcomes, idempotency protection and controlled failures.", [
        card(f"{p}10", 216, 102, 196, "Transactions", "Total Transactions", 10),
        card(f"{p}11", 427, 102, 196, "Valid submissions", "Valid Unique Submissions", 11),
        card(f"{p}12", 638, 102, 196, "Verified creations", "Verified Creations", 12),
        card(f"{p}13", 849, 102, 196, "CRM success rate", "CRM Success Rate", 13),
        card(f"{p}14", 1060, 102, 196, "Duplicates blocked", "Duplicates Blocked", 14),
        chart(f"{p}20", "areaChart", 216, 223, 616, 260, "CRM outcomes over time", column("Date", "Date", "Date"), [measure("Verified Creations"), measure("CRM Failures"), measure("Rejected Submissions")], 20),
        chart(f"{p}21", "donutChart", 847, 223, 409, 260, "Transactions by outcome group", column("v_transactions", "Outcome Group", "Outcome group"), [measure("Total Transactions")], 21),
        chart(f"{p}22", "clusteredBarChart", 216, 500, 360, 276, "Detailed workflow outcomes", column("v_transactions", "outcome", "Outcome"), [measure("Total Transactions")], 22, measure("Total Transactions")),
        chart(f"{p}23", "clusteredBarChart", 591, 500, 300, 276, "Submissions by service category", column("v_transactions", "service_category", "Category"), [measure("Total Transactions")], 23, measure("Total Transactions")),
        table(f"{p}24", 906, 500, 350, 276, "Latest workflow records", [column("v_transactions", "received_at", "Received"), column("v_transactions", "outcome", "Outcome"), column("v_transactions", "http_status", "HTTP"), column("v_transactions", "verified", "Verified"), column("v_transactions", "Duration (s)", "Seconds")], 24, column("v_transactions", "received_at")),
    ])

    p = ids[4]
    write_page(p, "Processing & controls", "Latency, rejection paths and audit-ready transaction details.", [
        card(f"{p}10", 216, 102, 196, "Median seconds", "Median Processing (s)", 10),
        card(f"{p}11", 427, 102, 196, "Average seconds", "Average Processing (s)", 11),
        card(f"{p}12", 638, 102, 196, "P90 seconds", "P90 Processing (s)", 12),
        card(f"{p}13", 849, 102, 196, "CRM failures", "CRM Failures", 13),
        card(f"{p}14", 1060, 102, 196, "Unauthorized", "Unauthorized Requests", 14),
        chart(f"{p}20", "areaChart", 216, 223, 616, 260, "Processing time trend", column("Date", "Date", "Date"), [measure("Median Processing (s)"), measure("Average Processing (s)"), measure("P90 Processing (s)")], 20),
        chart(f"{p}21", "clusteredBarChart", 847, 223, 409, 260, "Average processing by outcome", column("v_transactions", "outcome", "Outcome"), [measure("Average Processing (s)")], 21, measure("Average Processing (s)")),
        chart(f"{p}22", "clusteredBarChart", 216, 500, 340, 276, "Average processing by service", column("v_transactions", "service_category", "Service category"), [measure("Average Processing (s)")], 22, measure("Average Processing (s)")),
        chart(f"{p}23", "donutChart", 571, 500, 285, 276, "Verification status", column("v_transactions", "verified", "Verified"), [measure("Total Transactions")], 23),
        table(f"{p}24", 871, 500, 385, 276, "Exceptions and controls", [column("v_transactions", "received_at", "Received"), column("v_transactions", "outcome", "Outcome"), column("v_transactions", "service_category", "Category"), column("v_transactions", "http_status", "HTTP"), column("v_transactions", "error", "Error")], 24, column("v_transactions", "received_at")),
    ])

    write(PAGES / "pages.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": ids, "activePageName": ids[0],
    })


def build_project() -> None:
    theme = {
        "name": "7didan-powerbi-theme",
        "dataColors": ["#FF7900", "#1E1712", "#FFB06E", "#D65800", "#7C7168", "#1E9E60", "#D63A30", "#FFE2C4"],
        "background": "#FFFFFF", "foreground": "#1E1712", "tableAccent": "#FF7900",
        "good": "#1E9E60", "neutral": "#FFB06E", "bad": "#D63A30", "maximum": "#FF7900", "center": "#FFB06E", "minimum": "#FFF3E8",
        "textClasses": {
            "title": {"fontSize": 14, "fontFace": "Segoe UI Semibold", "color": "#1E1712"},
            "header": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#1E1712"},
            "callout": {"fontSize": 36, "fontFace": "Segoe UI Bold", "color": "#FF7900"},
            "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": "#7C7168"},
        },
        "visualStyles": {
            "*": {"*": {
                "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
                "border": [{"show": True, "color": {"solid": {"color": "#E8E1DA"}}, "radius": 12}],
                "dropShadow": [{"show": True, "color": {"solid": {"color": "#1E1712"}}, "preset": "BottomRight", "transparency": 93}],
                "title": [{"show": True, "fontColor": {"solid": {"color": "#1E1712"}}, "fontSize": 12, "fontFamily": "Segoe UI Semibold", "titleWrap": True}],
                "labels": [{"color": {"solid": {"color": "#7C7168"}}, "fontSize": 10, "fontFamily": "Segoe UI"}],
                "categoryLabels": [{"show": True, "color": {"solid": {"color": "#7C7168"}}, "fontSize": 10, "fontFamily": "Segoe UI"}],
                "valueAxis": [{"labelColor": {"solid": {"color": "#7C7168"}}, "fontFamily": "Segoe UI", "gridlineShow": True, "gridlineColor": {"solid": {"color": "#E8E1DA"}}, "gridlineStyle": "dashed"}],
                "categoryAxis": [{"labelColor": {"solid": {"color": "#7C7168"}}, "fontFamily": "Segoe UI", "gridlineShow": False}],
            }},
            "card": {"*": {"labels": [{"color": {"solid": {"color": "#FF7900"}}, "fontSize": 27, "fontFamily": "Segoe UI Bold"}], "categoryLabels": [{"show": False}]}},
            "tableEx": {"*": {"values": [{"fontFamily": "Segoe UI", "fontSize": 9, "fontColor": {"solid": {"color": "#1E1712"}}}], "columnHeaders": [{"fontFamily": "Segoe UI Semibold", "fontColor": {"solid": {"color": "#1E1712"}}}], "grid": [{"gridVertical": False, "gridHorizontal": True, "gridHorizontalColor": {"solid": {"color": "#E8E1DA"}}}]}},
        },
    }
    write(RESOURCES / "7didan-powerbi-theme.json", theme)
    write(REPORT / "definition" / "report.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.2.0/schema.json",
        "themeCollection": {"customTheme": {"name": "7didan-powerbi-theme", "reportVersionAtImport": {"visual": "2.7.0", "page": "2.1.0", "report": "3.2.0"}, "type": "RegisteredResources"}},
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources", "items": [{"name": "7didan-powerbi-theme", "path": "7didan-powerbi-theme.json", "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True, "useEnhancedTooltips": True, "allowChangeFilterTypes": True},
    })
    write(REPORT / "definition" / "version.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    write(REPORT / "definition.pbir", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json", "version": "4.0", "datasetReference": {"byPath": {"path": "../7didan_Command_Centre.SemanticModel"}}})
    write(REPORT / ".platform", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json", "metadata": {"type": "Report", "displayName": "7didan Marketing Command Centre"}, "config": {"version": "2.0", "logicalId": "20c3813f-918a-4fe8-ad6f-a897760a1171"}})
    write(MODEL / "definition.pbism", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json", "version": "4.0", "settings": {}})
    write(MODEL / ".platform", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json", "metadata": {"type": "SemanticModel", "displayName": "7didan Marketing Command Centre"}, "config": {"version": "2.0", "logicalId": "2efaf0d2-5df0-41f9-82e9-49a06651a8a6"}})
    write(ROOT / "7didan_Command_Centre.pbip", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0", "artifacts": [{"report": {"path": "7didan_Command_Centre.Report"}}], "settings": {"enableAutoRecovery": True}})

    (ROOT / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n", encoding="utf-8")
    (ROOT / "HOW_TO_OPEN.md").write_text("""# 7didan Marketing Command Centre\n\n## Open\n\nDouble-click `7didan_Command_Centre.pbip`. It opens directly in Power BI Desktop with five finished dashboard pages. Keep the `.pbip`, `.Report`, and `.SemanticModel` items together.\n\n## First refresh\n\n1. Start and prepare the local stack from the repository root: `python scripts/setup.py`.\n2. Generate synthetic demo data if required: `python scripts/seed_demo.py 40`.\n3. In Power BI Desktop choose **Home > Refresh**.\n4. When prompted, choose **Database** credentials:\n   - Username: `powerbi_reader`\n   - Password: `POWERBI_READER_PASSWORD` from `.env`\n5. Set the source privacy level to **Organizational**.\n\nThe connection parameter is `DidanOdbcConnectionString` and defaults to:\n\n```text\nDriver={PostgreSQL Unicode(x64)};Server=localhost;Port=5433;Database=7didan;sslmode=disable;\n```\n\nChange it through **Transform data > Manage parameters** if the database host, port, or name changes. Credentials are never stored in this project.\n\n## Pages\n\n- Executive overview\n- Conversation funnel\n- Lead quality\n- CRM integration\n- Processing & controls\n\nAll report values are based on `reporting.v_conversations`, `reporting.v_opportunities`, and `reporting.v_transactions`. The report clearly labels the data as synthetic and the system as an academic prototype.\n""", encoding="utf-8")


def main() -> None:
    build_project()
    build_model()
    build_pages()
    print(f"Built {ROOT / '7didan_Command_Centre.pbip'}")


if __name__ == "__main__":
    main()
