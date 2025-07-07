import pytz
import json
import pandas as pd
from datetime import datetime
from src.custom_exception import CustomException
from pydantic import BaseModel, Field, PrivateAttr, field_validator
from typing import Literal, Optional, Any, Dict, List, Optional
from src.adapters.sqlitemanager import sqlite_manager


class userFeedbackModel(BaseModel):
    """
    A Pydantic model representing user feedback.

    Attributes:
        feedback (str): Feedback provided by the user.
        previousSqlQuery (str): Previous SQL query.
    """

    feedback: str = Field(
        description="Feedback provided by the user",
    )
    previousSqlQuery: str = Field(
        description="Previous SQL query",
    )


class GetAnswerModel(BaseModel):
    """
    GetAnswerModel is a Pydantic model representing the structure of a request for obtaining an answer in the NLtoSQL system.

    Attributes:
        emailID (str): Email address of the user.
        clientName (Literal["AI-nlToSql"]): Name of the specific use case for this transaction.
        tenantId (str): Unique identifier for the tenant.
        userID (str): Unique identifier for the user.
        sessionID (str): Unique identifier for the conversation associated with this transaction.
        conversationID (str): Unique identifier for the conversation associated with this transaction.
        userText (str): The query or input provided by the user.
        date (str): Timestamp of the request in UTC format. (Format: YYYY-MM-DDTHH:MM:SS.fffZ)
        userFeedback (Optional[userFeedbackModel]): User feedback for the response provided by the bot and SQL query.

    Validators:
        date_must_be_utc: Ensures that the 'date' field is in the correct UTC format (YYYY-MM-DDTHH:MM:SS.fffZ) and represents a UTC timestamp.
    """

    emailID: str = Field(
        description="Email address of the user",
    )
    clientName: Literal["AI-nlToSql"] = Field(
        description="Name of the specific use case for this transaction."
    )
    tenantId: str = Field(
        description="Unique identifier for the tenant",
    )
    userID: str = Field(description="Unique identifier for the user")
    sessionID: str = Field(
        description="Unique identifier for the conversation associated with this transaction."
    )
    conversationID: str = Field(
        description="Unique identifier for the conversation associated with this transaction."
    )
    userText: str = Field(description="The query or input provided by the user.")
    date: str = Field(
        description="Timestamp of the request in UTC format. (Format: YYYY-MM-DDTHH:MM:SS.fffZ)"
    )
    userFeedback: Optional[userFeedbackModel] = Field(
        default=None,
        description="User feedback for the response provided by the bot and SQL query.",
    )

    @field_validator("date")
    @classmethod
    def date_must_be_utc(cls, value):
        """
        This validator ensures that the date provided is in the correct format and is in UTC.

        Args:
            value (str): The date string to be validated.

        Returns:
            str: The validated date string.
        """
        try:
            # attempt to parse the date string
            date = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
            if (date.tzinfo is not None) and (date.tzinfo != pytz.UTC):
                raise ValueError("date must be in UTC format")
            return value
        except ValueError as utc_valid_exc:
            raise ValueError(
                "Date must be in UTC format and follow the format YYYY-MM-DDTHH:MM:SS.fffZ"
            ) from utc_valid_exc


class GetFixSqlModel(BaseModel):
    """
    GetFixSqlModel is a Pydantic model representing the structure of a request for obtaining a fixed SQL query in the NLtoSQL system.

    Attributes:
        clientName (Literal["AI-nlToSql"]): Name of the specific use case for this transaction.
        tenantId (str): Unique identifier for the tenant.
        userText (str): The query or input provided by the user.
        correctSqlQuery (str): The correct SQL query provided by the user.
    """

    clientName: Literal["AI-nlToSql"] = Field(
        description="Name of the specific use case for this transaction."
    )
    tenantId: str = Field(
        description="Unique identifier for the tenant",
    )
    userText: str = Field(description="The query or input provided by the user.")
    correctSqlQuery: str = Field(
        description="The correct SQL query provided by the user.",
    )


class ConversationAnalyticsModel(GetAnswerModel):
    """
    ConversationAnalyticsModel is a data model for capturing analytics and metadata related to a user's conversation and the associated SQL query generation process.

    Attributes:
        id (str): Unique identifier for each individual transaction.
        userFeedbackFlag (bool): Flag to indicate if the user has provided feedback.
        userTextRephrased (str): Rephrased version of the user's text based on the previous conversation context.
        userTextRephrasedChatCompletionInputToken (int): Number of input tokens used for generating the rephrased query.
        userTextRephrasedChatCompletionOutputToken (int): Number of output tokens generated in the rephrased query.
        userTextRephrasedChatCompletionTime (float): Time taken to generate the rephrased query.
        userTextEmbeddingTokens (int): Number of tokens used to generate embeddings for the query.
        userTextEmbeddingGenerationTime (float): Time taken to generate embeddings for the query.
        tableVectorSearchTime (float): Time taken to perform a table vector search on the database.
        columnVectorSearchTime (float): Time taken to perform a column vector search on the database.
        SqlExampleVectorSearchTime (float): Time taken to perform a SQL example vector search on the database.
        sqlQuery (str): SQL query generated based on the user's query.
        sqlQueryChatCompletionInputToken (int): Number of input tokens used for generating the SQL query.
        sqlQueryChatCompletionOutputToken (int): Number of output tokens generated in the SQL query.
        sqlQueryChatCompletionTime (float): Time taken to generate the SQL query.
        sqlQueryExecutionTime (float): Time taken to execute the SQL query.
        sqlQueryResponse (List[dict]): Response from the SQL query execution.
        answerChatCompletionInputToken (int): Number of input tokens used for generating the answer.
        answerChatCompletionOutputToken (int): Number of output tokens generated in the answer.
        answerChatCompletionTime (float): Time taken to generate the answer.
        answer (str): Answer generated based on the SQL query response.
        graphChatCompletionTime (float): Time taken to generate the graph.
        graphChatCompletionInputToken (int): Number of input tokens used for generating the graph.
        graphChatCompletionOutputToken (int): Number of output tokens generated in the graph.
        graphGenerationCode (str): Code generated for graph generation based on the SQL query response.
        graphFigureJson (Dict[str, Any]): JSON representation of the graph figure generated based on the SQL query response.
        totalAdaCalls (int): Total number of requests made to the ADA model.
        totalChatCompletionCalls (int): Total number of requests made to the Chat Completion model.
        error (str): Any error encountered during the transaction.
        responseTime (float): Total time taken to generate and provide an answer to the user's query.

    Private Attributes:
        _start_time (datetime): Internal attribute to track the start time of the transaction.

    Methods:
        __init__(**data): Initializes a new instance of the ConversationAnalyticsModel, setting the start time.
        to_dict(): Converts the model to a dictionary, encoding any list or dictionary values as JSON strings.
        to_sql(): Converts the conversation analytics data to SQL format and inserts it into the database, updating the response time and handling errors.
    """

    id: str = Field(
        default=None, description="Unique identifier for each individual transaction."
    )
    userFeedbackFlag: bool = Field(
        default=False, description="Flag to indicate if the user has provided feedback."
    )
    userTextRephrased: str = Field(
        default=None,
        description="Rephrased version of the user's text based on the previous conversation context.",
    )
    userTextRephrasedChatCompletionInputToken: int = Field(
        default=0,
        description="Number of input tokens used for generating the rephrased query.",
    )
    userTextRephrasedChatCompletionOutputToken: int = Field(
        default=0,
        description="Number of output tokens generated in the rephrased query.",
    )
    userTextRephrasedChatCompletionTime: float = Field(
        default=0,
        description="Time taken to generate query rephrased query",
    )
    userTextEmbeddingTokens: int = Field(
        default=0,
        description="Number of tokens used to generate embeddings for the query.",
    )
    userTextEmbeddingGenerationTime: float = Field(
        default=0, description="Time taken to generate embeddings for the query."
    )
    # cacheSearchTime: float = Field(
    #     default=0, description="Time taken to search the cache for the SQL query."
    # )
    # cacheFlag: bool = Field(
    #     default=False,
    #     description="Flag to indicate if the SQL query was found in the cache.",
    # )
    # cacheUserText: str = Field(
    #     default=None,
    #     description="User text found in the cache.",
    # )
    # cacheSqlQuery: str = Field(
    #     default=None,
    #     description="SQL query found in the cache.",
    # )
    # cacheSqlQueryResponse: List[dict] = Field(
    #     default=None,
    #     description="Response from the SQL query found in the cache.",
    # )
    # cacheRelevanceScore: float = Field(
    #     default=0, description="Score of the User Text found in the cache."
    # )
    tableVectorSearchTime: float = Field(
        default=0,
        description="Time taken to perform a table vector search on database.",
    )
    columnVectorSearchTime: float = Field(
        default=0,
        description="Time taken to perform a column vector search on database.",
    )
    sqlExampleVectorSearchTime: float = Field(
        default=0,
        description="Time taken to perform a SQL example vector search on database.",
    )
    # greetingFlag: bool = Field(
    #     default=False, description="Flag to indicate if the user's query is a greeting."
    # )
    # greetingResponse: str = Field(
    #     default=None, description="Response to the user's greeting."
    # )
    sqlQuery: str = Field(
        default=None,
        description="SQL query generated based on the user's query.",
    )
    sqlQueryChatCompletionInputToken: int = Field(
        default=0,
        description="Number of input tokens used for generating the SQL query.",
    )
    sqlQueryChatCompletionOutputToken: int = Field(
        default=0,
        description="Number of output tokens generated in the SQL query.",
    )
    sqlQueryChatCompletionTime: float = Field(
        default=0,
        description="Time taken to generate the SQL query.",
    )
    sqlQueryExecutionTime: float = Field(
        default=0, description="Time taken to execute the SQL query."
    )
    sqlQueryResponse: Any = Field(
        default=None,
        description="Response from the SQL query execution.",
    )
    answerChatCompletionInputToken: int = Field(
        default=0,
        description="Number of input tokens used for generating the answer.",
    )
    answerChatCompletionOutputToken: int = Field(
        default=0, description="Number of output tokens generated in the answer."
    )
    answerChatCompletionTime: float = Field(
        default=0, description="Time taken to generate the answer."
    )
    answer: str = Field(
        default=None, description="Answer generated based on the SQL query response."
    )
    graphChatCompletionTime: float = Field(
        default=0, description="Time taken to generate the graph."
    )
    graphChatCompletionInputToken: int = Field(
        default=0, description="Number of input tokens used for generating the graph."
    )
    graphChatCompletionOutputToken: int = Field(
        default=0, description="Number of output tokens generated in the graph."
    )
    graphGenerationCode: str = Field(
        default=None,
        description="Code generated for graph generation based on the SQL query response.",
    )
    graphFigureJson: str = Field(
        default=None,
        description="Representation of figure as a JSON string",
    )
    totalAdaCalls: int = Field(
        default=0, description="Total number of requests made to the ADA model."
    )
    totalChatCompletionCalls: int = Field(
        default=0,
        description="Total number of requests made to the Chat Completion model.",
    )
    error: str = Field(
        default="", description="Any error encountered during the transaction."
    )
    responseTime: float = Field(
        default=0,
        description="Total time taken to generate and provide an answer to the user's query.",
    )

    _start_time: datetime = PrivateAttr()

    def __init__(self, **data):
        """
        Initializes a new instance of the class.

        Args:
            data (dict): A dictionary containing the data to initialize the instance.

        Returns:
            None
        """
        super().__init__(**data)
        self._start_time = datetime.now()

    def to_dict(self):
        """
        Convert the model to a dictionary, encoding any list or dictionary values as JSON strings.
        """
        model_dict = self.model_dump()
        for key, value in model_dict.items():
            if isinstance(value, (list, dict)):
                model_dict[key] = json.dumps(value)
        return model_dict

    def to_sql(self):
        """
        Converts the conversation analytics data to SQL format and inserts it into the database.

        This method calculates the response time, creates a DataFrame from the conversation analytics data,
        and inserts the data into the conversation analytics table in the database.

        Raises:
            NL2SQLException: If there is an error while inserting the data into the database.

        """
        current_time = datetime.now()
        self.responseTime = (current_time - self._start_time).total_seconds()
        try:
            sqlite_manager.insert_data(
                transaction_id=self.conversationID,
                table_name=sqlite_manager.CONVERSATION_ANALYTICS_TABLE,
                df=pd.DataFrame([self.to_dict()]),
            )
            # # change the type of the string to list
            # if isinstance(self.cacheSqlQueryResponse, str):
            #     self.cacheSqlQueryResponse = json.loads(self.cacheSqlQueryResponse)
            if isinstance(self.sqlQueryResponse, str):
                self.sqlQueryResponse = json.loads(self.sqlQueryResponse)
        except CustomException as custom_exc:
            custom_exc.conversation_analytics = self
            raise custom_exc


class RetrievalLogsModel(BaseModel):
    """
    RetrievalLogsModel is a Pydantic model for capturing logs related to the retrieval process in the NLtoSQL system.

    Attributes:
        conversationAnalyticsId (str): Unique identifier for the conversation analytics record.
        tenantId (str): Unique identifier for the tenant.
        userID (str): Unique identifier for the user.
        sessionID (str): Unique identifier for the conversation associated with this transaction.
        conversationID (str): Unique identifier for the conversation associated with this transaction.
        date (str): Timestamp of the request in UTC format. (Format: YYYY-MM-DDTHH:MM:SS.fffZ)
        relevantTables (List[str]): List of relevant tables identified during the retrieval process.
        relevantColumns (List[str]): List of relevant columns identified during the retrieval process.
        relevantSqlExamples (List[Dict[str, str]]): List of relevant SQL examples identified during the retrieval process.

    Methods:
        to_dict(): Converts the model to a dictionary, encoding any list or dictionary values as JSON strings.
        to_sql(conversation_analytics: ConversationAnalyticsModel): Converts the retrieval logs data to SQL format and inserts it into the database.
    """

    conversationAnalyticsId: str = Field(
        default=None,
        description="Unique identifier for the conversation analytics record.",
    )
    tenantId: str = Field(
        description="Unique identifier for the tenant",
    )
    emailID: str = Field(
        description="Email address of the user",
    )
    userID: str = Field(description="Unique identifier for the user")
    sessionID: str = Field(
        description="Unique identifier for the conversation associated with this transaction."
    )
    conversationID: str = Field(
        description="Unique identifier for the conversation associated with this transaction."
    )
    date: str = Field(
        description="Timestamp of the request in UTC format. (Format: YYYY-MM-DDTHH:MM:SS.fffZ)"
    )
    relevantTables: List[str] = Field(
        default=[],
        description="List of relevant tables identified during the retrieval process.",
    )
    relevantColumns: str = Field(
        default="",
        description="Relevant columns identified during the retrieval process.",
    )
    relevantSqlExamples: List[Dict[str, str]] = Field(
        default=[],
        description="List of relevant SQL examples identified during the retrieval process.",
    )

    def to_dict(self):
        """
        Convert the model to a dictionary, encoding any list or dictionary values as JSON strings.
        """
        model_dict = self.model_dump()
        for key, value in model_dict.items():
            if isinstance(value, (list, dict)):
                model_dict[key] = json.dumps(value)
        return model_dict

    def to_sql(self, conversation_analytics: ConversationAnalyticsModel):
        """
        Inserts the current object's data into the retrieval history table in the database.

        Args:
            conversation_analytics (ConversationAnalyticsModel):
                An instance containing analytics data for the current conversation.

        Raises:
            CustomException:
                If an error occurs during the insertion, the exception is raised after
                attaching the provided conversation_analytics to it.
        """
        try:
            sqlite_manager.insert_data(
                transaction_id=self.conversationID,
                table_name=sqlite_manager.RETRIEVAL_HISTORY_TABLE,
                df=pd.DataFrame([self.to_dict()]),
            )
        except CustomException as custom_exc:
            custom_exc.conversation_analytics = conversation_analytics
            raise custom_exc


class APIResponseModel(BaseModel):
    """
    This model is used to structure the API response, including the bot's responses and any errors that occurred during the API call.

    Attributes:
        botResponse (List[Dict[str, Any]]): Bot response.
        error (str): Error occurred in the API.
    """

    botResponse: List[Dict[str, Any]] = Field(default=[], description="Bot response")
    error: str = Field(default="", description="Error occured in the API")


class TablesVectorRecord(BaseModel):
    """
    TablesVectorRecord is a data model that represents the structure of a record in the tables vector collection.

    Attributes:
        tableName (str): Name of the table.
        tableDescription (str): Description of the table.
        tableDDL (str): DDL (Data Definition Language) statement for the table.
        tableCluster (str): Cluster to which the table belongs.
        tableSampleValues (str): Sample values from the table.
        tableDescriptionEmbeddings (List[float]): Embeddings for the table description.

    Methods:
        __init__(self, **data): Initializes a new instance of the class.
    """

    tableName: str = Field(
        description="Name of the table",
    )
    tableDescription: str = Field(
        description="Description of the table",
    )
    tableDDL: str = Field(
        default="",
        description="DDL (Data Definition Language) statement for the table.",
    )
    tableCluster: str = Field(
        default="",
        description="Cluster to which the table belongs.",
    )
    tableSampleValues: str = Field(
        default="",
        description="Sample values from the table.",
    )
    tableDescriptionEmbeddings: List[float] = Field(
        description="Embeddings for the table description",
    )


class ColumnsVectorRecord(BaseModel):
    """
    ColumnsVectorRecord is a data model that represents the structure of a record in the columns vector collection.

    Attributes:
        tableName (str): Name of the table.
        columnName (str): Name of the column.
        # columnIsPrimaryKey (str): Flag to indicate if the column is a primary key.
        columnDescription (str): Description of the column.
        columnDataType (str): Data type of the column.
        columnSampleValue (str): Sample value of the column.
        columnDescriptionEmbeddings (List[float]): Embeddings for the column description.

    Methods:
        __init__(self, **data): Initializes a new instance of the class.
    """

    tableName: str = Field(
        description="Name of the table",
    )
    columnName: str = Field(
        description="Name of the column",
    )
    # columnIsPrimaryKey: str = Field(
    #     default="false",
    #     description="Flag to indicate if the column is a primary key.",
    # )
    columnDescription: str = Field(
        description="Description of the column",
    )
    columnDataType: str = Field(
        description="Data type of the column",
    )
    columnSampleValue: str = Field(
        description="Sample value of the column",
    )
    columnDescriptionEmbeddings: List[float] = Field(
        description="Embeddings for the column description",
    )


class SqlExampleVectorRecord(BaseModel):
    """
    SqlExampleVectorRecord is a data model that represents the structure of a record in the sql example vector collection.

    Attributes:
        tenantID (str): Unique identifier for the tenant.
        question (str): The question asked by the user.
        sqlQuery (str): The SQL query generated based on the user's question.

    Methods:
        __init__(self, **data): Initializes a new instance of the class.
    """

    tenantID: str = Field(
        description="Unique identifier for the tenant",
    )
    question: str = Field(
        description="The question asked by the user",
    )
    sqlQuery: str = Field(
        description="The SQL query generated based on the user's question",
    )
    questionEmbeddings: List[float] = Field(
        description="Embeddings for the question",
    )


# type: ignore
