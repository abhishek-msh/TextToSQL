import os
import json


class DatabaseConfig:
    def __init__(self) -> None:
        """
        Contains all the configurations related to the database
        """
        self.DIALECT = {"postgresql": "PostgreSQL"}
        self.TEXT_TO_SQL_PROMPT_TEMPLATE = """PostgreSQL is a powerful, standards-compliant relational database that adds many modern extensions. Keep these quick tips in mind when crafting SQL:

1. Identifier vs literal quoting
   • Double quotes (") preserve case and allow reserved words as identifiers  
     ⇒ SELECT "users", "orderTotal" FROM sales;  
   • Single quotes (') delimit string literals  
     ⇒ WHERE status = 'shipped';  
     Mis-quoting (e.g. WHERE a="b") will make PostgreSQL look for a column called b instead of the string 'b'.

2. Extensibility & SQL-injection safety
   • PostgreSQL supports user-defined functions and procedures via CREATE FUNCTION/PROCEDURE in PL/pgSQL, SQL, Python (PL/Python), etc.  
   • Always use **parameterized queries** (e.g. psycopg placeholders %s) instead of string concatenation to avoid injection attacks.

3. Current time & epoch conversion
   • now() and current_timestamp return TIMESTAMP WITH TIME ZONE.  
   • EXTRACT(EPOCH FROM now()) * 1000 gives epoch-milliseconds if you need Unix time

4. Time-zone handling & bucketing
   • Use AT TIME ZONE to convert: created_at AT TIME ZONE 'UTC' AS created_utc  
   • Use date_trunc('hour', ts) or date_trunc('day', ts) to bucket timestamps.  
   • Combine with now(): date_trunc('day', now()) for “today” rounded to midnight.

5. Time-series scaffolding
   • generate_series(start_ts, end_ts, interval '1 hour') produces gap-free rows; LEFT JOIN it with aggregates to expose missing periods.

6. Statistics & percentiles
   • percentile_cont(p) WITHIN GROUP (ORDER BY val) → continuous percentile  
   • percentile_disc(p) for discrete values.  
   • For large, streaming data use extensions such as **tdigest_agg** or **approx_percentile** (in pg_partman/Timescale Toolkit) for faster, memory-bound summaries.

7. Performance diagnostics
   • Use EXPLAIN (ANALYZE, BUFFERS) to see the real plan and costs.  
   • Choose the right index: B-tree (default) for equality/range, GIN for jsonb/array containment, GiST for geometric/range types, BRIN for huge append-only tables.

Following these conventions will help you write clear, efficient, and secure PostgreSQL queries that take full advantage of the database’s rich feature set."""

        # 6. Quote the table in double-quotes and give everything an alias—the join works and the query is easy to read.

        self.DATABASE_INFORMATION_PROMPT_TEMPLATE = ""
        with open("data/5DayDatabaseInformation.txt", "r") as file:
            self.DATABASE_INFORMATION_PROMPT_TEMPLATE = file.read()

        with open("data/tableRelationships.json", "r") as file:
            self.TABLE_RELATIONSHIPS = json.load(file)

        with open("data/databaseRelationshipsDescription.json", "r") as file:
            self.DATABASE_RELATIONSHIPS_DESCRIPTION = json.load(file)


class OpenAIConfig:
    def __init__(self) -> None:
        """
        Contains:
            1. Credentials needed to estabalish connection with OpenAI API
        """
        ### Openai
        self.OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")

        self.CHATCOMPLETION_MODEL = os.getenv("CHATCOMPLETION_MODEL")
        self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
        self.MAX_RETRIES = int(os.getenv("MAX_RETRIES"))

        self.TEMPERATURE = float(os.getenv("TEMPERATURE"))


class SqlConfig:
    def __init__(self) -> None:
        """
        Contains all the configurations related to the SQL server
        """
        # Credentials
        self.SQL_SERVER = ""
        self.SQL_USERNAME = ""
        self.SQL_PASSWORD = ""
        self.SQL_DATABASE = ""
        self.SQL_PORT = 5432

        self.DB_PATH = os.getenv("DB_PATH")
        self.CONVERSATION_ANALYTICS_TABLE = os.getenv("CONVERSATION_ANALYTICS_TABLE")
        self.RETRIEVAL_HISTORY_TABLE = os.getenv("RETREIVAL_HISTORY_TABLE")


class MilvusConfig:
    def __init__(self) -> None:
        """
        Contains all the configurations related to the Milvus server
        """
        # Credentials
        self.MILVUS_HOST = os.getenv("MILVUS_HOST")
        self.MILVUS_PORT = os.getenv("MILVUS_PORT")

        self.MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME")
        self.MILVUS_DB_NAME = os.getenv("MILVUS_DB_NAME")
        self.MILVUS_TIMEOUT = int(os.getenv("MILVUS_TIMEOUT"))
        # Index parameters
        self.MILVUS_VECTOR_DIM = int(os.getenv("MILVUS_VECTOR_DIM"))
        self.MILVUS_INDEX_TYPE = os.getenv("MILVUS_INDEX_TYPE")
        self.MILVUS_INDEX_PARAMS = {
            "M": os.getenv("MILVUS_INDEX_PARAM_M"),
            "EFConstruction": os.getenv("MILVUS_INDEX_PARAM_EFCONSTRUCTION"),
        }
        self.MILVUS_DISTANCE_METRIC = os.getenv("MILVUS_DISTANCE_METRIC")

        self.MILVUS_TABLE_COLLECTION_NAME = os.getenv("MILVUS_TABLE_COLLECTION_NAME")
        self.MILVUS_COLUMN_COLLECTION_NAME = os.getenv("MILVUS_COLUMN_COLLECTION_NAME")
        self.MILVUS_SQL_EXAMPLE_COLLECTION_NAME = os.getenv("MILVUS_SQL_EXAMPLE_COLLECTION_NAME")

        self.MILVUS_TABLE_RETURN_FIELDS = ["tableName"]
        self.MILVUS_COLUMN_RETURN_FIELDS = [
            "tableName",
            "columnName",
            "columnDescription",
            "columnDataType",
            "columnSampleValue",
        ]
        self.MILVUS_SQL_EXAMPLE_RETURN_FIELDS = [
            "question",
            "sqlQuery",
        ]

        self.MILVUS_TOP_TABLES_K = os.getenv("MILVUS_TOP_TABLES_K")
        self.MILVUS_TOP_COLUMNS_K = os.getenv("MILVUS_TOP_COLUMNS_K")
        self.MILVUS_TOP_SQL_EXAMPLES_K = os.getenv("MILVUS_TOP_SQL_EXAMPLES_K")


class PinotConfig:
    def __init__(self) -> None:
        """
        Contains all the configurations related to the Pinot server
        """
        # Credentials
        self.PINOT_SERVER = os.getenv("PINOT_SERVER")
        self.PINOT_DATABASE = os.getenv("PINOT_DATABASE")
        self.PINOT_BROKER_PORT = os.getenv("PINOT_BROKER_PORT")
        self.PINOT_CONTROLLER_PORT = os.getenv("PINOT_CONTROLLER_PORT")


class OllamaConfig:
    def __init__(self) -> None:
        """
        Contains all the configurations related to the Ollama server
        """
        # Credentials
        self.OLLAMA_SERVER = os.getenv("OLLAMA_SERVER")
        self.OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
        self.TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE"))
