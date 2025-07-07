import pyodbc
import pandas as pd
from sqlalchemy import text
from config import SqlConfig
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from pandas.core.api import DataFrame
from src.custom_exception import CustomException
from src.adapters.loggingmanager import logger
from sqlalchemy.exc import TimeoutError, ResourceClosedError, SQLAlchemyError
import datetime
from src.decorators import measure_time

# disabling pyodbc default pooling
pyodbc.pooling = False


class SQLManager(SqlConfig):
    """
    SQLManager class for managing SQL operations.

    This class provides methods for establishing a connection to a SQL Server,
    inserting data from a DataFrame into a SQL table, and fetching data from the database.

    Attributes:
        engine (sqlalchemy.engine.Engine): The SQLAlchemy engine object for executing SQL queries.

    Inherits:
        SqlConfig: A base class for SQL Server configuration.

    Methods:
        __init__(): Initializes the SQLManager class.
        insert_data(): Inserts data from a DataFrame into a SQL table.
        fetch_data(): Fetches data from the database using the provided SQL query.
    """

    def __init__(self):
        """
        Initializes the SQLManager class.

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
            connection_string = f"postgresql://{self.SQL_USERNAME}:{quote_plus(self.SQL_PASSWORD)}@{self.SQL_SERVER}:{self.SQL_PORT}/{self.SQL_DATABASE}"
            self.engine = create_engine(
                connection_string, pool_pre_ping=True, pool_size=5, pool_recycle=1500
            )
            logger.info("[SQLManager] - SQL Client initialized")
        except (TimeoutError, ResourceClosedError, SQLAlchemyError) as exce:
            logger.exception(f"[SQLManager] Error: {str(exce)}")
            raise
        except Exception as sqlmgr_exc:
            logger.exception(f"[SQLManager] Error: {str(sqlmgr_exc)}")
            raise

    def insert_data(
        self,
        transaction_id: str,
        table_name: str,
        df: DataFrame,
        schema: str = "dbo",
        if_exists: str = "append",
    ) -> bool:
        """
        Inserts data from a DataFrame into a SQL table.

        Args:
            transaction_id (str): The ID of the transaction.
            table_name (str): The name of the SQL table.
            df (DataFrame): The DataFrame containing the data to be inserted.
            schema (str, optional): The schema of the SQL table. Defaults to "dbo".
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
                schema=schema,
                index=False,
                if_exists=if_exists,
            )
            connection.close()
            logger.info(
                f"[SQLManager][insert_data][{transaction_id}] - Data inserted Successfully in table {table_name}, rows affected: {_}"
            )
            return True
        except (TimeoutError, ResourceClosedError, SQLAlchemyError) as exce:
            logger.exception(
                f"[SQLManager][insert_data][{transaction_id}] Error: {str(exce)}"
            )
            if connection:
                connection.close()

            raise CustomException(error=self.sql_error, message=str(exce))
        except Exception as insert_data_exc:
            logger.exception(
                f"[SQLManager][insert_data][{transaction_id}] Error: {str(insert_data_exc)}"
            )
            if connection:
                connection.close()

            raise CustomException(error=self.sql_error, message=str(insert_data_exc))
        finally:
            if connection:
                connection.close()

    @measure_time
    def fetch_data(self, transaction_id: str, sql_query: str) -> DataFrame:
        """
        Fetches data from the database using the provided SQL query.

        Args:
            transaction_id (str): The ID of the transaction.
            sql_query (str): The SQL query to execute.

        Returns:
            DataFrame: A pandas DataFrame containing the fetched data.

        Raises:
            CustomException: If there is an error while fetching the data.
        """
        connection = None
        try:
            # Attempt with multistage engine first
            connection = self.engine.connect()
            multistage_query = f"SET useMultistageEngine=true; {sql_query}"
            connection = connection.execution_options(
                use_multistage_engine=True,
                queryOptions="useMultistageEngine=true",
            )
            df = pd.read_sql(
                sql=text(multistage_query), con=connection, parse_dates=True
            )
            logger.info(
                f"[SQLManager][fetch_data][{transaction_id}] - Data fetched successfully with multistage"
            )
            return df
        except Exception as multistage_exc:
            logger.warning(
                f"[SQLManager][fetch_data][{transaction_id}] Multistage query failed: {str(multistage_exc)}"
            )
            if connection:
                connection.close()

            try:
                # Retry without multistage
                connection = self.engine.connect()
                df = pd.read_sql(sql=text(sql_query), con=connection)
                logger.info(
                    f"[SQLManager][fetch_data][{transaction_id}] - Data fetched successfully without multistage"
                )
                return df
            except Exception as fetch_data_exc:
                logger.exception(
                    f"[SQLManager][fetch_data][{transaction_id}] General Error: {str(fetch_data_exc)}"
                )
                raise CustomException(
                    error=self.sql_error, message=str(fetch_data_exc), result=[]
                )
            finally:
                if connection:
                    connection.close()
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
                f"[SQLManager][execute_query][{transaction_id}] - query executed successfully"
            )
            return True
        except (TimeoutError, ResourceClosedError, SQLAlchemyError) as exce:
            logger.exception(
                f"[SQLManager][execute_query][{transaction_id}] Error: {str(exce)}"
            )
            if connection:
                connection.close()

            raise CustomException(error=self.sql_error, message=str(exce), result=[])
        except Exception as insert_data_exc:
            logger.exception(
                f"[SQLManager][execute_query][{transaction_id}] Error: {str(insert_data_exc)}"
            )

            raise CustomException(
                error=self.sql_error, message=str(insert_data_exc), result=[]
            )
        finally:
            if connection:
                connection.close()
        return False


sql_manager = SQLManager()
