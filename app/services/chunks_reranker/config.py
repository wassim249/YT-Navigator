"""Configuration settings for the chunks reranker package."""

from django.conf import settings

# Model settings
RANKER_MODEL_NAME = getattr(settings, "RANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RANKER_MAX_SEQUENCE_LENGTH = getattr(settings, "RANKER_MAX_SEQUENCE_LENGTH", 512)

# Batch processing settings
DEFAULT_BATCH_SIZE = getattr(settings, "RERANKER_DEFAULT_BATCH_SIZE", 32)
MAX_BATCH_SIZE = getattr(settings, "RERANKER_MAX_BATCH_SIZE", 64)
