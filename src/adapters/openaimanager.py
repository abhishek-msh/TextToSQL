import json
from typing import List, Dict, Any
from openai import AzureOpenAI
from config import OpenAIConfig
from src.custom_exception import CustomException
from src.decorators import measure_time
from src.adapters.loggingmanager import logger


class OpenaAIManager(OpenAIConfig):
    """
    A class that manages interactions with the OpenAI API.

    Inherits from the AzureConfig class.

    Methods:
        - create_embedding(transaction_id: str, text: str) -> dict:
            Creates an embedding for the given text using the OpenAI API.

        - chat_completion(transaction_id: str, messages: List[Dict[str, str]], temperature: float = 0.01, response_format={"type": "json_object"}) -> Dict[Any, Any]:
            Performs chat completion using the OpenAI API.
    """

    def __init__(self) -> None:
        """
        Initializes an instance of the OpenAIManager class.
        """
        super().__init__()
        self.embedding_error = "OpenAI Embedding Generation Failed"
        self.compeltion_error = "OpenAI Chat Completion Failed"
        self.openai_client = AzureOpenAI(
            api_key=self.OPENAI_API_KEY,
            api_version=self.OPENAI_API_VERSION,
            azure_endpoint=self.OPENAI_ENDPOINT,
            max_retries=self.MAX_RETRIES,
        )
        logger.info("[OpenaAIManager] - OpenAI Client initialized")

    @measure_time
    def create_embedding(self, text: str, transaction_id: str = "root"):
        """
        Creates an embedding for the given text using the OpenAI API.

        Args:
            transaction_id (str): The ID of the transaction.
            text (str): The input text for which the embedding needs to be generated.

        Returns:
            dict: A dictionary containing the response from the OpenAI API.

        Raises:
            CustomException: If there is an error while generating the embedding.
        """
        json_response = {}
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.EMBEDDING_MODEL,
                encoding_format="float",
            )
            json_response = response.model_dump()
            logger.info(
                f"[OpenaAIManager][create_embedding][{transaction_id}] - Embedding generated"
            )
        except Exception as create_embedding_exc:
            logger.exception(
                f"[OpenaAIManager][create_embedding][{transaction_id}] Error: {str(create_embedding_exc)}"
            )
            raise CustomException(error=self.embedding_error)
        return json_response

    @measure_time
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        transaction_id: str = "root",
        temperature: float = 0.01,
        response_format={"type": "json_object"},
        model: str = OpenAIConfig().CHATCOMPLETION_MODEL,
    ) -> Dict[Any, Any]:
        """
        Perform chat completion using OpenAI API.

        Args:
            transaction_id (str): The ID of the transaction.
            messages (List[Dict[str, str]]): List of messages in the conversation.
            temperature (float, optional): Controls the randomness of the output. Defaults to 0.
            max_tokens (int, optional): The maximum number of tokens in the response. Defaults to 500.
            response_format (dict, optional): The format of the response. Defaults to {"type": "json_object"}.
            model (str, optional): The model to use for chat completion. Defaults to OpenAIConfig().CHATCOMPLETION_MODEL.

        Returns:
            Dict[Any, Any]: The response from the OpenAI API.

        Raises:
            CustomException: If there is an error while performing chat completion.
            HTTPError: If there is an HTTP error during the API request.
            ConnectionError: If there is a connection error.
            Timeout: If the request times out.
            RequestException: If there is a general request exception.
            Exception: If there is any other exception.
        """
        json_response = {}
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
            )

            json_response = response.model_dump()
            logger.info(
                f"[OpenaAIManager][chat_completion][{transaction_id}] - Chat Completion Successful"
            )
        except Exception as chat_completion_exc:
            logger.exception(
                f"[OpenaAIManager][chat_completion][{transaction_id}] Error: {str(chat_completion_exc)}"
            )
            status_code = getattr(chat_completion_exc, "status_code", 500)
            error_message = (
                json.loads(getattr(chat_completion_exc, "response", None).text)
                .get("error", None)
                .get("message", None)
            )
            raise CustomException(
                error=self.compeltion_error,
                message=error_message,
                StatusCode=status_code,
            )
        return json_response


openai_manager = OpenaAIManager()
