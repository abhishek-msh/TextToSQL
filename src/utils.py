import re
from partialjson.json_parser import JSONParser
from typing import Tuple, Dict
from src.adapters.loggingmanager import logger
from src.custom_exception import CustomException
from config import DatabaseConfig
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from fastapi.responses import JSONResponse
from src.types import (
    ConversationAnalyticsModel,
    APIResponseModel,
)
import sqlparse
import sqlglot

return_key_dialect = list(DatabaseConfig().DIALECT.keys())[0]
prompt_dialect = DatabaseConfig().DIALECT[return_key_dialect]


def extract_and_format_metadata(columns_retrieved_data):
    relevant_metadata = {}

    for record in columns_retrieved_data[0]:
        entity = record["entity"]
        table_name = entity["tableName"]
        column_info = {
            "columnName": entity["columnName"],
            "columnIsPrimaryKey": entity["columnIsPrimaryKey"],
            "columnDescription": entity["columnDescription"],
            "columnDataType": entity["columnDataType"],
            "columnSampleValue": entity["columnSampleValue"],
        }
        relevant_metadata.setdefault(table_name, []).append(column_info)

    # Generate formatted metadata string
    lines = []
    for table_idx, (table_name, columns) in enumerate(
        relevant_metadata.items(), start=1
    ):
        lines.append(f"## TABLE {table_idx}: `{table_name}`\nCOLUMNS:")
        for col_idx, column in enumerate(columns, start=1):
            lines.append(
                f"- Column {col_idx}: `{column['columnName']}`\n"
                f"      * Is Primary Key: {column['columnIsPrimaryKey']}\n"
                f"      * Description: {column['columnDescription']}\n"
                f"      * Data Type: {column['columnDataType']}\n"
                f"      * Sample Value:\n{column['columnSampleValue']}\n"
            )

    return "\n".join(lines).strip()


def format_sql_examples(retrieved_sql_example_data):
    formatted_sql_examples = []
    for record in retrieved_sql_example_data[0]:
        if record["distance"] > 0.75:
            formatted_sql_examples.append(
                {
                    "question": record["entity"]["question"],
                    "sqlQuery": record["entity"]["sqlQuery"],
                }
            )
    return formatted_sql_examples


def clean_string(string):
    """
    Clean the string by removing extra spaces and newlines.
    """
    cleaned_lines = [re.sub(r"\s*\|\s*", "|", line) for line in string.splitlines()]
    cleaned_string = "\n".join(cleaned_lines)
    return cleaned_string


def rephrase_gpt_response_parser(transaction_id: str, gpt_response: Dict):
    """
    Method to parser GPT response Json and extract the rephrase query

    Args:
        transaction_id (str): Unique ID for the transaction
        gpt_response (Dict): Reponse Dict from openai

    Returns:
        Tuple[str]: Returns 1 key values i.e. rephrased_query
    """
    parser = JSONParser()
    rephrased_query = None
    try:
        parsed_response = parser.parse(gpt_response["choices"][0]["message"]["content"])
        rephrased_query = parsed_response["rephrased_query"]
        assert isinstance(rephrased_query, str), "invalid rephrased query format"
        logger.info(
            f"[utils][rephrase_gpt_response_parser][{transaction_id}] - rephrased query Response Parsed Successfully"
        )
    except Exception as response_parser_exc:
        logger.exception(
            f"[utils][rephrase_gpt_response_parser][{transaction_id}] Error: {str(response_parser_exc)}"
        )
        raise CustomException(error="Openai rephrased query parsing failed")
    return rephrased_query


def _clean_llm_response_for_deepseek(response):
    """
    Cleans the LLM response by removing unnecessary characters and formatting.
    """
    # Remove unwanted characters and formatting
    cleaned_response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)

    # Return the cleaned response
    return cleaned_response


def is_sql_valid(sql: str) -> bool:
    """
    Checks if the SQL query is valid. This is usually used to check if we should run the SQL query or not.
    By default it checks if the SQL query is a SELECT statement. You can override this method to enable running other types of SQL queries.

    Args:
        sql (str): The SQL query to check.

    Returns:
        bool: True if the SQL query is valid, False otherwise.
    """

    parsed = sqlparse.parse(sql)

    for statement in parsed:
        if statement.get_type() == "SELECT":
            return True

    return False


def sql_response_parser(transaction_id: str, gpt_response: Dict) -> Tuple[str]:
    print(gpt_response)
    parser = JSONParser()
    sql_query = None
    flag = False
    try:
        parsed_response = parser.parse(gpt_response["choices"][0]["message"]["content"])
        print(parsed_response)
        try:
            sql_query = parsed_response[f"{return_key_dialect}_query"]
            # parsed = sqlglot.parse_one(sql_query, dialect="presto")
            # if "limit" not in sql_query.lower():
            #     sql_query += " LIMIT 10"
            if is_sql_valid(sql_query):
                flag = True
            if ";" not in sql_query:
                sql_query += ";"

            assert isinstance(sql_query, str), "invalid sql format"
            logger.info(
                f"[utils][sql_response_parser][{transaction_id}] - Response Parsed Successfully"
            )
        except:
            # extract text between last " and first "
            try:
                error = str(parsed_response).split('"')[1]
            except:
                error = parsed_response.get("error", "Unable to generate SQL query")
            logger.info(
                f"[utils][sql_response_parser][{transaction_id}] - Unable to generate sql query: {error}"
            )
            return flag, error
    except Exception as response_parser_exc:
        logger.exception(
            f"[utils][sql_response_parser][{transaction_id}] Error: {str(response_parser_exc)}"
        )
        raise CustomException(error="Openai answer parsing failed")
    return flag, sql_query


def sql_response_parser_for_deepseek(
    transaction_id: str, gpt_response: Dict
) -> Tuple[str]:
    """
    Parses the SQL response from the GPT model and returns the SQL query.

    Args:
        transaction_id (str): Unique ID for the transaction
        gpt_response (Dict): Response Dict from OpenAI

    Returns:
        Tuple[str]: Returns a tuple containing the SQL query
    """
    sql_query = None
    flag = False
    try:
        gpt_response["choices"][0]["message"]["content"] = (
            _clean_llm_response_for_deepseek(
                gpt_response["choices"][0]["message"]["content"]
            )
        )
        sql_query = (
            gpt_response["choices"][0]["message"]["content"]
            .split("```sql\n")[1]
            .split("\n```")[0]
            .strip()
        )
        if "limit" not in sql_query.lower():
            if ";" in sql_query:
                sql_query = sql_query.replace(";", " LIMIT 10;")
            else:
                sql_query += " LIMIT 10;"
        # parsed = sqlglot.parse_one(sql_query, dialect="presto")
        if is_sql_valid(sql_query):
            flag = True
        else:
            flag = False
        assert isinstance(sql_query, str), "invalid sql format"
        logger.info(
            f"[utils][sql_response_parser_for_deepseek][{transaction_id}] - Response Parsed Successfully"
        )
    except Exception as response_parser_exc:
        logger.exception(
            f"[utils][sql_response_parser_for_deepseek][{transaction_id}] Error: {str(response_parser_exc)}"
        )
        print(gpt_response)
        return flag, gpt_response["choices"][0]["message"]["content"]
    return flag, sql_query


def answer_response_parser(transaction_id: str, gpt_response: Dict) -> Tuple[str]:
    parser = JSONParser()
    answer = None
    try:
        parsed_response = parser.parse(gpt_response["choices"][0]["message"]["content"])
        answer = parsed_response["answer"]

        assert isinstance(answer, str), "invalid answer format"
        logger.info(
            f"[utils][answer_response_parser][{transaction_id}] - Response Parsed Successfully"
        )
    except Exception as response_parser_exc:
        logger.exception(
            f"[utils][answer_response_parser][{transaction_id}] Error: {str(response_parser_exc)}"
        )
        raise CustomException(error="Openai answer parsing failed")
    return answer


def _extract_python_code(markdown_string: str) -> str:
    # Strip whitespace to avoid indentation errors in LLM-generated code
    markdown_string = markdown_string.strip()

    # Regex pattern to match Python code blocks
    pattern = r"```[\w\s]*python\n([\s\S]*?)```|```([\s\S]*?)```"

    # Find all matches in the markdown string
    matches = re.findall(pattern, markdown_string, re.IGNORECASE)

    # Extract the Python code from the matches
    python_code = []
    for match in matches:
        python = match[0] if match[0] else match[1]
        python_code.append(python.strip())

    if len(python_code) == 0:
        return markdown_string

    return python_code[0]


def _sanitize_plotly_code(raw_plotly_code: str) -> str:
    # Remove the fig.show() statement from the plotly code
    plotly_code = raw_plotly_code.replace("fig.show()", "")

    return plotly_code


def get_plotly_figure(
    plotly_code: str, df: pd.DataFrame, dark_mode: bool = True
) -> plotly.graph_objs.Figure:
    """
    **Example:**
    ```python
    fig = vn.get_plotly_figure(
        plotly_code="fig = px.bar(df, x='name', y='salary')",
        df=df
    )
    fig.show()
    ```
    Get a Plotly figure from a dataframe and Plotly code.

    Args:
        df (pd.DataFrame): The dataframe to use.
        plotly_code (str): The Plotly code to use.

    Returns:
        plotly.graph_objs.Figure: The Plotly figure.
    """
    ldict = {"df": df, "px": px, "go": go}
    try:
        exec(plotly_code, globals(), ldict)

        fig = ldict.get("fig", None)
    except Exception as e:
        # Inspect data types
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = df.select_dtypes(
            include=["object", "category"]
        ).columns.tolist()

        # Decision-making for plot type
        if len(numeric_cols) >= 2:
            # Use the first two numeric columns for a scatter plot
            fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1])
        elif len(numeric_cols) == 1 and len(categorical_cols) >= 1:
            # Use a bar plot if there's one numeric and one categorical column
            fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0])
        elif len(categorical_cols) >= 1 and df[categorical_cols[0]].nunique() < 10:
            # Use a pie chart for categorical data with fewer unique values
            fig = px.pie(df, names=categorical_cols[0])
        else:
            # Default to a simple line plot if above conditions are not met
            fig = px.line(df)

    if fig is None:
        return None

    if dark_mode:
        fig.update_layout(template="plotly_dark")

    return fig


def api_response_builder(
    conversation_analytics: ConversationAnalyticsModel,
    streaming: bool = False,
) -> APIResponseModel:
    """
    Builds an API response based on the conversation analytics data.

    Args:
        conversation_analytics (ConversationAnalyticsModel)

    Returns:
        APIResponseModel: The constructed API response model containing the bot's response
    """
    # Check if there's an error
    if conversation_analytics.error != "":
        # Assuming APIResponseModel can be initialized with error details
        if streaming:
            return APIResponseModel(
                botResponse=[],
                error=conversation_analytics.error,
            ).model_dump()
        return JSONResponse(
            status_code=500,
            content=APIResponseModel(error=conversation_analytics.error).model_dump(),
        )

    # Determine the answer and language specific answer fields

    response_payload = conversation_analytics.to_dict()
    if streaming:
        return APIResponseModel(botResponse=[response_payload]).model_dump()
    return JSONResponse(
        status_code=200,
        content=APIResponseModel(
            botResponse=[response_payload],
        ).model_dump(),
    )


def extract_sql(llm_response: str) -> str:
    """
    Example:
    ```python
    vn.extract_sql("Here's the SQL query in a code block: ```sql\nSELECT * FROM customers\n```")
    ```

    Extracts the SQL query from the LLM response. This is useful in case the LLM response contains other information besides the SQL query.
    Override this function if your LLM responses need custom extraction logic.

    Args:
        llm_response (str): The LLM response.

    Returns:
        str: The extracted SQL query.
    """

    import re

    """
        Extracts the SQL query from the LLM response, handling various formats including:
        - WITH clause
        - SELECT statement
        - CREATE TABLE AS SELECT
        - Markdown code blocks
        """

    # Match CREATE TABLE ... AS SELECT
    sqls = re.findall(
        r"\bCREATE\s+TABLE\b.*?\bAS\b.*?;", llm_response, re.DOTALL | re.IGNORECASE
    )
    if sqls:
        sql = sqls[-1]
        return sql

    # Match WITH clause (CTEs)
    sqls = re.findall(r"\bWITH\b .*?;", llm_response, re.DOTALL | re.IGNORECASE)
    if sqls:
        sql = sqls[-1]
        return sql

    # Match SELECT ... ;
    sqls = re.findall(r"\bSELECT\b .*?;", llm_response, re.DOTALL | re.IGNORECASE)
    if sqls:
        sql = sqls[-1]
        return sql

    # Match ```sql ... ``` blocks
    sqls = re.findall(r"```sql\s*\n(.*?)```", llm_response, re.DOTALL | re.IGNORECASE)
    if sqls:
        sql = sqls[-1].strip()
        return sql

    # Match any ``` ... ``` code blocks
    sqls = re.findall(r"```(.*?)```", llm_response, re.DOTALL | re.IGNORECASE)
    if sqls:
        sql = sqls[-1].strip()
        return sql

    return llm_response


def should_generate_chart(df: pd.DataFrame) -> bool:
    """
    Checks if a chart should be generated for the given DataFrame. By default, it checks if the DataFrame has more than one row and has numerical columns.
    You can override this method to customize the logic for generating charts.

    Args:
        df (pd.DataFrame): The DataFrame to check.

    Returns:
        bool: True if a chart should be generated, False otherwise.
    """

    if len(df) > 1 and df.select_dtypes(include=["number"]).shape[1] > 0:
        return True

    return False
