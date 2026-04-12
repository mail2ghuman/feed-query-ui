import logging
import re

from openai import OpenAI

from app.spark_manager import SparkManager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a SQL expert assistant. You generate SparkSQL/HiveQL queries based on user questions.

You have access to ONE table called `billing_feed_data` with the following schema:

| Column | Type | Description |
|--------|------|-------------|
| feed_id | int | Unique identifier for the feed (4001-4050) |
| billing_date | date | The billing/processing date (2025-01-01 to 2025-12-31) |
| source_count | int | Number of source records |
| target_count | int | Number of target records |
| file_count | int | Number of files generated |
| ingestion_time | timestamp | When the data was first ingested into the pipeline |
| processing_delay_min | int | Minutes between ingestion and completion (high values indicate slow/stuck pipelines) |
| update_dt | timestamp | When the record was last updated (completion time) |
| sla_breach | boolean | True if the feed breached its SLA for that day |
| version | int | Version number of the feed run (1 = first attempt, 2+ = retries) |
| version_type | string | Type of version: FULL or INCR (incremental) |
| version_status | string | Status: ACTIVE (current valid version) or INACTIVE (superseded/failed) |
| feed_file_prefix | string | Prefix identifying the feed region (e.g., BILLING_AU = Australia, BILLING_US = United States) |

Important context:
- There are 50 feeds (feed_id 4001-4050) covering 50 countries/regions
- Each feed_id + billing_date can have multiple versions (1, 2, 3, etc.)
- The ACTIVE version_status indicates the currently valid version for that date
- version_type can be FULL (full refresh) or INCR (incremental update)
- feed_file_prefix identifies the feed name/region (e.g., BILLING_AU = Australia billing)
- "today" or "current day" should use the MAX(billing_date) in the data as the reference date

Scenario-specific guidance:
- SLA breaches: Use sla_breach = true to find feeds that breached their SLA. High processing_delay_min often correlates with SLA breaches.
- Processing delays: Use processing_delay_min to identify slow pipelines. Values over 300 minutes are unusually high.
- Failed pipelines with retries: Multiple versions (version > 1) for the same feed_id + billing_date indicate retries. INACTIVE versions are failed/superseded attempts; the ACTIVE version is the successful one.
- Holiday and year-end spikes: Look at source_count/target_count spikes around holidays (e.g., Dec 25, Jan 1) and month-end/year-end dates. Compare volumes to averages.
- Global incident days: When multiple feeds have SLA breaches or high processing_delay_min on the same day, that suggests a global incident. Group by billing_date and count affected feeds.

Rules:
1. ONLY output a valid SparkSQL SELECT query. No INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER.
2. Do NOT wrap the query in markdown code blocks or any other formatting.
3. Output ONLY the SQL query, nothing else.
4. Use standard SparkSQL functions (e.g., DATE_FORMAT, CURRENT_DATE, DATEDIFF, etc.)
5. When asked about "today" or "current day", use (SELECT MAX(billing_date) FROM billing_feed_data) as the reference date since this is historical data.
6. When asked about monthly volumes, group by year-month using DATE_FORMAT(billing_date, 'yyyy-MM').
7. When filtering for ACTIVE feeds, use version_status = 'ACTIVE'.
8. Keep queries efficient with appropriate filters and limits where sensible.
9. SparkSQL HAVING clauses can ONLY reference columns that appear in the SELECT list or aggregate expressions. Do NOT reference raw columns that were transformed or aliased in the GROUP BY. Use a subquery or CTE if you need to filter on both aggregated and non-aggregated columns.
10. Prefer using subqueries or CTEs (WITH clauses) over HAVING when filtering requires access to original column values after aggregation.
11. NEVER use placeholders like <your_feed_id>, <feed_name>, {feed_id}, etc. If the user's question does not specify a particular feed or value, query ALL feeds and return the results. If the question mentions a feed by name (e.g., "BILLING_AU"), use feed_file_prefix = 'BILLING_AU'. If by number, use feed_id = that number. The query must always be directly executable without any manual substitution.
12. For boolean columns (sla_breach), use sla_breach = true or sla_breach = false (not string comparisons).
"""


class QueryEngine:
    """Converts natural language questions to SQL using OpenAI, then executes via Spark."""

    def __init__(
        self,
        spark_manager: SparkManager,
        openai_api_key: str,
        openai_model: str = "gpt-4o-mini",
    ):
        self.spark_manager = spark_manager
        self.openai_model = openai_model
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else None

    _PLACEHOLDER_RE = re.compile(r"<[a-zA-Z_]+>|\{[a-zA-Z_]+\}")
    _MAX_RETRIES = 2

    @staticmethod
    def _clean_sql_response(sql: str) -> str:
        """Remove markdown code blocks and whitespace from LLM response."""
        sql = sql.strip()
        sql = re.sub(r"^```(?:sql)?\s*", "", sql)
        sql = re.sub(r"\s*```$", "", sql)
        return sql.strip()

    def _generate_sql(
        self,
        question: str,
        conversation_history: list[dict] | None = None,
    ) -> str:
        """Use OpenAI to convert a natural language question to SQL.

        Detects placeholder tokens (e.g. <your_feed_id>) in the generated SQL
        and retries with explicit correction feedback.
        """
        if self.client is None:
            raise RuntimeError(
                "OpenAI API key not configured. Set the OPENAI_API_KEY environment variable."
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        # Include conversation history so the LLM can handle follow-up questions
        for entry in (conversation_history or []):
            messages.append({"role": "user", "content": entry["question"]})
            messages.append({"role": "assistant", "content": entry["sql"]})

        messages.append({"role": "user", "content": question})

        for attempt in range(self._MAX_RETRIES + 1):
            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                temperature=0,
                max_tokens=500,
            )

            sql = response.choices[0].message.content
            if sql is None:
                raise RuntimeError("OpenAI returned empty response")

            sql = self._clean_sql_response(sql)

            # Check for placeholder tokens
            placeholders = self._PLACEHOLDER_RE.findall(sql)
            if not placeholders:
                return sql

            if attempt < self._MAX_RETRIES:
                logger.warning(
                    "Attempt %d: LLM produced placeholders %s, retrying",
                    attempt + 1,
                    placeholders,
                )
                messages.append({"role": "assistant", "content": sql})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Your SQL contains placeholder tokens {placeholders} which are not valid SQL. "
                        "Replace them with actual values from the data. If the user did not specify "
                        "a particular feed, remove the WHERE clause and query all feeds. "
                        "Output only the corrected SQL query."
                    ),
                })

        # All retries exhausted — still has placeholders
        raise ValueError(
            f"Could not generate executable SQL. The query contains placeholder "
            f"values {placeholders} that need to be replaced with actual feed IDs "
            f"or names. Please rephrase your question and specify which feed you "
            f"mean (e.g., 'feed 4001' or 'BILLING_AU'), or ask about all feeds."
        )

    @staticmethod
    def _strip_sql_strings_and_comments(sql: str) -> str:
        """Single-pass tokenizer that strips string literals and comments from SQL.

        Processes the SQL left-to-right, correctly handling the interaction
        between string literals, block comments, and line comments. Returns
        only the structural SQL with string contents replaced by empty strings.
        """
        result = []
        i = 0
        length = len(sql)
        while i < length:
            # Block comment: /* ... */
            if sql[i:i + 2] == "/*":
                end = sql.find("*/", i + 2)
                if end == -1:
                    break  # unclosed block comment, skip rest
                i = end + 2
                result.append(" ")
            # Line comment: -- ...
            elif sql[i:i + 2] == "--":
                end = sql.find("\n", i + 2)
                if end == -1:
                    break  # rest of string is a comment
                i = end + 1
                result.append(" ")
            # String literal: '...' (with '' as escaped quote)
            elif sql[i] == "'":
                i += 1
                while i < length:
                    if sql[i] == "'" and i + 1 < length and sql[i + 1] == "'":
                        i += 2  # skip escaped quote ''
                    elif sql[i] == "'":
                        i += 1
                        break
                    else:
                        i += 1
                result.append("''")  # replace string content with empty string
            else:
                result.append(sql[i])
                i += 1
        return "".join(result)

    @staticmethod
    def _validate_sql(sql: str) -> None:
        """Basic validation to prevent destructive queries."""
        forbidden = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
            "TRUNCATE",
            "GRANT",
            "REVOKE",
        ]
        sql_clean = QueryEngine._strip_sql_strings_and_comments(
            sql.upper().strip()
        ).strip()
        # Must start with SELECT or WITH (defense-in-depth against non-SELECT commands)
        if not sql_clean.startswith("SELECT") and not sql_clean.startswith("WITH"):
            raise ValueError("Only SELECT queries are allowed.")
        for keyword in forbidden:
            if re.search(rf"\b{keyword}\b", sql_clean):
                raise ValueError(
                    f"Destructive SQL operation '{keyword}' is not allowed."
                )
        # Strip trailing semicolons (LLMs commonly add them), then reject multi-statement SQL
        sql_clean = sql_clean.rstrip(";").strip()
        if ";" in sql_clean:
            raise ValueError("Multiple SQL statements are not allowed.")

    def ask(
        self,
        question: str,
        conversation_history: list[dict] | None = None,
    ) -> dict:
        """Process a natural language question: generate SQL, validate, execute, return results."""
        generated_sql = ""
        try:
            generated_sql = self._generate_sql(question, conversation_history)
            logger.info("Generated SQL for '%s': %s", question, generated_sql)

            self._validate_sql(generated_sql)

            rows = self.spark_manager.execute_query(generated_sql)
            columns = list(rows[0].keys()) if rows else []

            # Convert any non-serializable types to strings
            clean_rows = []
            for row in rows:
                clean_row = {}
                for k, v in row.items():
                    if v is None:
                        clean_row[k] = None
                    elif isinstance(v, (int, float, str, bool)):
                        clean_row[k] = v
                    else:
                        clean_row[k] = str(v)
                clean_rows.append(clean_row)

            return {
                "question": question,
                "generated_sql": generated_sql,
                "columns": columns,
                "rows": clean_rows,
                "row_count": len(clean_rows),
                "error": None,
            }
        except Exception as e:
            logger.error("Error processing question '%s': %s", question, str(e))
            return {
                "question": question,
                "generated_sql": generated_sql,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e),
            }
