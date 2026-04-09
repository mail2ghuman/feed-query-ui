# Feed Query UI

A React + FastAPI application that lets you ask natural language questions about batch feed data. Questions are converted to SQL using OpenAI and executed against a PySpark/Hive table.

## Architecture

```
User types question → React UI → FastAPI /api/ask → OpenAI (text-to-SQL) → PySpark/HiveQL → Results → React UI
```

- **Frontend**: React + TypeScript + Tailwind CSS (Vite)
- **Backend**: Python FastAPI + PySpark (with Hive support) + OpenAI API
- **Data**: CSV loaded into a local Hive-managed table via PySpark

## Prerequisites (macOS)

1. **Python 3.9+**
   ```bash
   python3 --version
   ```

2. **Java 11 or 17** (required by PySpark)
   ```bash
   java -version
   # If not installed:
   brew install openjdk@11
   ```

3. **PySpark**
   ```bash
   pip3 install pyspark
   ```

4. **Node.js 18+**
   ```bash
   node --version
   # If not installed:
   brew install node
   ```

5. **OpenAI API Key**
   - Get one from https://platform.openai.com/api-keys

## Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/mail2ghuman/feed-query-ui.git
cd feed-query-ui
```

### 2. Start the Backend
```bash
cd backend

# Install Python dependencies
pip3 install poetry
poetry install

# Create .env file with your OpenAI key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Or export directly:
export OPENAI_API_KEY=your-key-here

# Start the FastAPI server
poetry run fastapi dev app/main.py
```

The backend will:
- Start a local PySpark session with Hive support
- Load `data/billing_feed_data.csv` into a Hive table
- Serve the API at http://localhost:8000

### 3. Start the Frontend
```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Open http://localhost:5173 in your browser.

## Sample Questions

- "Was feed 4001 generated today?"
- "Show monthly volume for each feed"
- "List all files generated on the latest day"
- "Which feeds had INACTIVE versions?"
- "Show total source count by feed for January 2025"
- "How many FULL vs INCR versions were created?"

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/healthz` | Health check |
| GET | `/api/schema` | Get table schema |
| POST | `/api/ask` | Ask a natural language question |
| GET | `/api/sample` | Get sample data (10 rows) |

## Project Structure

```
feed-query-ui/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app with endpoints
│   │   ├── spark_manager.py   # PySpark session & Hive table management
│   │   └── query_engine.py    # OpenAI text-to-SQL + query execution
│   ├── data/
│   │   └── billing_feed_data.csv  # Sample data (~18K records)
│   ├── .env.example
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Main app component
│   │   ├── api.ts             # API client
│   │   ├── types.ts           # TypeScript types
│   │   └── components/
│   │       ├── QueryInput.tsx  # Question input with suggestions
│   │       ├── ChatMessage.tsx # Chat message display
│   │       ├── ResultTable.tsx # Query results table
│   │       ├── SchemaPanel.tsx # Table schema viewer
│   │       └── StatusBadge.tsx # Backend connection status
│   └── .env
└── README.md
```

## Moving to a Real Cluster

When deploying to your Hadoop cluster, change:

1. **Spark master**: `SparkSession.builder.master("yarn")` in `spark_manager.py`
2. **Data path**: Point to `hdfs://...` instead of local CSV
3. **Hive metastore**: Use your cluster's Hive metastore URI instead of local Derby
4. **PyHive** (optional): Replace PySpark with PyHive if you prefer direct Hive connectivity
