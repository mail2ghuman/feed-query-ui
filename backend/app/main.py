from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.spark_manager import SparkManager
from app.query_engine import QueryEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

spark_manager: Optional[SparkManager] = None
query_engine: Optional[QueryEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global spark_manager, query_engine
    logger.info("Starting Spark session and loading data...")
    csv_path = os.environ.get(
        "CSV_DATA_PATH",
        os.path.join(os.path.dirname(__file__), "..", "data", "billing_feed_data_advanced.csv"),
    )
    csv_path = os.path.abspath(csv_path)
    spark_manager = SparkManager(csv_path=csv_path)
    spark_manager.initialize()

    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    query_engine = QueryEngine(
        spark_manager=spark_manager,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
    )
    logger.info("Application started successfully.")
    yield
    logger.info("Shutting down Spark session...")
    spark_manager.stop()


app = FastAPI(title="Feed Query UI Backend", lifespan=lifespan)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    question: str
    generated_sql: str
    columns: list[str]
    rows: list[dict]
    row_count: int
    error: Optional[str] = None


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/api/schema")
def get_schema():
    """Return the table schema so the frontend can display it."""
    if spark_manager is None:
        raise HTTPException(status_code=503, detail="Spark not initialized")
    return {"table_name": "billing_feed_data", "columns": spark_manager.get_schema()}


@app.post("/api/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    """Accept a natural language question and return query results."""
    if query_engine is None:
        raise HTTPException(status_code=503, detail="Query engine not initialized")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    result = query_engine.ask(request.question)
    return result


@app.get("/api/sample")
def get_sample():
    """Return a sample of data from the table."""
    if spark_manager is None:
        raise HTTPException(status_code=503, detail="Spark not initialized")
    rows = spark_manager.execute_query("SELECT * FROM billing_feed_data LIMIT 10")
    schema = spark_manager.get_schema()
    return {
        "columns": [col["name"] for col in schema],
        "rows": rows,
        "row_count": len(rows),
    }
