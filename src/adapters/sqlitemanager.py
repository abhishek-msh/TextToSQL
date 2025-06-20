import pyodbc
import pandas as pd
from sqlalchemy import text
from sqlalchemy import create_engine
from pandas.core.api import DataFrame
from sqlalchemy.exc import TimeoutError, ResourceClosedError, SQLAlchemyError
from config import SqlConfig
from src.adapters.loggingmanager import logger


# disabling pyodbc default pooling
pyodbc.pooling = False


class SQLiteManager(SqlConfig):
    """
    SQLiteManager class for managing SQL operations.

    This class provides methods for establishing a connection to a SQL Server,
    inserting data from a DataFrame into a SQL table, and fetching data from the database.

    Attributes:
        engine (sqlalchemy.engine.Engine): The SQLAlchemy engine object for executing SQL queries.

    Inherits:
        SqlConfig: A base class for SQL Server configuration.

    Methods:
        __init__(): Initializes the SQLiteManager class.
        insert_data(): Inserts data from a DataFrame into a SQL table.
        fetch_data(): Fetches data from the database using the provided SQL query.
        execute_query(): Executes a SQL query.
    """

    def __init__(self):
        """
        Initializes the SQLiteManager class.

        This method establishes a connection to the SQL Server using the provided credentials.
        It creates a SQLAlchemy engine object for executing SQL queries.

        Raises:
            TimeoutError: If a timeout occurs while establishing the connection.
            Exception: If any other error occurs during the initialization process.
        """
        super().__init__()
        self.sql_error = "On-prem SQL failed"
        ## SQL Connection
        try:
            self.engine = create_engine(f"sqlite:///{self.DB_PATH}")
            logger.info("[SQLiteManager] - SQL Client initialized")
        except (TimeoutError, ResourceClosedError, SQLAlchemyError) as exce:
            logger.exception(f"[SQLiteManager] Error: {str(exce)}")
            raise
        except Exception as sqlmgr_exc:
            logger.exception(f"[SQLiteManager] Error: {str(sqlmgr_exc)}")
            raise

    def insert_data(
        self,
        transaction_id: str,
        table_name: str,
        df: DataFrame,
        if_exists: str = "append",
    ) -> bool:
        """
        Inserts data from a DataFrame into a SQL table.

        Args:
            transaction_id (str): The ID of the transaction.
            table_name (str): The name of the SQL table.
            df (DataFrame): The DataFrame containing the data to be inserted.
            if_exists (str, optional): The action to take if the table already exists. Defaults to "append".

        Returns:
            bool: True if the data is inserted successfully, False otherwise.
        """
        connection = None
        try:
            connection = self.engine.connect()
            _ = df.to_sql(
                name=table_name,
                con=connection,
                index=False,
                if_exists=if_exists,
            )
            connection.close()
            logger.info(
                f"[SQLiteManager][insert_data][{transaction_id}] - Data inserted Successfully in table {table_name}, rows affected: {_}"
            )
            return True
        except (TimeoutError, ResourceClosedError, SQLAlchemyError) as exce:
            logger.exception(
                f"[SQLiteManager][insert_data][{transaction_id}] Error: {str(exce)}"
            )
            if connection:
                connection.close()
            raise exce
        except Exception as insert_data_exc:
            logger.exception(
                f"[SQLiteManager][insert_data][{transaction_id}] Error: {str(insert_data_exc)}"
            )
            if connection:
                connection.close()
            raise insert_data_exc
        finally:
            if connection:
                connection.close()

    def fetch_data(self, transaction_id: str, sql_query: str) -> DataFrame:
        """
        Fetches data from the database using the provided SQL query.

        Args:
            transaction_id (str): The ID of the transaction.
            sql_query (str): The SQL query to execute.

        Returns:
            DataFrame: A pandas DataFrame containing the fetched data.

        Raises:
            Exception: If there is an error while fetching the data.
        """
        connection = None
        try:
            connection = self.engine.connect()
            df = pd.read_sql(sql=text(sql_query), con=connection)
            connection.close()
            logger.info(
                f"[SQLiteManager][fetch_data][{transaction_id}] - Data Fetched Successfully"
            )
            return df
        except (TimeoutError, ResourceClosedError, SQLAlchemyError) as exce:
            logger.exception(
                f"[SQLiteManager][insert_data][{transaction_id}] Error: {str(exce)}"
            )
            if connection:
                connection.close()
            raise exce
        except Exception as insert_data_exc:
            logger.exception(
                f"[SQLiteManager][insert_data][{transaction_id}] Error: {str(insert_data_exc)}"
            )
            if connection:
                connection.close()
            raise insert_data_exc
        finally:
            if connection:
                connection.close()

    def execute_query(
        self, transaction_id: str, sql_query: str, params: dict = None
    ) -> bool:
        """
        Execute a sql command

        Args:
            transaction_id: Unique ID for the transaction
            sql_query: The SQL query to execute
            params: Optional dictionary of parameters for the SQL query
        Returns:
            True if the command executed succesfully, else false
        """
        connection = None
        try:
            connection = self.engine.connect()
            with connection.begin():  # Ensures transaction is committed properly
                if params:
                    connection.execute(
                        text(sql_query), params
                    )  # Use parameterized query
                else:
                    connection.execute(
                        text(sql_query)
                    )  # Execute without parameters if none provided

            logger.info(
                f"[SQLiteManager][execute_query][{transaction_id}] - query executed successfully"
            )
            return True
        except (TimeoutError, ResourceClosedError, SQLAlchemyError) as exce:
            logger.exception(
                f"[SQLiteManager][execute_query][{transaction_id}] Error: {str(exce)}"
            )
            raise exce
        except Exception as insert_data_exc:
            logger.exception(
                f"[SQLiteManager][execute_query][{transaction_id}] Error: {str(insert_data_exc)}"
            )
            raise insert_data_exc
        finally:
            if connection:
                connection.close()


sql_manager = SQLiteManager()
