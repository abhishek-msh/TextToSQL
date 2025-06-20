from pymilvus import (
    MilvusClient,
)
from pymilvus.exceptions import MilvusException
from config import MilvusConfig
from src.custom_exception import CustomException
from src.adapters.loggingmanager import logger
from src.decorators import measure_time
from typing import List, Dict, Any


class MilvusManager(MilvusConfig):
    def __init__(self) -> None:
        """
        Contains all the methods to manage the Milvus server
        """
        super().__init__()
        self.milvus_error = "Milvus Server Failed"
        try:
            self.milvus_client = MilvusClient(
                uri=f"tcp://{self.MILVUS_HOST}:{self.MILVUS_PORT}",
                timeout=self.MILVUS_TIMEOUT,
            )
            logger.info("[MilvusManager] - Milvus client connected")
        except MilvusException as milvus_exc:
            logger.exception(
                f"[MilvusManager] - Failed to connect to Milvus server: {milvus_exc}"
            )
            raise
        except Exception as exc:
            logger.exception(
                f"[MilvusManager] - Failed to connect to Milvus server: {exc}"
            )
            raise

    def check_collection_exists(
        self,
        transaction_id: str,
        collection_name: str = MilvusConfig().MILVUS_COLLECTION_NAME,
    ) -> bool:
        """
        Check if the collection exists in the Milvus server

        Args:
            transaction_id (str): The transaction ID
            collection_name (str): The name of the collection to check

        Returns:
            bool: True if the collection exists, False otherwise
        """
        try:
            status = self.milvus_client.has_collection(collection_name)
            logger.info(
                f"[MilvusManager][check_collection_exists] [{transaction_id}] - Collection {collection_name} exists: {status}"
            )
            return status
        except MilvusException as milvus_exc:
            logger.exception(
                f"[MilvusManager][check_collection_exists] [{transaction_id}] - Failed to check collection existence: {milvus_exc}"
            )
            raise CustomException(error=self.milvus_error, message=str(milvus_exc))
        except Exception as exc:
            logger.exception(
                f"[MilvusManager][check_collection_exists] [{transaction_id}] - Failed to check collection existence: {exc}"
            )
            raise CustomException(error=self.milvus_error, message=str(exc))

    @measure_time
    def search_index(
        self,
        transaction_id: str,
        collection_name: str,
        text_embedding: List[float],
        return_fields: List[str],
        filter_expr: str = "",
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Searches for similar items in a specified Milvus collection based on a given text embedding.

        Args:
            transaction_id (str): A unique identifier for the transaction.
            collection_name (str): The name of the Milvus collection to search in.
            text_embedding (List[float]): The embedding vector to search for similar items.
            return_fields (List[str]): A list of fields to include in the search results.
            filter_expr (str, optional): An optional filter expression to apply to the search. Defaults to None.
            top_k (int, optional): The number of top similar items to retrieve. Defaults to 5.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing the search results.
        """
        if not self.check_collection_exists(transaction_id, collection_name):
            raise CustomException(
                error=self.milvus_error,
                message=f"Collection {collection_name} does not exist",
            )
        try:
            retrieved_data = self.milvus_client.search(
                collection_name=collection_name,
                data=[text_embedding],
                limit=top_k,
                output_fields=return_fields,
                filter=filter_expr,
            )
            logger.info(
                f"[MilvusManager][search_index] [{transaction_id}] - Data retrieved successfully from collection {collection_name}"
            )
            return retrieved_data
        except MilvusException as milvus_exc:
            logger.exception(
                f"[MilvusManager][search_index] [{transaction_id}] - Failed to retrieve data from collection {collection_name}: {milvus_exc}"
            )
            raise CustomException(error=self.milvus_error, message=str(milvus_exc))
        except Exception as exc:
            logger.exception(
                f"[MilvusManager][search_index] [{transaction_id}] - Failed to retrieve data from collection {collection_name}: {exc}"
            )
            raise CustomException(error=self.milvus_error, message=str(exc))


milvus_manager = MilvusManager()
