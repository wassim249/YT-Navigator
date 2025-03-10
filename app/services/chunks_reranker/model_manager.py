"""Model manager for the chunks reranker."""

import os
from functools import lru_cache
from typing import Optional

import torch
from sentence_transformers import CrossEncoder
from structlog import get_logger

from app.services.chunks_reranker import config

logger = get_logger(__name__)


class ModelManager:
    """Manages ML models with efficient resource utilization."""

    _instance: Optional["ModelManager"] = None

    def __new__(cls):
        """Create a singleton instance of the ModelManager.

        This method ensures only one instance of ModelManager exists throughout
        the application lifecycle, following the singleton pattern.

        Returns:
            ModelManager: The singleton instance of the ModelManager class.
        """
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the model manager with optimal settings."""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("Initializing ModelManager with device", device=self.device)
        self._cross_encoder = None

        # Set optimal torch settings for inference
        if self.device.type == "cuda":
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            logger.info("CUDA optimizations enabled")

    @property
    @lru_cache(maxsize=1)  # noqa: B019
    def cross_encoder(self) -> CrossEncoder:
        """Lazy load and cache the cross-encoder model.

        Returns:
            CrossEncoder: The cross-encoder model instance.
        """
        if self._cross_encoder is None:
            model_name = config.RANKER_MODEL_NAME
            logger.info("Loading cross-encoder model", model_name=model_name)
            try:
                self._cross_encoder = CrossEncoder(
                    model_name, max_length=config.RANKER_MAX_SEQUENCE_LENGTH, device=self.device
                )
                logger.info("Cross-encoder model loaded successfully")
            except Exception as e:
                logger.error("Error loading cross-encoder model", error=e)
                raise
        return self._cross_encoder

    def get_cross_encoder(self) -> CrossEncoder:
        """Get the cross-encoder model instance.

        Returns:
            CrossEncoder: The cross-encoder model instance.
        """
        return self.cross_encoder

    def clear_cache(self):
        """Clear model cache if needed."""
        logger.info("Clearing model cache")
        if self._cross_encoder is not None:
            # Explicitly move model to CPU and clear CUDA cache if using GPU
            if self.device.type == "cuda":
                self._cross_encoder.to("cpu")
                torch.cuda.empty_cache()
                logger.info("CUDA cache cleared")

        self._cross_encoder = None
        # Clear the lru_cache for the property
        self.cross_encoder.fget.cache_clear()
        logger.info("Model cache cleared successfully")
