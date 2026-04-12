# Testing Feed Query UI

## Overview
Feed Query UI is a React + FastAPI + PySpark app that converts natural language questions to SparkSQL via OpenAI and executes them against a Hive table loaded from CSV.

## Devin Secrets Needed
- `OPENAI_API_KEY` — OpenAI API key with credits (gpt-4o-mini costs ~$0.01 per query)

## Local Setup

### Backend
```bash
cd backend
pip install poetry
poetry install --no-root
OPENAI_API_KEY=$OPENAI_API_KEY poetry run fastapi dev app/main.py --port 8000
```
- Backend takes ~30 seconds to start (Spark session initialization + CSV loading)
- Wait for `Application started successfully` in logs before testing
- Verify with: `curl -s http://localhost:8000/api/schema`

### Frontend
```bash
cd frontend
npm install
npm run dev
```
- Frontend runs at http://localhost:5173
- Check for "Backend Connected" badge in top-right corner

## Testing Workflow

1. **Schema verification**: Expand the schema panel (click "Table: billing_feed_data") and verify all expected columns are listed with correct types
2. **Suggestion chips**: Click each suggestion chip to populate the input, then click send. Each should generate valid SQL and return results (or "No results" without errors)
3. **SQL toggle**: After a query returns, click "Show generated SQL" to verify the SQL is valid and uses correct column names/types
4. **Error handling**: If OpenAI returns an error (e.g., rate limit), it should display in a red error banner

## Known Behaviors
- "today" or "current day" queries use `MAX(billing_date)` from the data as reference date (not actual current date), since this is historical data
- `sla_breach` is a boolean column — SQL should use `sla_breach = true` not string comparison
- "No results found" without an error banner is a valid outcome (e.g., no SLA breaches on the last date in the dataset)
- Complex queries (GROUP BY + HAVING) may occasionally fail due to SparkSQL HAVING clause restrictions — the system prompt has rules to guide the LLM, but it's not guaranteed
- If the LLM generates placeholder values like `<your_feed_id>`, there's a server-side retry mechanism that catches and retries up to 2 times

## Dataset
- Advanced dataset: `backend/data/billing_feed_data_advanced.csv` (~25,919 rows, 50 feeds, 50 countries)
- Key columns: `feed_id`, `billing_date`, `source_count`, `target_count`, `file_count`, `ingestion_time`, `processing_delay_min`, `update_dt`, `sla_breach`, `version`, `version_type`, `version_status`, `feed_file_prefix`
- Date range: 2025-01-01 to 2025-12-31
- Feed IDs: 4001-4050

## Common Issues
- If `poetry install` fails with Python version errors, ensure FastAPI is pinned to `<0.129.0` and PySpark to `<4.1.0` for Python 3.9 compatibility
- If backend fails to start, check that Java is installed (`java -version`) — PySpark requires JDK 8, 11, or 17
- The `.env` file in the backend directory should contain `OPENAI_API_KEY=<key>`
- Use `--no-root` flag with `poetry install` if there's no README.md in the backend directory
