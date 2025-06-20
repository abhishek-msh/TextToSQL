import uuid
import json
from src.types import GetAnswerModel, ConversationAnalyticsModel, RetrievalLogsModel
from config import SqlConfig, MilvusConfig, DatabaseConfig
from src.adapters.pinotmanager import pinot_manager
from config import DatabaseConfig
from src.pinot_prompts import (
    _query_rephrase_prompt,
    _texttosql_prompt,
    _answer_prompt,
    _graph_prompt,
    _texttosql_deepseak_prompt,
)
from src.adapters.openaimanager import openai_manager
from src.adapters.ollamamanager import ollama_manager
from src.adapters.milvusmanager import milvus_manager
from src.adapters.loggingmanager import logger
from src.adapters.sqlitemanager import sql_manager
from src.utils import (
    rephrase_gpt_response_parser,
    extract_and_format_metadata,
    format_sql_examples,
    sql_response_parser,
    answer_response_parser,
    clean_string,
    _extract_python_code,
    _sanitize_plotly_code,
    get_plotly_figure,
    api_response_builder,
    sql_response_parser_for_deepseek,
    should_generate_chart,
)
from typing import Tuple, Union, Generator

return_key_dialect = list(DatabaseConfig().DIALECT.keys())[0]
prompt_dialect = DatabaseConfig().DIALECT[return_key_dialect]


class biAssistant:
    def __init__(self, data: GetAnswerModel) -> None:
        """
        Initializes the biAssistant with the provided data.

        Args:
            data (GetAnswerModel): The data containing the question and answer.
        """
        self.data = data
        self.conversation_analytics = ConversationAnalyticsModel(
            **self.data.model_dump()
        )
        self.conversation_analytics.id = (
            f"{uuid.uuid4()}_{self.conversation_analytics.date}"
        )
        self.retrieval_logs = RetrievalLogsModel(**self.data.model_dump())
        self.retrieval_logs.conversationAnalyticsId = self.conversation_analytics.id

    def get_answer(self):
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Start"
        )

        question_column_name = "userText"

        sql_query = f"""SELECT {question_column_name}, answer, error FROM {SqlConfig().CONVERSATION_ANALYTICS_TABLE} WHERE userID = '{self.conversation_analytics.userID}' and sessionID = '{self.conversation_analytics.sessionID}' ORDER BY _ts desc LIMIT 2;"""

        fetched_df = (
            sql_manager.fetch_data(
                self.conversation_analytics.conversationID, sql_query=sql_query
            )
            .iloc[::-1]
            .reset_index(drop=True)
        )
        if not fetched_df.empty:
            previous_convo_string = ""
            for idx, row in fetched_df.iterrows():
                if row["error"]:
                    row["answer"] = "NONE"
                previous_convo_string += f"User Query {idx + 1}: {row[question_column_name]}\n{return_key_dialect}_query: {row['answer']}\n\n"
            previous_convo_string = previous_convo_string.strip()

            rephrase_messages = _query_rephrase_prompt(
                query=self.conversation_analytics.userText,
                previous_conversation=previous_convo_string,
            )
            (
                self.conversation_analytics.userTextRephrasedChatCompletionTime,
                rephrase_response,
            ) = openai_manager.chat_completion(
                transaction_id=self.conversation_analytics.conversationID,
                messages=rephrase_messages,
            )
            self.conversation_analytics.totalChatCompletionCalls += 1
            self.conversation_analytics.userTextRephrasedChatCompletionInputToken = (
                rephrase_response["usage"]["prompt_tokens"]
            )
            self.conversation_analytics.userTextRephrasedChatCompletionOutputToken = (
                rephrase_response["usage"]["completion_tokens"]
            )
            # parsing category gpt response
            self.conversation_analytics.userTextRephrased = (
                rephrase_gpt_response_parser(
                    self.conversation_analytics.conversationID, rephrase_response
                )
            )
            if (
                "not a follow-up question"
                not in self.conversation_analytics.userTextRephrased.lower()
            ):
                question_column_name = "userTextRephrased"
            logger.info(
                f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - User query rephrased"
            )
            del rephrase_response

        # STEP 1 : Generate query embedding
        (
            self.conversation_analytics.userTextEmbeddingGenerationTime,
            embedding_response,
        ) = openai_manager.create_embedding(
            transaction_id=self.conversation_analytics.conversationID,
            text=getattr(self.conversation_analytics, question_column_name),
        )
        self.conversation_analytics.totalAdaCalls += 1
        # Validation of text translation
        self.conversation_analytics.userTextEmbeddingTokens = embedding_response[
            "usage"
        ]["total_tokens"]
        query_embedding = embedding_response["data"][0]["embedding"]
        del embedding_response
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Query embedding generated"
        )
        # STEP 2 : Table Vector search
        self.conversation_analytics.tableVectorSearchTime, table_retrieved_data = (
            milvus_manager.search_index(
                transaction_id=self.conversation_analytics.conversationID,
                collection_name=MilvusConfig().MILVUS_TABLE_COLLECTION_NAME,
                text_embedding=query_embedding,
                return_fields=MilvusConfig().MILVUS_TABLE_RETURN_FIELDS,
                top_k=MilvusConfig().MILVUS_TOP_TABLES_K,
            )
        )
        for record in table_retrieved_data[0]:
            self.retrieval_logs.relevantTables.append(record["entity"]["tableName"])
        del table_retrieved_data
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Relevant tables retrieved"
        )
        # STEP 3 : Column Vector search
        column_filter_expr = f"tableName in {self.retrieval_logs.relevantTables}"
        self.conversation_analytics.columnVectorSearchTime, columns_retrieved_data = (
            milvus_manager.search_index(
                transaction_id=self.conversation_analytics.conversationID,
                collection_name=MilvusConfig().MILVUS_COLUMN_COLLECTION_NAME,
                text_embedding=query_embedding,
                return_fields=MilvusConfig().MILVUS_COLUMN_RETURN_FIELDS,
                top_k=len(self.retrieval_logs.relevantTables)
                * MilvusConfig().MILVUS_TOP_COLUMNS_K,
                filter_expr=column_filter_expr,
            )
        )

        self.retrieval_logs.relevantColumns = extract_and_format_metadata(
            columns_retrieved_data
        )
        del columns_retrieved_data
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Relevant columns retrieved"
        )
        # STEP 4 : SQL Example Vector search
        # sql_example_filter_expr = (
        #     f'tenantID == "{self.conversation_analytics.tenantId}"'
        # )
        sql_example_filter_expr = ""
        self.conversation_analytics.sqlExampleVectorSearchTime, sql_examples_data = (
            milvus_manager.search_index(
                transaction_id=self.conversation_analytics.conversationID,
                collection_name=MilvusConfig().MILVUS_SQL_EXAMPLE_COLLECTION_NAME,
                text_embedding=query_embedding,
                return_fields=MilvusConfig().MILVUS_SQL_EXAMPLE_RETURN_FIELDS,
                top_k=MilvusConfig().MILVUS_TOP_SQL_EXAMPLES_K,
                filter_expr=sql_example_filter_expr,
            )
        )
        self.retrieval_logs.relevantSqlExamples = format_sql_examples(sql_examples_data)
        del sql_examples_data
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Relevant SQL examples retrieved"
        )
        # STEP 5 : Generate SQL query
        sql_query_messages = _texttosql_prompt(
            user_input=getattr(self.conversation_analytics, question_column_name),
            tenant_id=self.conversation_analytics.tenantId,
            database_info=self.retrieval_logs.relevantColumns,
            example_sql=self.retrieval_logs.relevantSqlExamples,
            relationship_diagram=DatabaseConfig().DATABASE_INFORMATION_PROMPT_TEMPLATE,
        )
        (
            self.conversation_analytics.sqlQueryChatCompletionTime,
            sql_chat_completion_response,
        ) = openai_manager.chat_completion(
            transaction_id=self.conversation_analytics.conversationID,
            messages=sql_query_messages,
        )

        self.conversation_analytics.totalChatCompletionCalls += 1
        self.conversation_analytics.sqlQueryChatCompletionInputToken = (
            sql_chat_completion_response["usage"]["prompt_tokens"]
        )
        self.conversation_analytics.sqlQueryChatCompletionOutputToken = (
            sql_chat_completion_response["usage"]["completion_tokens"]
        )

        # parsing sql gpt response
        sql_flag, self.conversation_analytics.sqlQuery = sql_response_parser(
            transaction_id=self.conversation_analytics.conversationID,
            gpt_response=sql_chat_completion_response,
        )
        if not sql_flag:
            self.conversation_analytics.answer = self.conversation_analytics.sqlQuery
            self.conversation_analytics.sqlQuery = ""
            return self.conversation_analytics, self.retrieval_logs
        del sql_chat_completion_response
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - SQL query generated"
        )

        self.conversation_analytics.sqlQuery = (
            f"SET useMultistageEngine=true; {self.conversation_analytics.sqlQuery}"
        )
        # STEP 6 : Execute SQL query
        self.conversation_analytics.sqlQueryExecutionTime, sql_execution_response = (
            pinot_manager.fetch_data(
                transaction_id=self.conversation_analytics.conversationID,
                sql_query=self.conversation_analytics.sqlQuery,
            )
        )
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - SQL query executed"
        )
        self.conversation_analytics.sqlQueryResponse = sql_execution_response.to_json(
            orient="records", date_format="iso"
        )
        sql_result_markdown = sql_execution_response.to_markdown()
        sql_result_markdown = clean_string(sql_result_markdown)

        # STEP 7 : Generate answer
        answer_messages = _answer_prompt(
            user_input=getattr(self.conversation_analytics, question_column_name),
            sql_query=self.conversation_analytics.sqlQuery,
            sql_result=sql_result_markdown,
        )
        self.conversation_analytics.answerChatCompletionTime, answer_response = (
            openai_manager.chat_completion(
                transaction_id=self.conversation_analytics.conversationID,
                messages=answer_messages,
            )
        )
        self.conversation_analytics.totalChatCompletionCalls += 1
        self.conversation_analytics.answerChatCompletionInputToken = answer_response[
            "usage"
        ]["prompt_tokens"]
        self.conversation_analytics.answerChatCompletionOutputToken = answer_response[
            "usage"
        ]["completion_tokens"]
        self.conversation_analytics.answer = answer_response_parser(
            transaction_id=self.conversation_analytics.conversationID,
            gpt_response=answer_response,
        )
        del answer_response
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Answer generated"
        )
        if not sql_execution_response.empty and should_generate_chart(
            sql_execution_response
        ):
            # STEP 8 : Generate Graph
            logger.info(
                f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Generating Graph"
            )
            data_types = sql_execution_response.dtypes
            graph_messages = _graph_prompt(
                user_input=getattr(self.conversation_analytics, question_column_name),
                sql_query=self.conversation_analytics.sqlQuery,
                data_type=data_types,
            )
            self.conversation_analytics.graphChatCompletionTime, graph_response = (
                openai_manager.chat_completion(
                    transaction_id=self.conversation_analytics.conversationID,
                    messages=graph_messages,
                    response_format={"type": "text"},
                )
            )
            self.conversation_analytics.totalChatCompletionCalls += 1
            self.conversation_analytics.graphChatCompletionInputToken = graph_response[
                "usage"
            ]["prompt_tokens"]
            self.conversation_analytics.graphChatCompletionOutputToken = graph_response[
                "usage"
            ]["completion_tokens"]
            python_plotly_code = graph_response["choices"][0]["message"]["content"]
            self.conversation_analytics.graphGenerationCode = _sanitize_plotly_code(
                _extract_python_code(python_plotly_code)
            )
            del graph_response
            logger.info(
                f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Graph code generated"
            )
            # STEP 9 : Generate Graph Figure
            fig = get_plotly_figure(
                plotly_code=self.conversation_analytics.graphGenerationCode,
                df=sql_execution_response,
            )
            fig_json = fig.to_json()
            self.conversation_analytics.graphFigureJson = fig_json

        del sql_execution_response
        return self.conversation_analytics, self.retrieval_logs

    def get_answer_streaming(
        self,
    ) -> Generator[Union[str, dict], None, Tuple[ConversationAnalyticsModel]]:
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Start"
        )

        question_column_name = "userText"

        sql_query = f"""SELECT {question_column_name}, answer, error FROM {SqlConfig().CONVERSATION_ANALYTICS_TABLE} WHERE userID = '{self.conversation_analytics.userID}' and sessionID = '{self.conversation_analytics.sessionID}' ORDER BY _ts desc LIMIT 2;"""

        fetched_df = (
            sql_manager.fetch_data(
                self.conversation_analytics.conversationID, sql_query=sql_query
            )
            .iloc[::-1]
            .reset_index(drop=True)
        )
        if not fetched_df.empty:
            previous_convo_string = ""
            for idx, row in fetched_df.iterrows():
                if row["error"]:
                    row["answer"] = "NONE"
                previous_convo_string += f"User Query {idx + 1}: {row[question_column_name]}\n{return_key_dialect}_query: {row['answer']}\n\n"
            previous_convo_string = previous_convo_string.strip()
            yield f"[LOGS] - Rephrasing user query"
            rephrase_messages = _query_rephrase_prompt(
                query=self.conversation_analytics.userText,
                previous_conversation=previous_convo_string,
            )
            (
                self.conversation_analytics.userTextRephrasedChatCompletionTime,
                rephrase_response,
            ) = openai_manager.chat_completion(
                transaction_id=self.conversation_analytics.conversationID,
                messages=rephrase_messages,
            )
            self.conversation_analytics.totalChatCompletionCalls += 1
            self.conversation_analytics.userTextRephrasedChatCompletionInputToken = (
                rephrase_response["usage"]["prompt_tokens"]
            )
            self.conversation_analytics.userTextRephrasedChatCompletionOutputToken = (
                rephrase_response["usage"]["completion_tokens"]
            )
            # parsing category gpt response
            self.conversation_analytics.userTextRephrased = (
                rephrase_gpt_response_parser(
                    self.conversation_analytics.conversationID, rephrase_response
                )
            )
            if (
                "not a follow-up question"
                not in self.conversation_analytics.userTextRephrased.lower()
            ):
                question_column_name = "userTextRephrased"
            logger.info(
                f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - User query rephrased"
            )
            yield json.dumps(
                {
                    "type": "userTextRephrased",
                    "content": getattr(
                        self.conversation_analytics, question_column_name
                    ),
                }
            )
            del rephrase_response

        # STEP 1 : Generate query embedding
        yield f"[LOGS] - Query Vectorization"
        (
            self.conversation_analytics.userTextEmbeddingGenerationTime,
            embedding_response,
        ) = openai_manager.create_embedding(
            transaction_id=self.conversation_analytics.conversationID,
            text=getattr(self.conversation_analytics, question_column_name),
        )
        self.conversation_analytics.totalAdaCalls += 1
        # Validation of text translation
        self.conversation_analytics.userTextEmbeddingTokens = embedding_response[
            "usage"
        ]["total_tokens"]
        query_embedding = embedding_response["data"][0]["embedding"]
        del embedding_response
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Query embedding generated"
        )

        # STEP 2 : Table Vector search
        yield f"[LOGS] - Searching relevant tables"
        self.conversation_analytics.tableVectorSearchTime, table_retrieved_data = (
            milvus_manager.search_index(
                transaction_id=self.conversation_analytics.conversationID,
                collection_name=MilvusConfig().MILVUS_TABLE_COLLECTION_NAME,
                text_embedding=query_embedding,
                return_fields=MilvusConfig().MILVUS_TABLE_RETURN_FIELDS,
                top_k=MilvusConfig().MILVUS_TOP_TABLES_K,
            )
        )
        for record in table_retrieved_data[0]:
            self.retrieval_logs.relevantTables.append(record["entity"]["tableName"])
        del table_retrieved_data
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Relevant tables retrieved"
        )
        # STEP 3 : Column Vector search
        yield f"[LOGS] - Searching relevant columns"
        column_filter_expr = f"tableName in {self.retrieval_logs.relevantTables}"
        self.conversation_analytics.columnVectorSearchTime, columns_retrieved_data = (
            milvus_manager.search_index(
                transaction_id=self.conversation_analytics.conversationID,
                collection_name=MilvusConfig().MILVUS_COLUMN_COLLECTION_NAME,
                text_embedding=query_embedding,
                return_fields=MilvusConfig().MILVUS_COLUMN_RETURN_FIELDS,
                top_k=len(self.retrieval_logs.relevantTables)
                * MilvusConfig().MILVUS_TOP_COLUMNS_K,
                filter_expr=column_filter_expr,
            )
        )

        self.retrieval_logs.relevantColumns = extract_and_format_metadata(
            columns_retrieved_data
        )
        del columns_retrieved_data
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Relevant columns retrieved"
        )
        # STEP 4 : SQL Example Vector search
        yield f"[LOGS] - Searching relevant SQL examples"
        # sql_example_filter_expr = (
        #     f'tenantID == "{self.conversation_analytics.tenantId}"'
        # )
        sql_example_filter_expr = ""
        self.conversation_analytics.sqlExampleVectorSearchTime, sql_examples_data = (
            milvus_manager.search_index(
                transaction_id=self.conversation_analytics.conversationID,
                collection_name=MilvusConfig().MILVUS_SQL_EXAMPLE_COLLECTION_NAME,
                text_embedding=query_embedding,
                return_fields=MilvusConfig().MILVUS_SQL_EXAMPLE_RETURN_FIELDS,
                top_k=MilvusConfig().MILVUS_TOP_SQL_EXAMPLES_K,
                filter_expr=sql_example_filter_expr,
            )
        )
        self.retrieval_logs.relevantSqlExamples = format_sql_examples(sql_examples_data)
        del sql_examples_data
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Relevant SQL examples retrieved"
        )
        # STEP 5 : Generate SQL query
        yield f"[LOGS] - Generating SQL query"
        sql_query_messages = _texttosql_prompt(
            user_input=getattr(self.conversation_analytics, question_column_name),
            tenant_id=self.conversation_analytics.tenantId,
            database_info=self.retrieval_logs.relevantColumns,
            example_sql=self.retrieval_logs.relevantSqlExamples,
            relationship_diagram=DatabaseConfig().DATABASE_INFORMATION_PROMPT_TEMPLATE,
        )
        (
            self.conversation_analytics.sqlQueryChatCompletionTime,
            sql_chat_completion_response,
        ) = openai_manager.chat_completion(
            transaction_id=self.conversation_analytics.conversationID,
            messages=sql_query_messages,
        )

        self.conversation_analytics.totalChatCompletionCalls += 1
        self.conversation_analytics.sqlQueryChatCompletionInputToken = (
            sql_chat_completion_response["usage"]["prompt_tokens"]
        )
        self.conversation_analytics.sqlQueryChatCompletionOutputToken = (
            sql_chat_completion_response["usage"]["completion_tokens"]
        )

        # parsing sql gpt response
        yield f"[LOGS] - Parsing SQL query"
        sql_flag, self.conversation_analytics.sqlQuery = sql_response_parser(
            transaction_id=self.conversation_analytics.conversationID,
            gpt_response=sql_chat_completion_response,
        )
        if not sql_flag:
            self.conversation_analytics.answer = self.conversation_analytics.sqlQuery
            self.conversation_analytics.sqlQuery = ""
            yield json.dumps(
                {
                    "type": "sqlError",
                    "content": self.conversation_analytics.answer,
                }
            )
            self.conversation_analytics.to_sql()
            self.retrieval_logs.to_sql(
                conversation_analytics=self.conversation_analytics
            )
            yield json.dumps(
                api_response_builder(
                    conversation_analytics=self.conversation_analytics,
                    streaming=True,
                )
            )
            return
        del sql_chat_completion_response
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - SQL query generated"
        )

        # yield f"[LOGS] - Validating SQL query"
        self.conversation_analytics.sqlQuery = (
            f"SET useMultistageEngine=true; {self.conversation_analytics.sqlQuery}"
        )
        yield json.dumps(
            {
                "type": "sqlQuery",
                "content": self.conversation_analytics.sqlQuery,
            }
        )
        # STEP 6 : Execute SQL query
        yield f"[LOGS] - Executing SQL query"
        self.conversation_analytics.sqlQueryExecutionTime, sql_execution_response = (
            pinot_manager.fetch_data(
                transaction_id=self.conversation_analytics.conversationID,
                sql_query=self.conversation_analytics.sqlQuery,
            )
        )
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - SQL query executed"
        )
        self.conversation_analytics.sqlQueryResponse = sql_execution_response.to_json(
            orient="records", date_format="iso"
        )
        sql_result_markdown = sql_execution_response.to_markdown()
        sql_result_markdown = clean_string(sql_result_markdown)
        yield f"[LOGS] - SQL query executed"
        yield json.dumps(
            {
                "type": "sqlQueryResponse",
                "content": self.conversation_analytics.sqlQueryResponse,
            }
        )

        # STEP 7 : Generate answer
        answer_messages = _answer_prompt(
            user_input=getattr(self.conversation_analytics, question_column_name),
            sql_query=self.conversation_analytics.sqlQuery,
            sql_result=sql_result_markdown,
        )
        yield f"[LOGS] - Generating answer"
        self.conversation_analytics.answerChatCompletionTime, answer_response = (
            openai_manager.chat_completion(
                transaction_id=self.conversation_analytics.conversationID,
                messages=answer_messages,
            )
        )
        self.conversation_analytics.totalChatCompletionCalls += 1
        self.conversation_analytics.answerChatCompletionInputToken = answer_response[
            "usage"
        ]["prompt_tokens"]
        self.conversation_analytics.answerChatCompletionOutputToken = answer_response[
            "usage"
        ]["completion_tokens"]
        yield f"[LOGS] - Parsing answer"
        self.conversation_analytics.answer = answer_response_parser(
            transaction_id=self.conversation_analytics.conversationID,
            gpt_response=answer_response,
        )
        del answer_response
        logger.info(
            f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Answer generated"
        )
        yield json.dumps(
            {"type": "answer", "content": self.conversation_analytics.answer}
        )
        if not sql_execution_response.empty and should_generate_chart(
            sql_execution_response
        ):
            # STEP 8 : Generate Graph
            yield f"[LOGS] - Generating Graph"
            logger.info(
                f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Generating Graph"
            )
            data_types = sql_execution_response.dtypes
            graph_messages = _graph_prompt(
                user_input=getattr(self.conversation_analytics, question_column_name),
                sql_query=self.conversation_analytics.sqlQuery,
                data_type=data_types,
            )
            self.conversation_analytics.graphChatCompletionTime, graph_response = (
                openai_manager.chat_completion(
                    transaction_id=self.conversation_analytics.conversationID,
                    messages=graph_messages,
                    response_format={"type": "text"},
                )
            )
            self.conversation_analytics.totalChatCompletionCalls += 1
            self.conversation_analytics.graphChatCompletionInputToken = graph_response[
                "usage"
            ]["prompt_tokens"]
            self.conversation_analytics.graphChatCompletionOutputToken = graph_response[
                "usage"
            ]["completion_tokens"]
            python_plotly_code = graph_response["choices"][0]["message"]["content"]
            self.conversation_analytics.graphGenerationCode = _sanitize_plotly_code(
                _extract_python_code(python_plotly_code)
            )
            del graph_response
            logger.info(
                f"[biAssistant][get_answer][{self.conversation_analytics.conversationID}] - Graph code generated"
            )
            yield f"[LOGS] - Graph code generated"
            # STEP 9 : Generate Graph Figure
            fig = get_plotly_figure(
                plotly_code=self.conversation_analytics.graphGenerationCode,
                df=sql_execution_response,
            )
            fig_json = fig.to_json()
            self.conversation_analytics.graphFigureJson = fig_json
            yield f"[LOGS] - Graph figure generated"

        del sql_execution_response
        self.conversation_analytics.to_sql()
        self.retrieval_logs.to_sql(conversation_analytics=self.conversation_analytics)
        yield json.dumps(
            api_response_builder(
                conversation_analytics=self.conversation_analytics,
                streaming=True,
            )
        )
        return
