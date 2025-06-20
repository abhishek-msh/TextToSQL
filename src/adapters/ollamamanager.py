import json
from typing import List, Dict, Any
from openai import OpenAI
from config import OllamaConfig
from src.custom_exception import CustomException
from src.decorators import measure_time
from src.adapters.loggingmanager import logger


class OllamaManager(OllamaConfig):
    """
    A class that manages interactions with the Ollama API.

    Inherits from the OllamaConfig class.

    Methods:
        - create_embedding(transaction_id: str, text: str) -> dict:
            Creates an embedding for the given text using the Ollama API.

        - chat_completion(transaction_id: str, messages: List[Dict[str, str]], temperature: float = 0.01, response_format={"type": "json_object"}) -> Dict[Any, Any]:
            Performs chat completion using the Ollama API.
    """

    def __init__(self) -> None:
        """
        Initializes an instance of the OpenAIManager class.
        """
        super().__init__()
        self.compeltion_error = "Ollama Chat Completion Failed"
        self.ollama_client = OpenAI(
            base_url=self.OLLAMA_SERVER,
            api_key=self.OLLAMA_API_KEY,
        )
        logger.info("[OllamaManager] - Ollama Client initialized")

    @measure_time
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        transaction_id: str = "root",
        temperature: float = 0.01,
        response_format={"type": "json_object"},
    ) -> Dict[Any, Any]:
        """
        Perform chat completion using Ollama API.

        Args:
            transaction_id (str): The ID of the transaction.
            messages (List[Dict[str, str]]): List of messages in the conversation.
            temperature (float, optional): Controls the randomness of the output. Defaults to 0.
            max_tokens (int, optional): The maximum number of tokens in the response. Defaults to 500.

        Returns:
            Dict[Any, Any]: The response from the Ollama API.

        Raises:
            CustomException: If there is an error while performing chat completion.
            HTTPError: If there is an HTTP error during the API request.
            ConnectionError: If there is a connection error.
            Timeout: If the request times out.
            RequestException: If there is a general request exception.
            Exception: If there is any other exception.
        """
        print("here1")
        json_response = {}
        try:
            response = self.ollama_client.chat.completions.create(
                model=self.OLLAMA_MODEL,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
            )

            json_response = response.model_dump()
            logger.info(
                f"[OllamaManager][chat_completion][{transaction_id}] - Chat Completion Successful"
            )
        except Exception as chat_completion_exc:
            logger.exception(
                f"[OllamaManager][chat_completion][{transaction_id}] Error: {str(chat_completion_exc)}"
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


ollama_manager = OllamaManager()
