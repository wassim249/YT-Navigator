"""Configuration settings for the chunks reranker package."""

from django.conf import settings

# Model settings
DEFAULT_MODEL_NAME = getattr(settings, "RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2")
MAX_SEQUENCE_LENGTH = getattr(settings, "RERANKER_MAX_SEQUENCE_LENGTH", 512)

# Batch processing settings
DEFAULT_BATCH_SIZE = getattr(settings, "RERANKER_DEFAULT_BATCH_SIZE", 32)
MAX_BATCH_SIZE = getattr(settings, "RERANKER_MAX_BATCH_SIZE", 64)

# Performance settings
ENABLE_CUDA_OPTIMIZATIONS = getattr(settings, "RERANKER_ENABLE_CUDA_OPTIMIZATIONS", True)
ENABLE_TF32 = getattr(settings, "RERANKER_ENABLE_TF32", True)
CUDA_BENCHMARK = getattr(settings, "RERANKER_CUDA_BENCHMARK", True)
