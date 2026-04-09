import logging
import os
from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


class SparkManager:
    """Manages the Spark session and Hive table operations."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.spark: SparkSession | None = None
        self.table_name = "billing_feed_data"

    def initialize(self):
        """Create Spark session with Hive support and load CSV into a Hive table."""
        warehouse_dir = os.path.join(
            os.path.dirname(self.csv_path), "..", "spark-warehouse"
        )
        warehouse_dir = os.path.abspath(warehouse_dir)

        self.spark = (
            SparkSession.builder.appName("FeedQueryUI")
            .master("local[*]")
            .config("spark.sql.catalogImplementation", "hive")
            .config("spark.sql.warehouse.dir", warehouse_dir)
            .config("spark.driver.memory", "1g")
            .config(
                "spark.driver.extraJavaOptions",
                "-Dderby.system.home=" + warehouse_dir,
            )
            .config("spark.ui.enabled", "false")
            .enableHiveSupport()
            .getOrCreate()
        )

        # Set log level to reduce noise
        self.spark.sparkContext.setLogLevel("WARN")

        logger.info("Spark session created. Loading CSV data...")
        self._load_csv_to_hive()
        logger.info("Data loaded into Hive table '%s'.", self.table_name)

    def _load_csv_to_hive(self):
        """Read CSV and register as a Hive-managed table."""
        if self.spark is None:
            raise RuntimeError("Spark session not initialized")

        df = self.spark.read.csv(self.csv_path, header=True, inferSchema=True)
        df.write.mode("overwrite").saveAsTable(self.table_name)

        row_count = self.spark.sql(
            f"SELECT COUNT(*) as cnt FROM {self.table_name}"
        ).collect()[0]["cnt"]
        logger.info("Loaded %d rows into table '%s'.", row_count, self.table_name)

    def get_schema(self) -> list[dict]:
        """Return the schema of the Hive table as a list of dicts."""
        if self.spark is None:
            raise RuntimeError("Spark session not initialized")

        df = self.spark.table(self.table_name)
        return [
            {"name": field.name, "type": str(field.dataType)}
            for field in df.schema.fields
        ]

    def execute_query(self, sql: str) -> list[dict]:
        """Execute a SparkSQL query and return results as list of dicts."""
        if self.spark is None:
            raise RuntimeError("Spark session not initialized")

        logger.info("Executing SQL: %s", sql)
        result_df = self.spark.sql(sql)
        rows = result_df.collect()
        columns = result_df.columns
        return [
            {col: (row[col] if row[col] is not None else None) for col in columns}
            for row in rows
        ]

    def get_column_names(self) -> list[str]:
        """Return column names of the table."""
        if self.spark is None:
            raise RuntimeError("Spark session not initialized")
        return self.spark.table(self.table_name).columns

    def stop(self):
        """Stop the Spark session."""
        if self.spark:
            self.spark.stop()
            self.spark = None
            logger.info("Spark session stopped.")
