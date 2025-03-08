"""Vector retrieval functionality for the database.

This module provides retrieval operations for vector embeddings and keyword-based search
using BM25 algorithm.
"""

import traceback
from typing import (
    List,
    Optional,
)

import asyncpg
from asgiref.sync import sync_to_async
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
    async def get_non_existing_ids(ids: List[str]) -> List[str]:
        """Retrieve IDs that do not exist in the database.

        Args:
            ids: List of document IDs to check.

        Returns:
            List[str]: List of IDs that don't exist in the database.

        Raises:
            Exception: If there's an error during the retrieval process.

        Note:
            Uses asyncpg for efficient database querying.
        """
        if not ids:
            return []

        try:
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
        except Exception as e:
            logger.error("Error getting non-existing IDs", error=str(e), traceback=traceback.format_exc())
            raise e

    @classmethod
    async def get_bm25_retriever(cls, channel_id: str, **kwargs) -> Optional[BM25Retriever]:
        """Get a BM25Retriever for the given channel.

        Args:
            channel_id: The ID of the channel to create the retriever for.
            **kwargs: Additional keyword arguments for retriever configuration.

        Returns:
            Optional[BM25Retriever]: Configured BM25Retriever instance or None if creation fails.
        """
        try:
            # Use select_related to prefetch the video relationship to avoid async access issues
            chunks = await sync_to_async(
                lambda: list(VideoChunk.objects.filter(video__channel_id=channel_id).select_related("video"))
            )()

            # Process all chunks in a sync context to avoid async DB access
            def prepare_documents():
                return [
                    Document(
                        page_content=chunk.text,
                        metadata={
                            "id": chunk.id,
                            "video_id": chunk.video.id if hasattr(chunk, "video") and chunk.video else None,
                            "start": chunk.start,
                            "end": chunk.end,
                            "text": chunk.text,
                            "channel_id": channel_id,
                        },
                    )
                    for chunk in chunks
                ]

            # Execute document preparation in sync context
            documents = await sync_to_async(prepare_documents)()
            return BM25Retriever.from_documents(documents or [])
        except Exception as e:
            logger.error("Error creating BM25Retriever", error=str(e), traceback=traceback.format_exc())
            return None

    @classmethod
    async def keyword_search(cls, query: str, channel_id: str, **kwargs) -> List[Document]:
        """Perform keyword-based search using BM25.

        Args:
            query: The search query string.
            channel_id: The ID of the channel to search in.
            **kwargs: Additional keyword arguments for search configuration.

        Returns:
            List[Document]: List of matching documents, empty list if retriever not found.
        """
        retriever = await cls.get_bm25_retriever(channel_id, **kwargs)
        if not retriever:
            logger.warning("No Keyword retriever found for channel", channel_id=channel_id)
            return []
        return await retriever.ainvoke(query)
