"""Pydantic schemas for vector store and search-related data models.

This module defines data models used for representing video chunks,
video metadata, and vector store query responses using Pydantic.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ChunkSchema(BaseModel):
    """Represents a transcript chunk from a video.

    This schema defines the structure of a video transcript segment,
    including its text content, timing, and associated metadata.

    Attributes:
        text: The textual content of the transcript chunk.
        start: Start time of the chunk in string format.
        start_in_seconds: Optional start time in floating-point seconds.
        end: End time of the chunk in string format.
        videoId: Unique identifier of the source video.
        score: Relevance or similarity score of the chunk.
    """

    text: str = Field(..., description="Textual content of the transcript chunk")
    start: str = Field(..., description="Start time of the chunk")
    start_in_seconds: Optional[float] = Field(None, description="Start time in seconds")
    end: str = Field(..., description="End time of the chunk")
    videoId: str = Field(..., description="Unique identifier of the source video")
    score: float = Field(..., description="Relevance or similarity score of the chunk")


class VideoSchema(BaseModel):
    """Represents metadata for a YouTube video.

    This schema captures essential information about a video,
    including its identification, metadata, and optional scoring.

    Attributes:
        videoId: Unique identifier of the video.
        title: Title of the video.
        thumbnail: URL or path to the video's thumbnail image.
        published_at: Timestamp of when the video was published.
        avg_score: Optional average relevance score for the video.
    """

    videoId: str = Field(..., description="Unique identifier of the video")
    title: str = Field(..., description="Title of the video")
    thumbnail: str = Field(..., description="URL or path to the video's thumbnail")
    published_at: str = Field(..., description="Timestamp of video publication")
    avg_score: Optional[float] = Field(None, description="Average relevance score for the video")


class QueryVectorStoreResponse(BaseModel):
    """Represents the response from a vector store query.

    This schema encapsulates the results of a vector similarity search,
    providing both matching transcript chunks and associated video metadata.

    Attributes:
        chunks: List of transcript chunks matching the query.
        videos: List of videos associated with the matching chunks.
    """

    chunks: list[ChunkSchema] = Field(..., description="List of matching transcript chunks")
    videos: list[VideoSchema] = Field(..., description="List of videos associated with the chunks")
