from typing import Any


class CustomException(Exception):
    """
    Custom exception class for AI exceptions.

    Attributes:
        error (str): The error code or identifier.
        message (str): The error message.
        result (Any): Additional result or data associated with the exception.
        StatusCode (int): The HTTP status code associated with the exception.
        conversation_analytics: Additional analytics data associated with the conversation.
    """

    def __init__(
        self,
        error: str = None,
        message: str = None,
        result: Any = None,
        StatusCode: int = 500,
        conversation_analytics=None,
    ):
        self.error = error
        self.message = message
        self.result = result
        self.StatusCode = StatusCode
        self.conversation_analytics = conversation_analytics

    def __str__(self):
        return f"[CustomException]: [{self.StatusCode}] {self.error or 'Unknown error'} - {self.message or ''} {self.result or ''}"
