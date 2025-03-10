"""Tools for vector database operations."""

import traceback
from collections import Counter
from typing import (
    Any,
    List,
)

import numpy as np
from asgiref.sync import sync_to_async
from langchain.tools import StructuredTool
from langchain_core.documents.base import Document
from sklearn.preprocessing import MinMaxScaler
from structlog import get_logger

from app.models import Video
from app.schemas import (
    ChunkSchema,
    QueryVectorStoreResponse,
    VectorDatabaseToolInput,
    VideoSchema,
)
from app.services.chunks_reranker import ChunksReRanker
from app.services.vector_database import (
    VectorDatabaseService,
    VectorRetriever,
    get_avg_score,
    minimise_chunks,
)

logger = get_logger(__name__)


class VectorDatabaseTools:
    """Tools for vector database operations."""

    vectorstore_service = VectorDatabaseService()
    _scaler = MinMaxScaler(feature_range=(0, 100))

    @classmethod
    def _standardize_scores(cls, chunks: List[ChunkSchema]) -> List[ChunkSchema]:
        """Standardize chunk scores to a 0-100 scale using MinMaxScaler.

        This method transforms the raw similarity scores of chunks to a standardized
        0-100 scale for better interpretability. It handles edge cases where scaling
        might fail and provides appropriate fallbacks.

        Args:
            chunks: List of chunks with raw similarity scores

        Returns:
            The same list of chunks with scores standardized to 0-100 scale

        Raises:
            No exceptions are raised as errors are handled internally
        """
        if not chunks:
            return chunks

        # Extract scores into a numpy array
        scores = np.array([chunk.score for chunk in chunks], dtype=np.float32).reshape(-1, 1)

        try:
            # Scale scores to 0-100 range
            scaled_scores = cls._scaler.fit_transform(scores)
            # Round to 2 decimal places
            scaled_scores = np.round(scaled_scores, 2)

            # Update chunks with new scores
            for chunk, score in zip(chunks, scaled_scores.flatten(), strict=True):
                chunk.score = float(score)
        except (ValueError, TypeError):
            # Fallback for invalid scores or edge cases
            default_score = 50
            for chunk in chunks:
                chunk.score = default_score

        return chunks

    @classmethod
    async def _get_video_data(cls, video_ids: List[str]) -> dict[str, dict[str, Any]]:
        """Fetch video data efficiently.

        Retrieves video information for the given video IDs using a single database query
        with optimized joins.

        Args:
            video_ids: List of video IDs to fetch data for.

        Returns:
            A dictionary mapping video IDs to their data with the following structure:
            {
                "video_id": {
                    "id": str,
                    "title": str,
                    "thumbnail": str,
                    "published_at": str,
                    "channel": str
                },
                ...
            }
        """
        # Single efficient query with select_related and values
        video_data = await sync_to_async(
            lambda: list(
                Video.objects.filter(id__in=video_ids)
                .select_related("channel")
                .values("id", "title", "thumbnail", "published_at", "channel__id")
            )
        )()

        # Create a mapping for efficient lookup
        return {
            str(video["id"]): {
                "id": str(video["id"]),
                "title": video["title"],
                "thumbnail": video["thumbnail"],
                "published_at": str(video["published_at"]),
                "channel": video["channel__id"],
            }
            for video in video_data
        }

    @classmethod
    async def similarity_videos_search(cls, query: str, channel_id: str, **kwargs) -> QueryVectorStoreResponse:
        """Search for videos based on a query, returning the most similar videos and their chunks.

        This method performs a semantic search using vector embeddings to find relevant
        video content. It's useful for retrieving videos not accessible through structured inputs.

        Args:
            query: Search query text to find similar content
            channel_id: YouTube channel ID to restrict the search
            **kwargs: Additional arguments to pass to the search

        Returns:
            QueryVectorStoreResponse: Object containing relevant chunks and videos matching the query

        Raises:
            ConnectionError: If unable to connect to the vector database
            ValueError: If the query or channel_id is invalid
        """
        logger.info("Starting search with query", query=query, channel_id=channel_id)

        vstore = await cls.vectorstore_service.get_vstore(channel_id)
        if not vstore:
            logger.warning("No vector store found for this channel")
            return QueryVectorStoreResponse(chunks=[], videos=[])

        # Use a semaphore to limit concurrent database operations
        similarity_results = []
        keyword_results = []

        # Perform similarity search
        logger.info("Performing similarity search...")
        try:
            # Use a separate task for similarity search
            similarity_results = await vstore.asimilarity_search(
                query, k=20, filter={"channel_id": {"$eq": channel_id}}
            )
            logger.info("Found results from similarity search", count=len(similarity_results))
        except Exception as e:
            logger.error("Error in similarity search", error=str(e), traceback=traceback.format_exc())
            similarity_results = []

        # Perform keyword search with fallback
        logger.info("Performing keyword search...")
        try:
            # Use a separate task for keyword search
            keyword_results = await VectorRetriever.keyword_search(query, channel_id)
            logger.info("Found keyword results", count=len(keyword_results))
        except Exception as e:
            logger.error("Error in keyword search", error=str(e), traceback=traceback.format_exc())
            keyword_results = []

        # Combine results from both searches
        combined_results = similarity_results + keyword_results
        logger.info("Combined results", count=len(combined_results))
        if not combined_results:
            logger.warning("No results found in any search")
            return QueryVectorStoreResponse(chunks=[], videos=[])

        # Extract unique video IDs
        video_ids = list({r.metadata.get("video_id") for r in combined_results if r.metadata.get("video_id")})
        if not video_ids:
            logger.warning("No video IDs found in search results for query", query=query, channel_id=channel_id)
            return QueryVectorStoreResponse(chunks=[], videos=[])
        logger.info("Found unique video IDs", count=len(video_ids))

        # Fetch video data efficiently
        video_map = await cls._get_video_data(video_ids)
        logger.info("Retrieved video objects", count=len(video_map))

        # Enrich search results with video data
        logger.info("Enriching search results with video data...")
        enriched_results = []
        for r in combined_results:
            video_id = r.metadata.get("video_id")
            if video_id and video_id in video_map:
                video = video_map[video_id]
                video_dict = {
                    "id": video.get("id"),
                    "title": video.get("title"),
                    "thumbnail": video.get("thumbnail"),
                    "published_at": video.get("published_at"),
                    "channel": video.get("channel"),
                }
                enriched_results.append(
                    Document(
                        page_content=r.page_content,
                        metadata={**r.metadata, "video": video_dict},
                    )
                )
        logger.info("Enriched results with video data", count=len(enriched_results))

        if not enriched_results:
            logger.warning("No enriched results found")
            return QueryVectorStoreResponse(chunks=[], videos=[])

        # Remove duplicates
        logger.info("Removing duplicates...")
        seen = set()
        enriched_results = [
            doc for doc in enriched_results if not (doc.page_content in seen or seen.add(doc.page_content))
        ]
        logger.info("After deduplication", count=len(enriched_results))

        # Rerank results with fallback
        logger.info("Reranking results...")
        try:
            reranked_results = ChunksReRanker.rerank(query, enriched_results)
            if not reranked_results:
                logger.warning("No results after reranking, falling back to original results")
                # Convert enriched results to the expected format
                reranked_results = [
                    {
                        "content": doc.page_content,
                        "video_id": doc.metadata.get("video_id"),
                        "score": 0.5,  # Default middle score
                        **doc.metadata,
                    }
                    for doc in enriched_results[:10]  # Limit to top 10 for reasonable results
                ]
        except Exception as e:
            logger.warning("Error in reranking", error=str(e))
            reranked_results = [
                {
                    "content": doc.page_content,
                    "video_id": doc.metadata.get("video_id"),
                    "score": 0.5,
                    **doc.metadata,
                }
                for doc in enriched_results[:10]
            ]

        if not reranked_results:
            logger.warning("No results after reranking and fallback")
            return QueryVectorStoreResponse(chunks=[], videos=[])

        # Filter valid results
        logger.info("Filtering valid results...")
        valid_results = [r for r in reranked_results if r.get("video_id") or r.get("videoId")]
        if not valid_results:
            logger.warning("No valid results found")
            return QueryVectorStoreResponse(chunks=[], videos=[])
        logger.info("Found valid results", count=len(valid_results))

        # Normalize video_id key to ensure consistent format
        for r in valid_results:
            if "videoId" in r and "video_id" not in r:
                r["video_id"] = r["videoId"]

        video_id_counter = Counter(r["video_id"] for r in valid_results)
        most_common_video_ids = [vid for vid, _ in video_id_counter.most_common(5)]
        logger.info("Found most common videos", count=len(most_common_video_ids))

        top_chunks = [r for r in valid_results if r["video_id"] in most_common_video_ids]
        logger.info("Selected top chunks", count=len(top_chunks))

        # Standardize chunk scores before calculating video averages
        standardized_chunks = cls._standardize_scores(minimise_chunks(top_chunks))
        logger.info("Standardized chunk scores to 0-100 range")

        # More forgiving video schema creation
        logger.info("Creating video schemas...")
        unique_videos = []
        for vid in most_common_video_ids:
            if vid not in video_map:
                continue
            video_info = video_map[vid]
            unique_videos.append(
                VideoSchema(
                    videoId=vid,
                    title=video_info["title"] or "Untitled Video",
                    thumbnail=video_info["thumbnail"] or "",
                    published_at=video_info["published_at"],
                    avg_score=get_avg_score(standardized_chunks, vid),
                )
            )

        if not unique_videos and standardized_chunks:
            logger.info("No video schemas created but have chunks, creating minimal video schema")
            # Create minimal video schema from chunk data
            for chunk in standardized_chunks[:5]:  # Limit to 5 videos
                # Access chunk attributes properly using dot notation
                vid = getattr(chunk, "video_id", None) or getattr(chunk, "videoId", None)
                if not vid:
                    continue
                unique_videos.append(
                    VideoSchema(
                        videoId=vid,
                        title=getattr(chunk, "title", "Unknown Title"),
                        thumbnail="",
                        published_at="",
                        avg_score=getattr(chunk, "score", 50),  # Using standardized score
                    )
                )

        unique_videos.sort(key=lambda x: x.avg_score, reverse=True)
        logger.info("Created video schemas", count=len(unique_videos))

        logger.info("Returning final response...")
        return QueryVectorStoreResponse(chunks=standardized_chunks, videos=unique_videos)

    @classmethod
    def tool(cls) -> StructuredTool:
        """Create a structured tool for searching videos."""
        return StructuredTool.from_function(
            coroutine=cls.similarity_videos_search,
            name="similarity_videos_search",
            description="Advanced semantic video search tool powered by vector embeddings. Use this tool to: "
            "- Find videos that match the semantic meaning of your query, not just exact keywords "
            "- Discover relevant video content across different topics and contexts "
            "- Retrieve video chunks that closely align with the intent of your search "
            "- Explore nuanced connections between search queries and video content "
            "Ideal for complex information retrieval tasks that require understanding context, "
            "subtext, and deeper semantic relationships in video transcripts."
            "The tool may return some irrelevant results, your task is to provide the user with the most relevant results",
            args_schema=VectorDatabaseToolInput,
            handle_tool_error=True,
        )
