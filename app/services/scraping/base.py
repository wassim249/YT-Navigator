"""
Base class for YouTube scraping functionality.
"""

import structlog

logger = structlog.get_logger(__name__)


class BaseYoutubeScraper:
    """
    Base class for YouTube scraping functionality.

    This class provides the foundation for YouTube scraping operations
    with configurable parameters.

    Attributes:
        workers_num (int): Number of concurrent workers for processing videos
        max_transcript_segment_duration (int): Maximum duration for transcript segments
        request_timeout (int): Timeout for HTTP requests in seconds
    """

    def __init__(self, workers_num: int = 4, max_transcript_segment_duration: int = 40, request_timeout: int = 10):
        """
        Initialize the YouTube scraper with configurable parameters.

        Args:
            workers_num: Number of concurrent workers for processing videos
            max_transcript_segment_duration: Maximum duration for transcript segments
            request_timeout: Timeout for HTTP requests in seconds
        """
        self.workers_num = workers_num
        self.max_transcript_segment_duration = max_transcript_segment_duration
        self.request_timeout = request_timeout
        logger.info(
            "Initialized BaseYoutubeScraper",
            workers_num=workers_num,
            max_transcript_segment_duration=max_transcript_segment_duration,
            request_timeout=request_timeout,
        )
