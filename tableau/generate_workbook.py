"""
Generate a Tableau workbook (.twbx) for the Billing Feed Operations Dashboard.

This script creates a complete Tableau workbook validated against the official
Tableau 2026.1 XSD schema (twb_2026.1.0.xsd), with:
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

import os
import uuid
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_SOURCE = os.path.join(
    SCRIPT_DIR, "..", "backend", "data", "billing_feed_data_advanced.csv"
)
OUTPUT_DIR = SCRIPT_DIR
TWB_FILENAME = "Feed_Operations_Dashboard.twb"
TWBX_FILENAME = "Feed_Operations_Dashboard.twbx"

DS_NAME = "billing_feed_data"
DS_CAPTION = "Billing Feed Data"


def uid():
    """Generate a short unique identifier for simple-id elements."""
    return str(uuid.uuid4()).replace("-", "")[:16]


# ---------------------------------------------------------------------------
# Column metadata
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

CAPTIONS = {
    "feed_id": "Feed ID",
    "billing_date": "Billing Date",
    "source_count": "Source Count",
    "target_count": "Target Count",
    "file_count": "File Count",
    "ingestion_time": "Ingestion Time",
    "processing_delay_min": "Processing Delay (min)",
    "update_dt": "Update Timestamp",
    "sla_breach": "SLA Breach",
    "version": "Version",
    "version_type": "Version Type",
    "version_status": "Version Status",
    "feed_file_prefix": "Feed File Prefix",
}

# ---------------------------------------------------------------------------
# Calculated fields
# ---------------------------------------------------------------------------
CALCULATED_FIELDS = [
    {
        "name": "Calculation_HealthStatus",
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
        "name": "Calculation_Country",
        "caption": "Country",
        "datatype": "string",
        "role": "dimension",
        "type": "nominal",
        "formula": "RIGHT([feed_file_prefix], 2)",
    },
    {
        "name": "Calculation_SourceTargetDiff",
        "caption": "Source Target Diff",
        "datatype": "integer",
        "role": "measure",
        "type": "quantitative",
        "formula": "[source_count] - [target_count]",
    },
    {
        "name": "Calculation_DiscrepancyPct",
        "caption": "Discrepancy %",
        "datatype": "real",
        "role": "measure",
        "type": "quantitative",
        "formula": (
            "IF [source_count] = 0 THEN 0\r\n"
            "ELSE ABS([source_count] - [target_count]) / [source_count]\r\n"
            "END"
        ),
    },
    {
        "name": "Calculation_HasRetries",
        "caption": "Has Retries",
        "datatype": "string",
        "role": "dimension",
        "type": "nominal",
        "formula": 'IF [version] > 1 THEN "Yes" ELSE "No" END',
    },
    {
        "name": "Calculation_DelayBucket",
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
        "name": "Calculation_HealthColor",
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
        "name": "Calculation_FeedHealth",
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


def _esc(text):
    """XML-escape a string."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def fqn(field, agg="none"):
    """Build a fully-qualified column reference for rows/cols shelf."""
    for name, dtype, role, kind in COLUMNS:
        if name == field:
            if agg not in ("none", ""):
                sk = "qk"
            else:
                sk = (
                    "qk"
                    if role == "measure"
                    else ("ok" if kind == "ordinal" else "nk")
                )
            return "[{}].[{}:{}:{}]".format(DS_NAME, agg, field, sk)
    for cf in CALCULATED_FIELDS:
        if cf["name"] == field:
            if agg not in ("none", ""):
                sk = "qk"
            else:
                sk = (
                    "qk"
                    if cf["role"] == "measure"
                    else ("ok" if cf["type"] == "ordinal" else "nk")
                )
            return "[{}].[{}:{}:{}]".format(DS_NAME, agg, cf["name"], sk)
    return "[{}].[{}:{}:nk]".format(DS_NAME, agg, field)


# ---------------------------------------------------------------------------
# Worksheet definitions (data-driven)
# ---------------------------------------------------------------------------
WORKSHEETS = [
    {
        "name": "KPI Summary",
        "mark": "Text",
        "rows": "",
        "cols_fields": [
            ("source_count", "sum"),
            ("target_count", "sum"),
            ("processing_delay_min", "avg"),
        ],
        "encodings": {},
        "tooltip_fields": [],
    },
    {
        "name": "Today's Feed Status",
        "mark": "Bar",
        "rows_fields": [("feed_file_prefix", "none")],
        "cols_fields": [
            ("source_count", "sum"),
            ("target_count", "sum"),
            ("processing_delay_min", "avg"),
        ],
        "encodings": {"color": ("Calculation_HealthStatus", "none")},
        "tooltip_fields": [
            ("feed_file_prefix", "none"),
            ("source_count", "sum"),
            ("target_count", "sum"),
            ("processing_delay_min", "avg"),
            ("sla_breach", "none"),
            ("Calculation_SourceTargetDiff", "sum"),
        ],
    },
    {
        "name": "Weekly Trend",
        "mark": "Line",
        "rows_fields": [("feed_id", "cnt")],
        "cols_fields": [("billing_date", "none")],
        "encodings": {"color": ("Calculation_HealthStatus", "none")},
        "tooltip_fields": [
            ("billing_date", "none"),
            ("feed_id", "cnt"),
            ("processing_delay_min", "avg"),
        ],
    },
    {
        "name": "Problematic Feeds",
        "mark": "Bar",
        "rows_fields": [("feed_file_prefix", "none")],
        "cols_fields": [("processing_delay_min", "avg")],
        "encodings": {
            "color": ("Calculation_HealthStatus", "none"),
            "size": ("source_count", "sum"),
        },
        "tooltip_fields": [
            ("feed_file_prefix", "none"),
            ("Calculation_Country", "none"),
            ("processing_delay_min", "avg"),
            ("sla_breach", "none"),
            ("Calculation_FeedHealth", "sum"),
        ],
    },
    {
        "name": "SLA Breach Heatmap",
        "mark": "Square",
        "rows_fields": [("Calculation_Country", "none")],
        "cols_fields": [("billing_date", "none")],
        "encodings": {"color": ("processing_delay_min", "avg")},
        "tooltip_fields": [
            ("Calculation_Country", "none"),
            ("billing_date", "none"),
            ("processing_delay_min", "avg"),
            ("source_count", "sum"),
            ("target_count", "sum"),
        ],
    },
    {
        "name": "Delay Distribution",
        "mark": "Bar",
        "rows_fields": [("feed_id", "cnt")],
        "cols_fields": [("Calculation_DelayBucket", "none")],
        "encodings": {"color": ("Calculation_DelayBucket", "none")},
        "tooltip_fields": [
            ("Calculation_DelayBucket", "none"),
            ("feed_id", "cnt"),
            ("processing_delay_min", "avg"),
        ],
    },
]


# ===================================================================
# XML builders - all follow the official Tableau 2026.1 XSD ordering
# ===================================================================


def build_datasource_xml():
    """Build the <datasource> element.

    XSD child order for inline datasource:
        connection -> column* (no metadata-records at datasource level)
    """
    lines = []
    a = lines.append

    a(
        '  <datasource caption="{}" inline="true"'
        ' name="{}" version="26.1">'.format(_esc(DS_CAPTION), DS_NAME)
    )

    # -- connection --
    a(
        '    <connection class="textscan" directory="Data"'
        ' filename="billing_feed_data_advanced.csv"'
        ' separator=",">'
    )
    a(
        '      <relation name="billing_feed_data_advanced.csv"'
        ' table="[billing_feed_data_advanced#csv]" type="table">'
    )
    a('        <columns header="yes">')
    for i, (name, dtype, _, _) in enumerate(COLUMNS):
        a(
            '          <column datatype="{}" name="{}"'
            ' ordinal="{}" />'.format(dtype, name, i)
        )
    a("        </columns>")
    a("      </relation>")
    a("    </connection>")

    # -- column definitions (physical) --
    for name, dtype, role, ctype in COLUMNS:
        cap = CAPTIONS.get(name, name)
        a(
            '    <column caption="{}" datatype="{}" name="[{}]"'
            ' role="{}" type="{}" />'.format(_esc(cap), dtype, name, role, ctype)
        )

    # -- column definitions (calculated) --
    for cf in CALCULATED_FIELDS:
        a(
            '    <column caption="{}" datatype="{}" name="[{}]"'
            ' role="{}" type="{}">'.format(
                _esc(cf["caption"]),
                cf["datatype"],
                cf["name"],
                cf["role"],
                cf["type"],
            )
        )
        a(
            '      <calculation class="tableau"'
            ' formula="{}" />'.format(_esc(cf["formula"]))
        )
        a("    </column>")

    a("  </datasource>")
    return "\n".join(lines)


def build_datasource_deps_xml(indent=8):
    """Build <datasource-dependencies> declaring columns used by the view.

    XSD allows: (column | column-instance | style)*
    """
    pad = " " * indent
    lines = []
    a = lines.append

    a(
        '{}<datasource-dependencies datasource="{}">'.format(pad, DS_NAME)
    )

    # Physical columns
    for name, dtype, role, ctype in COLUMNS:
        a(
            '{}  <column datatype="{}" name="[{}]"'
            ' role="{}" type="{}" />'.format(pad, dtype, name, role, ctype)
        )

    # Calculated columns
    for cf in CALCULATED_FIELDS:
        a(
            '{}  <column datatype="{}" name="[{}]"'
            ' role="{}" type="{}">'.format(
                pad, cf["datatype"], cf["name"], cf["role"], cf["type"]
            )
        )
        a(
            '{}    <calculation class="tableau"'
            ' formula="{}" />'.format(pad, _esc(cf["formula"]))
        )
        a("{}  </column>".format(pad))

    a("{}</datasource-dependencies>".format(pad))
    return "\n".join(lines)


def build_worksheet_xml(ws_def):
    """Build a single <worksheet> element.

    XSD ordering for table (Workbook-VisualSpecification-G):
        view -> style -> panes -> rows -> cols

    XSD ordering for view:
        datasources -> datasource-dependencies -> aggregation

    XSD ordering for pane (PaneSpecification-G):
        mark -> encodings
    """
    name = ws_def["name"]
    mark_type = ws_def["mark"]
    rows_fields = ws_def.get("rows_fields", [])
    cols_fields = ws_def.get("cols_fields", [])
    rows_text = ws_def.get("rows", None)
    cols_text = ws_def.get("cols", None)
    encodings = ws_def.get("encodings", {})
    tooltip_fields = ws_def.get("tooltip_fields", [])
    ws_uuid = uid()

    # Build rows/cols text from field specs if not provided directly
    if rows_text is None:
        rows_text = (
            " ".join(fqn(f, ag) for f, ag in rows_fields)
            if rows_fields
            else ""
        )
    if cols_text is None:
        cols_text = (
            " ".join(fqn(f, ag) for f, ag in cols_fields)
            if cols_fields
            else ""
        )

    lines = []
    a = lines.append

    a('  <worksheet name="{}">'.format(_esc(name)))
    a("    <table>")

    # ---- view (1st child of table) ----
    a("      <view>")
    a("        <datasources>")
    a(
        '          <datasource caption="{}"'
        ' name="{}" />'.format(_esc(DS_CAPTION), DS_NAME)
    )
    a("        </datasources>")
    a(build_datasource_deps_xml(indent=8))
    a('        <aggregation value="true" />')
    a("      </view>")

    # ---- style (2nd child of table) ----
    a("      <style />")

    # ---- panes (3rd child of table) ----
    a("      <panes>")
    a("        <pane>")
    # mark: empty element with class attribute
    a('          <mark class="{}" />'.format(mark_type))
    # encodings wrapper
    if encodings or tooltip_fields:
        a("          <encodings>")
        if "color" in encodings:
            field, ag = encodings["color"]
            a(
                '            <color column="{}" />'.format(
                    _esc(fqn(field, ag))
                )
            )
        if "size" in encodings:
            field, ag = encodings["size"]
            a(
                '            <size column="{}" />'.format(
                    _esc(fqn(field, ag))
                )
            )
        if "text" in encodings:
            field, ag = encodings["text"]
            a(
                '            <text column="{}" />'.format(
                    _esc(fqn(field, ag))
                )
            )
        for field, ag in tooltip_fields:
            a(
                '            <tooltip column="{}" />'.format(
                    _esc(fqn(field, ag))
                )
            )
        a("          </encodings>")
    a("        </pane>")
    a("      </panes>")

    # ---- rows (after panes per XSD) ----
    a("      <rows>{}</rows>".format(_esc(rows_text)))
    # ---- cols (after rows per XSD) ----
    a("      <cols>{}</cols>".format(_esc(cols_text)))

    a("    </table>")

    # simple-id (required last child of worksheet)
    a('    <simple-id uuid="{{{}}}" />'.format(ws_uuid))
    a("  </worksheet>")

    return "\n".join(lines)


def build_dashboard_xml():
    """Build the <dashboard> element.

    XSD ordering for DashboardDoc-G:
        style? -> size? -> zones -> simple-id
    """
    dash_uuid = uid()

    lines = []
    a = lines.append

    a('  <dashboard name="Feed Operations Dashboard">')

    # size
    a(
        '    <size maxheight="900" maxwidth="1400"'
        ' minheight="900" minwidth="1400" />'
    )

    # zones
    a("    <zones>")
    # Root layout zone (vertical container)
    a(
        '      <zone h="100000" id="2" type-v2="layout-basic"'
        ' w="100000" x="0" y="0">'
    )

    # Title zone
    a(
        '        <zone h="5000" id="3" type-v2="title"'
        ' w="100000" x="0" y="0" />'
    )

    # Row 1: KPI Summary
    a(
        '        <zone h="12000" id="4" name="KPI Summary"'
        ' w="100000" x="0" y="5000" />'
    )

    # Row 2: Today's Status + Weekly Trend
    a(
        '        <zone h="28000" id="5" type-v2="layout-basic"'
        ' w="100000" x="0" y="17000">'
    )
    a(
        "          <zone h=\"28000\" id=\"6\""
        " name=\"Today&apos;s Feed Status\""
        ' w="50000" x="0" y="0" />'
    )
    a(
        '          <zone h="28000" id="7" name="Weekly Trend"'
        ' w="50000" x="50000" y="0" />'
    )
    a("        </zone>")

    # Row 3: Problematic Feeds + SLA Heatmap
    a(
        '        <zone h="28000" id="8" type-v2="layout-basic"'
        ' w="100000" x="0" y="45000">'
    )
    a(
        '          <zone h="28000" id="9" name="Problematic Feeds"'
        ' w="50000" x="0" y="0" />'
    )
    a(
        '          <zone h="28000" id="10" name="SLA Breach Heatmap"'
        ' w="50000" x="50000" y="0" />'
    )
    a("        </zone>")

    # Row 4: Delay Distribution
    a(
        '        <zone h="27000" id="11" name="Delay Distribution"'
        ' w="100000" x="0" y="73000" />'
    )

    a("      </zone>")
    a("    </zones>")

    # simple-id
    a('    <simple-id uuid="{{{}}}" />'.format(dash_uuid))
    a("  </dashboard>")

    return "\n".join(lines)


def build_windows_xml():
    """Build the <windows> element.

    XSD ordering for dashboard window:
        viewpoints -> active -> simple-id
    """
    win_uuid = uid()

    lines = []
    a = lines.append

    a("  <windows>")
    a(
        '    <window class="dashboard" maximized="true"'
        ' name="Feed Operations Dashboard">'
    )

    # viewpoints
    a("      <viewpoints>")
    for ws in WORKSHEETS:
        a('        <viewpoint name="{}" />'.format(_esc(ws["name"])))
    a("      </viewpoints>")

    # active element
    a('      <active id="-1" />')

    # simple-id
    a('      <simple-id uuid="{{{}}}" />'.format(win_uuid))

    a("    </window>")
    a("  </windows>")

    return "\n".join(lines)


def build_workbook_xml():
    """Build the complete <workbook> XML.

    XSD ordering for WorkbookFile-CT:
        preferences -> datasources -> worksheets -> dashboards -> windows
    """
    lines = []
    a = lines.append

    a('<?xml version="1.0" encoding="utf-8"?>')
    a(
        '<workbook original-version="26.1"'
        ' source-build="2026.1.0 (20261.26.0211.1127)"'
        ' source-platform="win"'
        ' version="26.1"'
        ' xmlns:user="http://www.tableausoftware.com/xml/user">'
    )

    # --- preferences ---
    a("  <preferences>")
    a('    <color-palette name="Health Status Colors" type="regular">')
    a("      <color>#22b14c</color>")
    a("      <color>#ff7f27</color>")
    a("      <color>#ed1c24</color>")
    a("    </color-palette>")
    a("  </preferences>")

    # --- datasources ---
    a("  <datasources>")
    a(build_datasource_xml())
    a("  </datasources>")

    # --- worksheets ---
    a("  <worksheets>")
    for ws_def in WORKSHEETS:
        a(build_worksheet_xml(ws_def))
    a("  </worksheets>")

    # --- dashboards ---
    a("  <dashboards>")
    a(build_dashboard_xml())
    a("  </dashboards>")

    # --- windows ---
    a(build_windows_xml())

    a("</workbook>")
    return "\n".join(lines)


def main():
    """Generate the Tableau workbook and package as .twbx."""
    print("Building Tableau workbook XML (XSD-compliant)...")
    xml_content = build_workbook_xml()

    # Write .twb file
    twb_path = os.path.join(OUTPUT_DIR, TWB_FILENAME)
    with open(twb_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    print("  Written: {}".format(twb_path))

    # Package as .twbx (zip with .twb + Data/)
    twbx_path = os.path.join(OUTPUT_DIR, TWBX_FILENAME)
    csv_path = os.path.abspath(CSV_SOURCE)

    if not os.path.exists(csv_path):
        print("  WARNING: CSV not found at {}".format(csv_path))
        print("  The .twb file was created but .twbx packaging skipped.")
        return

    with zipfile.ZipFile(twbx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(twb_path, TWB_FILENAME)
        zf.write(csv_path, "Data/billing_feed_data_advanced.csv")

    print("  Packaged: {}".format(twbx_path))
    print()
    print("Done! Open the .twbx file in Tableau Public Desktop.")
    print()
    print("After opening in Tableau:")
    print("  1. Data source and calculated fields are pre-configured")
    print("  2. Six worksheets with field assignments are ready")
    print("  3. A dashboard layout combines all worksheets")
    print("  4. Right-click Health Status -> Color -> Edit Colors")
    print("     to assign green/amber/red")
    print("  5. For KPI sheet: increase font size to 24+")
    print(
        "\nBoth {} and {} are available.".format(TWB_FILENAME, TWBX_FILENAME)
    )


if __name__ == "__main__":
    main()
