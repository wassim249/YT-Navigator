"""This module provides a service for managing vector database operations and embeddings.

The VectorDatabaseService class handles vector storage operations, including initialization of embeddings,
managing database instances, and handling document operations.
"""

import json
import traceback
from typing import (
    Dict,
    List,
    Optional,
)

import torch
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import connection
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents.base import Document
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_postgres.vectorstores import PGVector
from sqlalchemy.ext.asyncio import create_async_engine
from structlog import get_logger

from app.models import (
    Video,
    VideoChunk,
)
from yt_navigator.settings import DATABASE_URL

from .retriever import VectorRetriever
from .utils import get_chunk_id

logger = get_logger(__name__)


class VectorDatabaseService:
    """Service for managing vector database operations and embeddings.

    This service handles vector storage operations, including initialization of embeddings,
    managing database instances, and handling document operations.
    """

    def __init__(self):
        """Initialize the VectorDatabaseService.

        Sets up the device for model inference and initializes the embeddings model
        with the configured settings.
        """
        self._ENGINE = create_async_engine(DATABASE_URL)

        # Determine the best available device
        self.device = self._get_optimal_device()

        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={
                "device": self.device,
                "trust_remote_code": True,
            },
            encode_kwargs={
                "normalize_embeddings": settings.EMBEDDING_NORMALIZE_EMBEDDINGS,
                "batch_size": settings.EMBEDDING_BATCH_SIZE,
            },
        )
        self._db_instances: Dict[str, Optional[PGVector]] = {}
        self._bm25_retrievers: Dict[str, Optional[BM25Retriever]] = {}

    def _get_optimal_device(self) -> str:
        """Determine the optimal device for model inference.

        Returns:
            str: 'cuda' if available and supported, otherwise 'cpu'

        Note:
            This method checks for CUDA availability and falls back to CPU if
            CUDA is not available or if an error occurs during detection.
        """
        try:
            # Check if CUDA is available and has GPU devices
            if torch.cuda.is_available() and torch.cuda.device_count() > 0:
                logger.info("CUDA is available. Using GPU.")
                return "cuda"
            else:
                logger.warning("CUDA not available. Falling back to CPU.")
                return "cpu"
        except Exception as e:
            logger.error(f"Error detecting device: {e}. Defaulting to CPU.")
            return "cpu"

    def get_vstore(self, channel_id: str) -> Optional[PGVector]:
        """Get or create a vector store instance for a specific channel.

        Args:
            channel_id: The ID of the channel to get the vector store for.

        Returns:
            Optional[PGVector]: The vector store instance for the channel,
                or None if creation fails.
        """
        if channel_id not in self._db_instances:
            try:
                self._db_instances[channel_id] = PGVector(
                    connection=self._ENGINE,
                    collection_name=f"{channel_id}",
                    embeddings=self.embeddings,
                    create_extension=False,
                    use_jsonb=True,
                    async_mode=True,
                )
            except Exception as e:
                logger.error(f"Failed to create PGVector instance: {str(e)}")
                self._db_instances[channel_id] = None
        return self._db_instances[channel_id]

    def dict_to_langchain_documents(self, data: List[dict], **kwargs) -> List[Document]:
        """Convert dictionary data to Langchain Document objects.

        Args:
            data: List of dictionaries containing document data.
            **kwargs: Additional keyword arguments, must include 'channel_id'.

        Returns:
            List[Document]: List of Langchain Document objects with metadata.
        """
        return [
            Document(
                page_content=chunk["text"],
                metadata={**{k: v for k, v in chunk.items() if v is not None}, "channel_id": kwargs["channel_id"]},
            )
            for chunk in data
        ]

    @staticmethod
    def delete_video(video_id: str) -> int:
        """Delete a video and its associated vector embeddings.

        Args:
            video_id: The ID of the video to delete.

        Returns:
            int: Number of deleted records (0 if deletion fails).
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """DELETE FROM langchain_pg_embedding WHERE cmetadata @> %s""",
                    [json.dumps({"videoId": video_id})],
                )
            return Video.objects.filter(id=video_id).delete()[0]
        except Exception as e:
            logger.error(f"Error deleting video {video_id}: {str(e)}")
            return 0

    async def add_chunks(self, chunks: List[dict], channel_id: str) -> None:
        """Add video chunks to the vector database and create VideoChunk records.

        Args:
            chunks: List of dictionaries containing chunk data.
            channel_id: The ID of the channel the chunks belong to.

        Raises:
            Exception: If there's an error during the chunk addition process.
        """
        logger.info("Adding chunks to the database", channel_id=channel_id)
        try:
            vstore = self.get_vstore(channel_id)
            if not vstore:
                logger.error("Failed to get vector store for channel", channel_id=channel_id)
                return

            documents = self.dict_to_langchain_documents(chunks, channel_id=channel_id)
            chunks_ids = [get_chunk_id(c) for c in documents]
            non_existing_ids = await VectorRetriever.get_non_existing_ids(chunks_ids)

            if non_existing_ids:
                non_existing_chunks = [c for c in documents if get_chunk_id(c) in non_existing_ids]
                logger.info("Adding new chunks to the database", new_chunks_count=len(non_existing_chunks))
                await vstore.aadd_documents(non_existing_chunks, ids=non_existing_ids)

            # Create a function that performs the entire synchronous operation
            async def get_existing_texts():
                @sync_to_async
                def _get_existing_texts():
                    return set(
                        VideoChunk.objects.filter(text__in=[c.page_content for c in documents]).values_list(
                            "text", flat=True
                        )
                    )

                return await _get_existing_texts()

            # Get existing texts using the properly wrapped function
            existing_texts = await get_existing_texts()
            filtered_chunks = [c for c in documents if c.page_content not in existing_texts]

            # Create a function that performs the entire synchronous operation for videos
            async def get_videos():
                @sync_to_async
                def _get_videos():
                    return {video.id: video for video in Video.objects.filter(channel_id=channel_id)}

                return await _get_videos()

            # Get videos using the properly wrapped function
            videos = await get_videos()

            video_chunks = [
                VideoChunk(
                    video=videos[c.metadata["videoId"]],
                    text=c.page_content,
                    start=c.metadata["start"],
                    end=c.metadata["end"],
                )
                for c in filtered_chunks
                if c.metadata.get("videoId") in videos
            ]

            if video_chunks:
                logger.info("Adding video chunks to the database", video_chunks_count=len(video_chunks))
                await VideoChunk.abulk_create(video_chunks)

        except Exception as e:
            logger.error("Error adding chunks", error=str(e), traceback=traceback.format_exc())
            raise
