import os


class DatabaseConfig:
    def __init__(self) -> None:
        """
        Contains all the configurations related to the database
        """
        self.DIALECT = {"apache_pinot": "Apache Pinot SQL (MYSQL_ANSI dialect)"}
        self.TEXT_TO_SQL_PROMPT_TEMPLATE = """Apache Pinot is a real-time distributed OLAP datastore designed to answer OLAP queries with low latency. Writing SQL queries for Pinot is somewhat similar to standard SQL, but with some differences due to Pinot's architecture and optimizations.
1. In Apache Pinot SQL:
    - Double quotes(") are used to force string identifiers, e.g. column name.
    - Single quotes(') are used to enclose string literals.
    Mis-using those might cause unexpected query results:
    E.g.
    - WHERE a='b' means the predicate on the column a equals to a string literal value 'b'
    - WHERE a="b" means the predicate on the column a equals to the value of the column b
2. Apache Pinot doesn't currently support injecting functions.  Functions have to be implemented within Pinot
3. Use `now` function to get the current time as epoch millis.
4. Use `DATETIMECONVERT` function to Converts the value from a column that contains a timestamp into another time unit and buckets based on the given time granularity.
5. Use `DATETRUNC` function to Converts the value into a specified output granularity seconds since UTC epoch that is bucketed on a unit in a specified timezone.
6. Pinot’s SQL parser only accepts the plain-ASCII operators >= and <=."""
        self.DATABASE_INFORMATION_PROMPT_TEMPLATE = """"""


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
        # self.SQL_SERVER = "localhost"
        # self.SQL_USERNAME = "admin"
        # self.SQL_PASSWORD = "VMKSfewtWzad"
        # self.SQL_DATABASE = "postgres"
        # self.SQL_PORT = 5432

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
            "columnIsPrimaryKey",
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
