"""Service for reranking document chunks using a cross-encoder model."""

import concurrent.futures
from typing import (
    Any,
    Dict,
    List,
)

from langchain.docstore.document import Document
from structlog import get_logger

from app.services.chunks_reranker import config
from app.services.chunks_reranker.model_manager import ModelManager

logger = get_logger(__name__)


class ChunksReRanker:
    """Reranks document chunks using a cross-encoder model."""

    _model_manager = ModelManager()

    def __init__(self, batch_size: int = None):
        """Initialize the reranker with specified batch size.

        Args:
            batch_size: Number of documents to process in each batch.
                Defaults to config.DEFAULT_BATCH_SIZE if not provided.
        """
        self.batch_size = batch_size or config.DEFAULT_BATCH_SIZE

        # Validate batch size
        if self.batch_size > config.MAX_BATCH_SIZE:
            logger.warning("Batch size exceeds maximum. Capping ", max_batch_size=config.MAX_BATCH_SIZE)
            self.batch_size = config.MAX_BATCH_SIZE

        logger.info("Initialized ChunksReRanker", batch_size=self.batch_size)

    @classmethod
    def rerank(cls, query: str, docs: List[Document]) -> List[Dict[str, Any]]:
        """Sync class method to rerank documents using the cross-encoder model.

        Args:
            query: The search query
            docs: List of documents to rerank

        Returns:
            List of ranked documents with scores
        """
        # Create an instance of the reranker
        reranker = cls()
        return reranker._rerank(query, docs)

    def _rerank(self, query: str, docs: List[Document]) -> List[Dict[str, Any]]:
        """Sync internal method to rerank documents using the cross-encoder model with parallel processing.

        Args:
            query: The search query
            docs: List of documents to rerank

        Returns:
            List of ranked documents with scores
        """
        if not docs:
            logger.warning("No documents provided for reranking")
            return []

        logger.info("Starting reranking", num_docs=len(docs))

        # Split documents into chunks for batch processing
        doc_chunks = self.chunk_docs(docs, self.batch_size)

        # Use a thread pool executor for parallel processing
        with concurrent.futures.ThreadPoolExecutor() as pool:
            # Process chunks in parallel
            tasks = [pool.submit(self.process_chunk, query, chunk) for chunk in doc_chunks]

            # Wait for all tasks to complete
            all_ranked_docs = []
            for future in concurrent.futures.as_completed(tasks):
                try:
                    ranked_chunk = future.result()
                    all_ranked_docs.extend(ranked_chunk)
                except Exception as e:
                    logger.error("Error processing chunk", error=e)

        # Sort all ranked documents by score from highest to lowest
        all_ranked_docs.sort(key=lambda x: x["score"], reverse=True)

        logger.info("Completed reranking", num_docs=len(docs))
        return all_ranked_docs

    @staticmethod
    def chunk_docs(docs: List[Document], size: int) -> List[List[Document]]:
        """Divide the documents into chunks of the given size.

        Args:
            docs: List of documents to chunk
            size: Size of each chunk

        Returns:
            List of document chunks
        """
        return [docs[i : i + size] for i in range(0, len(docs), size)]

    def prepare_pairs(self, query: str, chunk: List[Document]) -> List[tuple]:
        """Prepare the query-document pairs for scoring.

        Args:
            query: Search query
            chunk: List of documents

        Returns:
            List of (query, document) pairs
        """
        return [(query, doc.page_content) for doc in chunk]

    def process_chunk(self, query: str, chunk: List[Document]) -> List[Dict[str, Any]]:
        """Process a single chunk of documents.

        Args:
            query: Search query
            chunk: List of documents to process

        Returns:
            List of ranked documents with scores
        """
        try:
            pairs = self.prepare_pairs(query, chunk)
            model = self._model_manager.get_cross_encoder()

            # Get scores for the chunk
            scores = model.predict(pairs)

            # Create ranked documents with scores
            ranked_docs = []
            for doc, score in zip(chunk, scores, strict=True):
                ranked_docs.append({"score": float(score), **doc.metadata, "text": doc.page_content})

            logger.debug("Successfully processed chunk", num_docs=len(chunk))
            return ranked_docs

        except Exception as e:
            logger.error("Error processing chunk", error=e)
            # Return documents with zero score in case of error
            return [{"score": 0, **doc.metadata, "text": doc.page_content} for doc in chunk]
