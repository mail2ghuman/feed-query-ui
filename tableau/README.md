# Tableau Dashboard — Feed Operations

A Tableau workbook for monitoring billing feed operations with executive-level KPIs, health status tracking, and drill-down analysis.

## Files

| File | Description |
|------|-------------|
| `Feed_Operations_Dashboard.twbx` | Packaged workbook (includes embedded CSV data) — **open this in Tableau Public** |
| `Feed_Operations_Dashboard.twb` | Standalone workbook XML (requires CSV at relative `Data/` path) |
| `generate_workbook.py` | Python script that generates both files from the advanced CSV |

## Quick Start

1. **Download** [Tableau Public Desktop](https://www.tableau.com/products/public/download) (free)
2. **Open** `Feed_Operations_Dashboard.twbx` in Tableau Public
3. The data (25,919 rows, 50 feeds, 12 months) loads automatically

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────┐
│  KPI Summary (big bold numbers)                         │
│  Total Feeds Today | SLA Breaches | Avg Delay | Retries │
├────────────────────────────┬────────────────────────────┤
│  Today's Feed Status       │  Weekly Trend              │
│  (bar chart by feed,       │  (line chart of feed       │
│   colored by health)       │   health over 7 days)      │
├────────────────────────────┬────────────────────────────┤
│  Problematic Feeds         │  SLA Breach Heatmap        │
│  (worst feeds by SLA       │  (country x date grid,     │
│   breaches & delay)        │   colored by breach count) │
├────────────────────────────┴────────────────────────────┤
│  Processing Delay Distribution                          │
│  (histogram by delay bucket)                            │
└─────────────────────────────────────────────────────────┘
```

## What's Included

### Pre-built Calculated Fields (13 total)

| Field | Description |
|-------|-------------|
| **Health Status** | `Failed` (SLA breach) / `Partial` (delay > 300 min) / `Healthy` |
| **Country** | Extracted from feed_file_prefix (e.g., `BILLING_AU` → `AU`) |
| **Source Target Diff** | `source_count - target_count` |
| **Discrepancy %** | `ABS(source - target) / source` |
| **Has Retries** | `Yes` if version > 1 |
| **Is Latest Day** | Boolean filter for "today" (max billing_date) |
| **Is Last Week** | Boolean filter for last 7 days |
| **Total Feeds Today** | LOD: count distinct feeds on latest day |
| **SLA Breaches Today** | LOD: count SLA breaches on latest day |
| **Avg Processing Delay** | LOD: average delay on latest day |
| **Feeds With Retries Today** | LOD: count feeds with version > 1 on latest day |
| **Delay Bucket** | `0-60 min` / `60-120 min` / `120-180 min` / `180-300 min` / `300+ min (Critical)` |
| **Feed Health Score** | Percentage of healthy records per feed |

### 6 Worksheets

1. **KPI Summary** — Executive-level numbers: total feeds, SLA breaches, avg delay, retries
2. **Today's Feed Status** — Per-feed bar chart with health color coding
3. **Weekly Trend** — Line chart showing feed volume and SLA breaches over 7 days
4. **Problematic Feeds** — Bar chart ranking feeds by SLA breaches and delay
5. **SLA Breach Heatmap** — Country × date grid colored by breach intensity
6. **Delay Distribution** — Histogram of processing delays by bucket

### Tooltips

All charts include tooltips showing:
- Source count vs Target count
- Processing delay (minutes)
- SLA breach status
- Source-target discrepancy

## Color Scheme

After opening in Tableau, assign these colors to the **Health Status** field:

| Status | Color | Hex |
|--------|-------|-----|
| Healthy | 🟢 Green | `#22B14C` |
| Partial | 🟡 Amber | `#FF7F27` |
| Failed | 🔴 Red | `#ED1C24` |

**How to assign:** Right-click the Health Status color legend → Edit Colors → click each value and assign the color above.

## Formatting Guide

After opening, apply these formatting tweaks for the best look:

1. **KPI Summary**: Select the numbers → Format → Font → size 24+, Bold
2. **Background**: Format → Shading → White
3. **Gridlines**: Format → Lines → Grid Lines → Light Gray
4. **Dashboard title**: Double-click title → "Feed Operations Dashboard" → Bold, size 18

## Regenerating the Workbook

If the CSV data changes, regenerate the workbook:

```bash
cd tableau
python generate_workbook.py
```

This recreates both `.twb` and `.twbx` files using the latest `billing_feed_data_advanced.csv`.

## Questions This Dashboard Answers

| Question | Where to Look |
|----------|---------------|
| "What's happening today?" | KPI Summary + Today's Feed Status |
| "What changed in the last week?" | Weekly Trend |
| "What's normal vs abnormal?" | Delay Distribution + Health Status colors |
| "Which feeds/countries are problematic?" | Problematic Feeds + SLA Breach Heatmap |
