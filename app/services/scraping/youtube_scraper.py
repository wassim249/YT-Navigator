"""
Main YouTube scraper class that combines all scraping components.
"""

import concurrent.futures
from typing import Dict, List, Optional, Tuple

import scrapetube
import structlog

from app.models import Channel
from app.services.scraping.base import BaseYoutubeScraper
from app.services.scraping.channel import ChannelScraper
from app.services.scraping.transcript import TranscriptScraper
from app.services.scraping.utils import chunk_generator, validate_channel_link
from app.services.scraping.video import VideoScraper

logger = structlog.get_logger(__name__)


class YoutubeScraper(BaseYoutubeScraper):
    """
    Main YouTube scraper class that combines all scraping components.

    This class provides a comprehensive interface for scraping YouTube channels
    and videos, including transcript extraction and processing.
    """

    def __init__(self, workers_num: int = 4, max_transcript_segment_duration: int = 40, request_timeout: int = 10):
        """
        Initialize the YouTube scraper with configurable parameters.

        Args:
            workers_num: Number of concurrent workers for processing videos
            max_transcript_segment_duration: Maximum duration for transcript segments
            request_timeout: Timeout for HTTP requests in seconds
        """
        super().__init__(workers_num, max_transcript_segment_duration, request_timeout)

        # Initialize component scrapers
        self.channel_scraper = ChannelScraper(request_timeout=request_timeout)
        self.video_scraper = VideoScraper(workers_num=workers_num)
        self.transcript_scraper = TranscriptScraper(max_transcript_segment_duration=max_transcript_segment_duration)

    @staticmethod
    def validate_channel_link(channel_link: str) -> str:
        """
        Validate the YouTube channel link format and existence.

        Args:
            channel_link: The YouTube channel link to validate

        Returns:
            str: The validated channel username

        Raises:
            ValueError: If the channel link is invalid or the channel doesn't exist
        """
        return validate_channel_link(channel_link)

    async def get_channel_data(self, channel_link: str, channel_username: Optional[str] = None) -> Optional[Channel]:
        """
        Fetch and store channel data from a YouTube channel link.

        Args:
            channel_link: The YouTube channel link
            channel_username: Optional channel username (will be extracted from link if not provided)

        Returns:
            Optional[Channel]: The channel object if successful, None otherwise
        """
        return await self.channel_scraper.get_channel_data(channel_link, channel_username)

    async def scrape(
        self, channel_username: str, channel_id: str, videos_limit: int = 10
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Scrapes YouTube channel videos and processes them in parallel.

        Args:
            channel_username: YouTube channel username
            channel_id: Channel ID to associate videos with
            videos_limit: Maximum number of videos to scrape

        Returns:
            Tuple[List[Dict], List[Dict]]: Tuple of (processed videos, transcript chunks)
        """
        try:
            logger.info("Starting channel scrape", channel_username=channel_username, videos_limit=videos_limit)

            # Get videos from channel
            scrape_results = list(scrapetube.get_channel(channel_username=channel_username, limit=videos_limit))

            if not scrape_results:
                logger.warning("No videos found in channel", channel_username=channel_username)
                return [], []

            # Process videos in parallel
            all_videos = []
            all_chunks = []
            chunk_size = max(1, len(scrape_results) // self.workers_num)

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers_num) as executor:
                futures = [
                    executor.submit(self.video_scraper.process_video_chunk, chunk, self.transcript_scraper)
                    for chunk in chunk_generator(scrape_results, chunk_size)
                ]

                for future in concurrent.futures.as_completed(futures):
                    try:
                        videos, chunks = future.result()
                        all_videos.extend(videos)
                        all_chunks.extend(chunks)
                    except Exception as e:
                        logger.error("Error processing video chunk", channel_username=channel_username, error=e)

            # Save videos to database
            await self.video_scraper.save_videos_to_db(all_videos, channel_id)

            logger.info(
                f"Channel scrape completed for {channel_username}",
                channel_username=channel_username,
                videos_count=len(all_videos),
                chunks_count=len(all_chunks),
            )

            return all_videos, all_chunks

        except Exception as e:
            logger.error("Channel scrape failed", channel_username=channel_username, error=e)
            return [], []
