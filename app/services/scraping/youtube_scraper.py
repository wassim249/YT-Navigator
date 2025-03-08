"""YouTube scraping service for channel and video data extraction.

This module provides a comprehensive scraping service that combines channel, video,
and transcript scraping components to extract data from YouTube channels.
"""

import concurrent.futures
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)

import scrapetube
import structlog

from app.models import Channel
from app.services.scraping.base import BaseYoutubeScraper
from app.services.scraping.channel import ChannelScraper
from app.services.scraping.transcript import TranscriptScraper
from app.services.scraping.utils import (
    chunk_generator,
    validate_channel_link,
)
from app.services.scraping.video import VideoScraper

logger = structlog.get_logger(__name__)


class YoutubeScraper(BaseYoutubeScraper):
    """Main YouTube scraper service for comprehensive data extraction.

    This class orchestrates the scraping process by combining channel, video,
    and transcript scraping components. It handles parallel processing of videos
    and manages the extraction and storage of channel data.

    Attributes:
        channel_scraper: Component for scraping channel information.
        video_scraper: Component for scraping video information.
        transcript_scraper: Component for extracting video transcripts.
    """

    def __init__(self, workers_num: int = 4, max_transcript_segment_duration: int = 40, request_timeout: int = 10):
        """Initialize the YouTube scraper with configurable parameters.

        Args:
            workers_num: Number of concurrent workers for processing videos.
            max_transcript_segment_duration: Maximum duration in seconds for transcript segments.
            request_timeout: Timeout in seconds for HTTP requests.
        """
        super().__init__(workers_num, max_transcript_segment_duration, request_timeout)

        # Initialize component scrapers
        self.channel_scraper = ChannelScraper(request_timeout=request_timeout)
        self.video_scraper = VideoScraper(max_concurrent_tasks=workers_num)
        self.transcript_scraper = TranscriptScraper(max_transcript_segment_duration=max_transcript_segment_duration)

    @staticmethod
    def validate_channel_link(channel_link: str) -> str:
        """Validate and extract username from a YouTube channel link.

        Args:
            channel_link: The YouTube channel link to validate.

        Returns:
            str: The validated channel username.

        Raises:
            ValueError: If the channel link is invalid or the channel doesn't exist.
        """
        return validate_channel_link(channel_link)

    async def get_channel_data(self, channel_link: str, channel_username: Optional[str] = None) -> Optional[Channel]:
        """Fetch and store channel metadata from a YouTube channel.

        Args:
            channel_link: The YouTube channel link to scrape.
            channel_username: Optional channel username. If not provided,
                will be extracted from the channel link.

        Returns:
            Optional[Channel]: The created/updated Channel object if successful,
                None if the channel data couldn't be retrieved.
        """
        return await self.channel_scraper.get_channel_data(channel_link, channel_username)

    async def scrape(
        self, channel_username: str, channel_id: str, videos_limit: int = 10
    ) -> Tuple[List[Dict], List[Dict]]:
        """Scrape videos and transcripts from a YouTube channel.

        This method orchestrates the parallel processing of videos from a channel,
        including transcript extraction and segmentation.

        Args:
            channel_username: YouTube channel username to scrape.
            channel_id: Database ID of the channel to associate videos with.
            videos_limit: Maximum number of videos to scrape from the channel.

        Returns:
            Tuple[List[Dict], List[Dict]]: A tuple containing:
                - List of processed video dictionaries
                - List of transcript chunk dictionaries

        Note:
            Videos are processed in parallel using a thread pool executor,
            with the number of workers specified during initialization.
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
                "Channel scrape completed",
                channel_username=channel_username,
                videos_count=len(all_videos),
                chunks_count=len(all_chunks),
            )

            return all_videos, all_chunks

        except Exception as e:
            logger.error("Channel scrape failed", channel_username=channel_username, error=e)
            return [], []
