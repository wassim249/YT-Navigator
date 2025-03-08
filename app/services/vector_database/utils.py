"""Utility functions for vector database operations.

This module provides utility functions for generating unique IDs for documents,
calculating average scores, and converting chunks to minimal representations.
"""

import hashlib
import json
from typing import List

from langchain_core.documents.base import Document

from app.schemas import ChunkSchema


def get_chunk_id(chunk: Document) -> str:
    """Generate a unique ID for a document chunk."""
    serialized = json.dumps(
        {"content": chunk.page_content, "metadata": {k: v for k, v in chunk.metadata.items() if v is not None}}
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def get_avg_score(chunks: List[ChunkSchema], video_id: str) -> float:
    """Calculate the average score for a video."""
    import torch

    relevant_chunks = [r for r in chunks if r.videoId == video_id]
    if not relevant_chunks:
        return 0.0

    # Extract scores, handling both tensor and float types
    scores = []
    for r in relevant_chunks:
        score = r.score
        # If it's a tensor, convert to float
        if isinstance(score, torch.Tensor):
            score = score.item()
        scores.append(score)

    if not scores:
        return 0.0  # Safeguard against division by zero

    return sum(scores) / len(scores)


def minimise_chunks(chunks: List[dict]) -> List[ChunkSchema]:
    """Convert chunks to a minimal representation."""
    return [
        ChunkSchema(
            text=r["text"],
            start=str(r["start"]),
            end=str(r["end"]),
            videoId=r["video_id"],
            score=r["score"],
        )
        for r in chunks
        if all(key in r for key in ["text", "start", "end", "video_id", "score"])
    ]
