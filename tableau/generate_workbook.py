"""
Generate a Tableau workbook (.twbx) for the Billing Feed Operations Dashboard.

This script creates a complete Tableau workbook with:
- Data source connected to billing_feed_data_advanced.csv
- Calculated fields for health status, country extraction, SLA analysis
- 6 worksheets: KPI Summary, Today's Status, Weekly Trend, Problematic Feeds,
  SLA Breach Heatmap, Processing Delay Distribution
- 1 dashboard combining all worksheets
- Color encoding: Green (Healthy), Amber (Partial), Red (Failed)
- Tooltips with source vs target, delay, SLA breach info

Usage:
    python generate_workbook.py

Output:
    Feed_Operations_Dashboard.twbx (packaged workbook with embedded data)
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import zipfile
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_SOURCE = os.path.join(SCRIPT_DIR, "..", "backend", "data", "billing_feed_data_advanced.csv")
OUTPUT_DIR = SCRIPT_DIR
TWB_FILENAME = "Feed_Operations_Dashboard.twb"
TWBX_FILENAME = "Feed_Operations_Dashboard.twbx"

DS_NAME = "billing_feed_data"
DS_CAPTION = "Billing Feed Data"


def indent_xml(elem):
    """Pretty-print XML with indentation."""
    rough = ET.tostring(elem, encoding="unicode")
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="  ", encoding="utf-8")


# ---------------------------------------------------------------------------
# Column metadata for the CSV
# ---------------------------------------------------------------------------
COLUMNS = [
    ("feed_id", "integer", "dimension", "nominal"),
    ("billing_date", "date", "dimension", "ordinal"),
    ("source_count", "integer", "measure", "quantitative"),
    ("target_count", "integer", "measure", "quantitative"),
    ("file_count", "integer", "measure", "quantitative"),
    ("ingestion_time", "datetime", "dimension", "ordinal"),
    ("processing_delay_min", "integer", "measure", "quantitative"),
    ("update_dt", "datetime", "dimension", "ordinal"),
    ("sla_breach", "string", "dimension", "nominal"),
    ("version", "integer", "measure", "quantitative"),
    ("version_type", "string", "dimension", "nominal"),
    ("version_status", "string", "dimension", "nominal"),
    ("feed_file_prefix", "string", "dimension", "nominal"),
]

# ---------------------------------------------------------------------------
# Calculated fields
# ---------------------------------------------------------------------------
CALCULATED_FIELDS = [
    {
        "name": "[Calculation_HealthStatus]",
        "caption": "Health Status",
        "datatype": "string",
        "role": "dimension",
        "type": "nominal",
        "formula": (
            'IF [sla_breach] = "True" THEN "Failed"\r\n'
            'ELSEIF [processing_delay_min] > 300 THEN "Partial"\r\n'
            'ELSE "Healthy"\r\n'
            "END"
        ),
    },
    {
        "name": "[Calculation_Country]",
        "caption": "Country",
        "datatype": "string",
        "role": "dimension",
        "type": "nominal",
        "formula": 'RIGHT([feed_file_prefix], 2)',
    },
    {
        "name": "[Calculation_SourceTargetDiff]",
        "caption": "Source Target Diff",
        "datatype": "integer",
        "role": "measure",
        "type": "quantitative",
        "formula": "[source_count] - [target_count]",
    },
    {
        "name": "[Calculation_DiscrepancyPct]",
        "caption": "Discrepancy %",
        "datatype": "real",
        "role": "measure",
        "type": "quantitative",
        "default-format": "p0.0%",
        "formula": (
            "IF [source_count] = 0 THEN 0\r\n"
            "ELSE ABS([source_count] - [target_count]) / [source_count]\r\n"
            "END"
        ),
    },
    {
        "name": "[Calculation_HasRetries]",
        "caption": "Has Retries",
        "datatype": "string",
        "role": "dimension",
        "type": "nominal",
        "formula": 'IF [version] > 1 THEN "Yes" ELSE "No" END',
    },
    {
        "name": "[Calculation_IsLatestDay]",
        "caption": "Is Latest Day",
        "datatype": "boolean",
        "role": "dimension",
        "type": "nominal",
        "formula": "[billing_date] = {MAX([billing_date])}",
    },
    {
        "name": "[Calculation_IsLastWeek]",
        "caption": "Is Last Week",
        "datatype": "boolean",
        "role": "dimension",
        "type": "nominal",
        "formula": "[billing_date] >= DATEADD('day', -7, {MAX([billing_date])})",
    },
    {
        "name": "[Calculation_TotalFeeds]",
        "caption": "Total Feeds Today",
        "datatype": "integer",
        "role": "measure",
        "type": "quantitative",
        "formula": (
            '{FIXED : COUNTD(IF [billing_date] = {MAX([billing_date])} '
            "THEN [feed_id] END)}"
        ),
    },
    {
        "name": "[Calculation_SLABreachCount]",
        "caption": "SLA Breaches Today",
        "datatype": "integer",
        "role": "measure",
        "type": "quantitative",
        "formula": (
            '{FIXED : SUM(IF [billing_date] = {MAX([billing_date])} '
            'AND [sla_breach] = "True" THEN 1 ELSE 0 END)}'
        ),
    },
    {
        "name": "[Calculation_AvgDelay]",
        "caption": "Avg Processing Delay (min)",
        "datatype": "real",
        "role": "measure",
        "type": "quantitative",
        "formula": (
            "{FIXED : AVG(IF [billing_date] = {MAX([billing_date])} "
            "THEN [processing_delay_min] END)}"
        ),
    },
    {
        "name": "[Calculation_RetryCount]",
        "caption": "Feeds With Retries Today",
        "datatype": "integer",
        "role": "measure",
        "type": "quantitative",
        "formula": (
            '{FIXED : COUNTD(IF [billing_date] = {MAX([billing_date])} '
            "AND [version] > 1 THEN [feed_id] END)}"
        ),
    },
    {
        "name": "[Calculation_HealthColor]",
        "caption": "Health Color",
        "datatype": "string",
        "role": "dimension",
        "type": "nominal",
        "formula": (
            'IF [sla_breach] = "True" THEN "red"\r\n'
            'ELSEIF [processing_delay_min] > 300 THEN "amber"\r\n'
            'ELSE "green"\r\n'
            "END"
        ),
    },
    {
        "name": "[Calculation_DelayBucket]",
        "caption": "Delay Bucket",
        "datatype": "string",
        "role": "dimension",
        "type": "nominal",
        "formula": (
            'IF [processing_delay_min] <= 60 THEN "0-60 min"\r\n'
            'ELSEIF [processing_delay_min] <= 120 THEN "60-120 min"\r\n'
            'ELSEIF [processing_delay_min] <= 180 THEN "120-180 min"\r\n'
            'ELSEIF [processing_delay_min] <= 300 THEN "180-300 min"\r\n'
            'ELSE "300+ min (Critical)"\r\n'
            "END"
        ),
    },
    {
        "name": "[Calculation_FeedHealth]",
        "caption": "Feed Health Score",
        "datatype": "real",
        "role": "measure",
        "type": "quantitative",
        "formula": (
            'SUM(IF [sla_breach] = "False" AND [processing_delay_min] <= 300 '
            "THEN 1 ELSE 0 END) / COUNT([feed_id]) * 100"
        ),
    },
]


def build_workbook():
    """Build the complete Tableau workbook XML tree."""
    wb = ET.Element("workbook")
    wb.set("original-version", "18.1")
    wb.set("source-build", "2024.1.0 (20241.24.0117.1044)")
    wb.set("source-platform", "win")
    wb.set("version", "18.1")
    wb.set("xmlns:user", "http://www.tableausoftware.com/xml/user")

    # -- Preferences (color palette) ----------------------------------------
    prefs = ET.SubElement(wb, "preferences")
    # Health status color mapping
    color_pref = ET.SubElement(prefs, "color-palette")
    color_pref.set("name", "Health Status Colors")
    color_pref.set("type", "regular")
    for hex_color in ["#22b14c", "#ff7f27", "#ed1c24"]:  # green, amber, red
        ce = ET.SubElement(color_pref, "color")
        ce.text = hex_color

    # -- Data sources -------------------------------------------------------
    datasources = ET.SubElement(wb, "datasources")
    ds = _build_datasource()
    datasources.append(ds)

    # -- Worksheets ---------------------------------------------------------
    worksheets = ET.SubElement(wb, "worksheets")

    ws_kpi = _build_kpi_worksheet()
    worksheets.append(ws_kpi)

    ws_today = _build_today_status_worksheet()
    worksheets.append(ws_today)

    ws_weekly = _build_weekly_trend_worksheet()
    worksheets.append(ws_weekly)

    ws_problem = _build_problematic_feeds_worksheet()
    worksheets.append(ws_problem)

    ws_heatmap = _build_sla_heatmap_worksheet()
    worksheets.append(ws_heatmap)

    ws_delay = _build_delay_distribution_worksheet()
    worksheets.append(ws_delay)

    # -- Dashboard ----------------------------------------------------------
    dashboards = ET.SubElement(wb, "dashboards")
    dash = _build_dashboard()
    dashboards.append(dash)

    # -- Windows ------------------------------------------------------------
    windows = ET.SubElement(wb, "windows")
    win = ET.SubElement(windows, "window")
    win.set("class", "dashboard")
    win.set("name", "Feed Operations Dashboard")
    win.set("maximized", "true")

    return wb


def _build_datasource():
    """Build the data source element with CSV connection and calculated fields."""
    ds = ET.Element("datasource")
    ds.set("caption", DS_CAPTION)
    ds.set("inline", "true")
    ds.set("name", DS_NAME)
    ds.set("version", "18.1")

    # Connection
    conn = ET.SubElement(ds, "connection")
    conn.set("class", "textscan")
    conn.set("directory", "Data")
    conn.set("filename", "billing_feed_data_advanced.csv")
    conn.set("separator", ",")
    conn.set("header", "yes")

    rel = ET.SubElement(conn, "relation")
    rel.set("name", "billing_feed_data_advanced.csv")
    rel.set("table", "[billing_feed_data_advanced#csv]")
    rel.set("type", "table")

    cols_el = ET.SubElement(rel, "columns")
    cols_el.set("header", "yes")
    for i, (name, dtype, _, _) in enumerate(COLUMNS):
        col = ET.SubElement(cols_el, "column")
        col.set("datatype", dtype)
        col.set("name", name)
        col.set("ordinal", str(i))

    # Column definitions (physical columns)
    for name, dtype, role, ctype in COLUMNS:
        col = ET.SubElement(ds, "column")
        col.set("datatype", dtype)
        col.set("name", f"[{name}]")
        col.set("role", role)
        col.set("type", ctype)
        if name == "feed_id":
            col.set("caption", "Feed ID")
        elif name == "billing_date":
            col.set("caption", "Billing Date")
        elif name == "source_count":
            col.set("caption", "Source Count")
        elif name == "target_count":
            col.set("caption", "Target Count")
        elif name == "file_count":
            col.set("caption", "File Count")
        elif name == "ingestion_time":
            col.set("caption", "Ingestion Time")
        elif name == "processing_delay_min":
            col.set("caption", "Processing Delay (min)")
        elif name == "update_dt":
            col.set("caption", "Update Timestamp")
        elif name == "sla_breach":
            col.set("caption", "SLA Breach")
        elif name == "version":
            col.set("caption", "Version")
        elif name == "version_type":
            col.set("caption", "Version Type")
        elif name == "version_status":
            col.set("caption", "Version Status")
        elif name == "feed_file_prefix":
            col.set("caption", "Feed File Prefix")

    # Calculated fields
    for cf in CALCULATED_FIELDS:
        col = ET.SubElement(ds, "column")
        col.set("caption", cf["caption"])
        col.set("datatype", cf["datatype"])
        col.set("name", cf["name"])
        col.set("role", cf["role"])
        col.set("type", cf["type"])
        if "default-format" in cf:
            col.set("default-format", cf["default-format"])

        calc = ET.SubElement(col, "calculation")
        calc.set("class", "tableau")
        calc.set("formula", cf["formula"])

    # Metadata records
    meta = ET.SubElement(ds, "metadata-records")
    for name, dtype, _, _ in COLUMNS:
        rec = ET.SubElement(meta, "metadata-record")
        rec.set("class", "column")
        rn = ET.SubElement(rec, "remote-name")
        rn.text = name
        ln = ET.SubElement(rec, "local-name")
        ln.text = f"[{name}]"
        lt = ET.SubElement(rec, "local-type")
        lt.text = dtype
        agg = ET.SubElement(rec, "aggregation")
        agg.text = "Sum" if dtype in ("integer", "real") else "Count"

    return ds


def _field_ref(field_name, agg="none", kind="nk"):
    """Create a field reference string like [datasource].[agg:field:kind]."""
    return f"[{DS_NAME}].[{agg}:{field_name}:{kind}]"


def _make_worksheet(name):
    """Create a basic worksheet element."""
    ws = ET.Element("worksheet")
    ws.set("name", name)

    table = ET.SubElement(ws, "table")
    view = ET.SubElement(table, "view")

    # Reference the data source
    dss = ET.SubElement(view, "datasources")
    ds_ref = ET.SubElement(dss, "datasource")
    ds_ref.set("caption", DS_CAPTION)
    ds_ref.set("name", DS_NAME)

    return ws, table, view


def _add_rows_cols(table, rows_str, cols_str):
    """Add rows and cols shelf content to a table element."""
    rows = ET.SubElement(table, "rows")
    rows.text = rows_str
    cols = ET.SubElement(table, "cols")
    cols.text = cols_str


def _add_filter(view, column, values=None, is_bool=False):
    """Add a categorical filter to the view."""
    f = ET.SubElement(view, "filter")
    f.set("class", "categorical")
    f.set("column", f"[{DS_NAME}].[{column}]")
    if values:
        groupfilter = ET.SubElement(f, "groupfilter")
        groupfilter.set("function", "member")
        groupfilter.set("level", f"[{column}]")
        groupfilter.set("member", values[0])


def _add_mark_encoding(panes, mark_class, color_field=None, size_field=None,
                       label_field=None, tooltip_fields=None):
    """Add mark type and encodings to panes."""
    pane = ET.SubElement(panes, "pane")
    mark = ET.SubElement(pane, "mark")
    mark.set("class", mark_class)

    if color_field:
        enc = ET.SubElement(mark, "encoding")
        enc.set("attr", "color")
        enc.set("field", color_field)

    if size_field:
        enc = ET.SubElement(mark, "encoding")
        enc.set("attr", "size")
        enc.set("field", size_field)

    if label_field:
        enc = ET.SubElement(mark, "encoding")
        enc.set("attr", "text")
        enc.set("field", label_field)

    if tooltip_fields:
        for tf in tooltip_fields:
            enc = ET.SubElement(mark, "encoding")
            enc.set("attr", "tooltip")
            enc.set("field", tf)


def _build_kpi_worksheet():
    """Build KPI Summary worksheet with big bold numbers."""
    ws, table, view = _make_worksheet("KPI Summary")

    # Use text table with calculated KPIs
    _add_rows_cols(
        table,
        "",
        (
            f"[{DS_NAME}].[sum:Calculation_TotalFeeds:qk] "
            f"[{DS_NAME}].[sum:Calculation_SLABreachCount:qk] "
            f"[{DS_NAME}].[avg:Calculation_AvgDelay:qk] "
            f"[{DS_NAME}].[sum:Calculation_RetryCount:qk]"
        ),
    )

    panes = ET.SubElement(table, "panes")
    _add_mark_encoding(
        panes, "Text",
        tooltip_fields=[
            _field_ref("Calculation_TotalFeeds", "sum", "qk"),
            _field_ref("Calculation_SLABreachCount", "sum", "qk"),
            _field_ref("Calculation_AvgDelay", "avg", "qk"),
            _field_ref("Calculation_RetryCount", "sum", "qk"),
        ],
    )

    return ws


def _build_today_status_worksheet():
    """Build Today's Feed Status worksheet - shows each feed with health status color."""
    ws, table, view = _make_worksheet("Today's Feed Status")

    # Filter to latest day only
    _add_filter(view, "Calculation_IsLatestDay")

    # Rows: feed_file_prefix, Cols: health status colored
    _add_rows_cols(
        table,
        f"[{DS_NAME}].[none:feed_file_prefix:nk]",
        (
            f"[{DS_NAME}].[sum:source_count:qk] "
            f"[{DS_NAME}].[sum:target_count:qk] "
            f"[{DS_NAME}].[avg:processing_delay_min:qk]"
        ),
    )

    panes = ET.SubElement(table, "panes")
    _add_mark_encoding(
        panes, "Bar",
        color_field=_field_ref("Calculation_HealthStatus", "none", "nk"),
        tooltip_fields=[
            _field_ref("feed_file_prefix", "none", "nk"),
            _field_ref("source_count", "sum", "qk"),
            _field_ref("target_count", "sum", "qk"),
            _field_ref("processing_delay_min", "avg", "qk"),
            _field_ref("sla_breach", "none", "nk"),
            _field_ref("Calculation_SourceTargetDiff", "sum", "qk"),
        ],
    )

    return ws


def _build_weekly_trend_worksheet():
    """Build Weekly Trend worksheet - line chart of feed health over the last week."""
    ws, table, view = _make_worksheet("Weekly Trend")

    # Filter to last week
    _add_filter(view, "Calculation_IsLastWeek")

    # Rows: count of feeds, Cols: billing_date
    _add_rows_cols(
        table,
        (
            f"[{DS_NAME}].[cnt:feed_id:qk] "
            f"[{DS_NAME}].[sum:Calculation_SLABreachCount:qk]"
        ),
        f"[{DS_NAME}].[none:billing_date:ok]",
    )

    panes = ET.SubElement(table, "panes")
    _add_mark_encoding(
        panes, "Line",
        color_field=_field_ref("Calculation_HealthStatus", "none", "nk"),
        tooltip_fields=[
            _field_ref("billing_date", "none", "ok"),
            _field_ref("feed_id", "cnt", "qk"),
            _field_ref("Calculation_SLABreachCount", "sum", "qk"),
            _field_ref("Calculation_AvgDelay", "avg", "qk"),
        ],
    )

    return ws


def _build_problematic_feeds_worksheet():
    """Build Problematic Feeds worksheet - feeds with most SLA breaches / retries."""
    ws, table, view = _make_worksheet("Problematic Feeds")

    # Rows: feed_file_prefix sorted by SLA breach count desc
    # Cols: count of SLA breaches
    _add_rows_cols(
        table,
        f"[{DS_NAME}].[none:feed_file_prefix:nk]",
        (
            f"[{DS_NAME}].[sum:Calculation_SLABreachCount:qk] "
            f"[{DS_NAME}].[avg:processing_delay_min:qk]"
        ),
    )

    panes = ET.SubElement(table, "panes")
    _add_mark_encoding(
        panes, "Bar",
        color_field=_field_ref("Calculation_HealthStatus", "none", "nk"),
        size_field=_field_ref("processing_delay_min", "avg", "qk"),
        tooltip_fields=[
            _field_ref("feed_file_prefix", "none", "nk"),
            _field_ref("Calculation_Country", "none", "nk"),
            _field_ref("Calculation_SLABreachCount", "sum", "qk"),
            _field_ref("processing_delay_min", "avg", "qk"),
            _field_ref("Calculation_RetryCount", "sum", "qk"),
            _field_ref("Calculation_FeedHealth", "sum", "qk"),
        ],
    )

    return ws


def _build_sla_heatmap_worksheet():
    """Build SLA Breach Heatmap - country x date showing breach intensity."""
    ws, table, view = _make_worksheet("SLA Breach Heatmap")

    # Rows: Country, Cols: billing_date (week)
    _add_rows_cols(
        table,
        f"[{DS_NAME}].[none:Calculation_Country:nk]",
        f"[{DS_NAME}].[none:billing_date:ok]",
    )

    panes = ET.SubElement(table, "panes")
    _add_mark_encoding(
        panes, "Square",
        color_field=_field_ref("Calculation_SLABreachCount", "sum", "qk"),
        tooltip_fields=[
            _field_ref("Calculation_Country", "none", "nk"),
            _field_ref("billing_date", "none", "ok"),
            _field_ref("Calculation_SLABreachCount", "sum", "qk"),
            _field_ref("processing_delay_min", "avg", "qk"),
            _field_ref("source_count", "sum", "qk"),
            _field_ref("target_count", "sum", "qk"),
        ],
    )

    return ws


def _build_delay_distribution_worksheet():
    """Build Processing Delay Distribution worksheet."""
    ws, table, view = _make_worksheet("Delay Distribution")

    # Rows: count, Cols: delay bucket
    _add_rows_cols(
        table,
        f"[{DS_NAME}].[cnt:feed_id:qk]",
        f"[{DS_NAME}].[none:Calculation_DelayBucket:nk]",
    )

    panes = ET.SubElement(table, "panes")
    _add_mark_encoding(
        panes, "Bar",
        color_field=_field_ref("Calculation_DelayBucket", "none", "nk"),
        tooltip_fields=[
            _field_ref("Calculation_DelayBucket", "none", "nk"),
            _field_ref("feed_id", "cnt", "qk"),
            _field_ref("processing_delay_min", "avg", "qk"),
        ],
    )

    return ws


def _build_dashboard():
    """Build the dashboard layout combining all worksheets."""
    dash = ET.Element("dashboard")
    dash.set("name", "Feed Operations Dashboard")

    size = ET.SubElement(dash, "size")
    size.set("maxheight", "900")
    size.set("maxwidth", "1400")
    size.set("minheight", "900")
    size.set("minwidth", "1400")

    zones = ET.SubElement(dash, "zones")

    # Root container (vertical layout)
    root_zone = ET.SubElement(zones, "zone")
    root_zone.set("h", "100000")
    root_zone.set("id", "1")
    root_zone.set("type-v2", "layout-basic")
    root_zone.set("w", "100000")
    root_zone.set("x", "0")
    root_zone.set("y", "0")

    # Title zone
    title = ET.SubElement(root_zone, "zone")
    title.set("h", "5000")
    title.set("id", "2")
    title.set("type-v2", "title")
    title.set("w", "100000")
    title.set("x", "0")
    title.set("y", "0")

    # Row 1: KPI Summary (top - executive summary)
    kpi_zone = ET.SubElement(root_zone, "zone")
    kpi_zone.set("h", "12000")
    kpi_zone.set("id", "3")
    kpi_zone.set("name", "KPI Summary")
    kpi_zone.set("type-v2", "worksheet")
    kpi_zone.set("w", "100000")
    kpi_zone.set("x", "0")
    kpi_zone.set("y", "5000")

    # Row 2: Today's Status + Weekly Trend (side by side)
    row2 = ET.SubElement(root_zone, "zone")
    row2.set("h", "30000")
    row2.set("id", "4")
    row2.set("type-v2", "layout-basic")
    row2.set("w", "100000")
    row2.set("x", "0")
    row2.set("y", "17000")

    today_zone = ET.SubElement(row2, "zone")
    today_zone.set("h", "30000")
    today_zone.set("id", "5")
    today_zone.set("name", "Today's Feed Status")
    today_zone.set("type-v2", "worksheet")
    today_zone.set("w", "50000")
    today_zone.set("x", "0")
    today_zone.set("y", "0")

    weekly_zone = ET.SubElement(row2, "zone")
    weekly_zone.set("h", "30000")
    weekly_zone.set("id", "6")
    weekly_zone.set("name", "Weekly Trend")
    weekly_zone.set("type-v2", "worksheet")
    weekly_zone.set("w", "50000")
    weekly_zone.set("x", "50000")
    weekly_zone.set("y", "0")

    # Row 3: Problematic Feeds + SLA Heatmap (side by side)
    row3 = ET.SubElement(root_zone, "zone")
    row3.set("h", "28000")
    row3.set("id", "7")
    row3.set("type-v2", "layout-basic")
    row3.set("w", "100000")
    row3.set("x", "0")
    row3.set("y", "47000")

    problem_zone = ET.SubElement(row3, "zone")
    problem_zone.set("h", "28000")
    problem_zone.set("id", "8")
    problem_zone.set("name", "Problematic Feeds")
    problem_zone.set("type-v2", "worksheet")
    problem_zone.set("w", "50000")
    problem_zone.set("x", "0")
    problem_zone.set("y", "0")

    heatmap_zone = ET.SubElement(row3, "zone")
    heatmap_zone.set("h", "28000")
    heatmap_zone.set("id", "9")
    heatmap_zone.set("name", "SLA Breach Heatmap")
    heatmap_zone.set("type-v2", "worksheet")
    heatmap_zone.set("w", "50000")
    heatmap_zone.set("x", "50000")
    heatmap_zone.set("y", "0")

    # Row 4: Delay Distribution (full width)
    delay_zone = ET.SubElement(root_zone, "zone")
    delay_zone.set("h", "25000")
    delay_zone.set("id", "10")
    delay_zone.set("name", "Delay Distribution")
    delay_zone.set("type-v2", "worksheet")
    delay_zone.set("w", "100000")
    delay_zone.set("x", "0")
    delay_zone.set("y", "75000")

    return dash


def main():
    """Generate the Tableau workbook and package as .twbx."""
    print("Building Tableau workbook XML...")
    wb = build_workbook()

    # Write .twb file
    twb_path = os.path.join(OUTPUT_DIR, TWB_FILENAME)
    xml_bytes = indent_xml(wb)
    with open(twb_path, "wb") as f:
        f.write(xml_bytes)
    print(f"  Written: {twb_path}")

    # Package as .twbx (zip with .twb + Data/)
    twbx_path = os.path.join(OUTPUT_DIR, TWBX_FILENAME)
    csv_path = os.path.abspath(CSV_SOURCE)

    if not os.path.exists(csv_path):
        print(f"  WARNING: CSV not found at {csv_path}")
        print(f"  The .twb file was created but .twbx packaging skipped.")
        return

    with zipfile.ZipFile(twbx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(twb_path, TWB_FILENAME)
        zf.write(csv_path, "Data/billing_feed_data_advanced.csv")

    print(f"  Packaged: {twbx_path}")
    print()
    print("Done! Open the .twbx file in Tableau Public Desktop to view the dashboard.")
    print()
    print("After opening in Tableau:")
    print("  1. The data source and calculated fields are pre-configured")
    print("  2. Six worksheets are set up with the right field assignments")
    print("  3. A dashboard layout combines all worksheets")
    print("  4. Assign Health Status Colors: right-click Health Status field")
    print("     -> Color -> Edit Colors -> assign green/amber/red")
    print("  5. For KPI sheet: increase font size to 24+ for big bold numbers")
    print("  6. Format background: white with light gray gridlines")

    # Clean up standalone .twb (it's inside .twbx now)
    # Keep it for users who want the .twb separately
    print(f"\nBoth {TWB_FILENAME} and {TWBX_FILENAME} are available.")


if __name__ == "__main__":
    main()
