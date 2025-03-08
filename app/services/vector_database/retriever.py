"""Vector retrieval functionality for the database.

This module provides retrieval operations for vector embeddings and keyword-based search
using BM25 algorithm.
"""

import asyncio
from typing import List, Optional

import asyncpg
from django.conf import settings
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents.base import Document
from structlog import get_logger

from app.models import VideoChunk

logger = get_logger(__name__)


class VectorRetriever:
    """Handles vector and keyword-based retrieval operations.

    This class provides methods for checking document existence in the database
    and performing keyword-based searches using BM25 algorithm.
    """

    @staticmethod
    def get_non_existing_ids(ids: List[str]) -> List[str]:
        """Retrieve IDs that do not exist in the database.

        Args:
            ids: List of document IDs to check.

        Returns:
            List[str]: List of IDs that don't exist in the database.

        Note:
            Uses asyncpg for efficient database querying.
        """
        if not ids:
            return []

        try:
            # Use a synchronous method to create a connection pool
            async def _get_non_existing_ids():
                async with asyncpg.create_pool(
                    user=settings.DATABASES["default"]["USER"],
                    password=settings.DATABASES["default"]["PASSWORD"],
                    database=settings.DATABASES["default"]["NAME"],
                    host=settings.DATABASES["default"]["HOST"],
                    port=settings.DATABASES["default"]["PORT"],
                ) as pool:
                    async with pool.acquire() as conn:
                        values_clause = ", ".join(f"('{id}')" for id in ids)
                        raw_query = f"""
                            SELECT input_id
                            FROM (VALUES {values_clause}) AS input_ids(input_id)
                            WHERE input_id NOT IN (SELECT id FROM langchain_pg_embedding);
                        """
                        rows = await conn.fetch(raw_query)
                        return [row["input_id"] for row in rows]

            # Use asyncio.run to execute the async function synchronously
            return asyncio.run(_get_non_existing_ids())
        except Exception as e:
            logger.error("Error getting non-existing IDs", error=str(e))
            return []

    @classmethod
    def get_bm25_retriever(cls, channel_id: str, **kwargs) -> Optional[BM25Retriever]:
        """Get a BM25Retriever for the given channel.

        Args:
            channel_id: The ID of the channel to create the retriever for.
            **kwargs: Additional keyword arguments for retriever configuration.

        Returns:
            Optional[BM25Retriever]: Configured BM25Retriever instance or None if creation fails.
        """
        try:
            chunks = list(VideoChunk.objects.filter(video__channel_id=channel_id))
            documents = [
                Document(
                    page_content=chunk.text,
                    metadata={
                        **chunk.dict(),
                        "channel_id": channel_id,
                        "video_id": chunk.video.id if chunk.video else None,
                    },
                )
                for chunk in chunks
            ]
            return BM25Retriever.from_documents(documents or [])
        except Exception as e:
            logger.error("Error creating BM25Retriever", error=str(e))
            return None

    @classmethod
    def keyword_search(cls, query: str, channel_id: str, **kwargs) -> List[Document]:
        """Perform keyword-based search using BM25.

        Args:
            query: The search query string.
            channel_id: The ID of the channel to search in.
            **kwargs: Additional keyword arguments for search configuration.

        Returns:
            List[Document]: List of matching documents, empty list if retriever not found.
        """
        retriever = cls.get_bm25_retriever(channel_id, **kwargs)
        if not retriever:
            logger.warning("No Keyword retriever found for channel", channel_id=channel_id)
            return []
        return retriever.invoke(query)
