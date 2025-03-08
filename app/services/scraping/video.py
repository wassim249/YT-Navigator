"""Video-related functionality for YouTube scraping."""

import asyncio
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)

import structlog
from asgiref.sync import sync_to_async
from django.db import IntegrityError
from django.utils import timezone

from app.helpers import get_exact_time
from app.models import Video

logger = structlog.get_logger(__name__)


class VideoScraper:
    """Video-related functionality for YouTube scraping."""

    def __init__(self, max_concurrent_tasks: int = 4):
        """Initialize the video scraper.

        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks for processing videos
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)

    async def __aenter__(self):
        """Initialize async resources."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup async resources."""
        pass

    def get_formatted_video_metadata(self, video: Dict) -> Optional[Dict]:
        """Format raw video metadata into a standardized structure.

        Args:
            video: Raw video metadata from YouTube

        Returns:
            Optional[Dict]: Formatted video metadata if successful, None otherwise
        """
        try:
            video_id = video.get("videoId")
            if not video_id:
                logger.warning("Missing video ID in metadata")
                return None

            published_timestamp = video.get("publishedTimeText", {}).get("simpleText", "")
            published_at = get_exact_time(published_timestamp) if published_timestamp else timezone.now()

            metadata = {
                "videoId": video_id,
                "title": video.get("title", {}).get("runs", [{}])[0].get("text", "Untitled Video"),
                "description": video.get("descriptionSnippet", {}).get("runs", [{}])[0].get("text", "No description"),
                "thumbnail": video.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url", ""),
                "published_at": published_at,
                "view_count": video.get("viewCountText", {})
                .get("simpleText", "0 views")
                .split(" ")[0]
                .replace(",", ""),
                "duration": video.get("lengthText", {}).get("simpleText", "0:00"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }

            return metadata

        except Exception as e:
            logger.error("Failed to format video metadata", video_id=video.get("videoId", "unknown"), error=e)
            return None

    async def process_single_video(self, video: Dict, transcript_scraper) -> Tuple[Optional[Dict], List[Dict]]:
        """Process a single video to extract metadata and transcript.

        Args:
            video: Raw video data
            transcript_scraper: TranscriptScraper instance for transcript processing

        Returns:
            Tuple[Optional[Dict], List[Dict]]: Tuple of (video metadata, transcript chunks)
        """
        try:
            async with self.semaphore:  # Control concurrency
                video_metadata = self.get_formatted_video_metadata(video)
                if not video_metadata:
                    return None, []

                # Assuming transcript_scraper.get_video_transcript is async
                video_chunks = await transcript_scraper.get_video_transcript(video_metadata)

                logger.debug(
                    f"Processed video successfully https://www.youtube.com/watch?v={video_metadata['videoId']}",
                    video_id=video_metadata["videoId"],
                    chunks_count=len(video_chunks),
                )

                return video_metadata, video_chunks

        except Exception as e:
            logger.error("Failed to process video", video_id=video.get("videoId", "unknown"), error=e)
            return None, []

    async def process_video_chunk(self, chunk: List[Dict], transcript_scraper) -> Tuple[List[Dict], List[Dict]]:
        """Process a chunk of videos to extract transcripts concurrently.

        Args:
            chunk: List of raw video data
            transcript_scraper: TranscriptScraper instance for transcript processing

        Returns:
            Tuple[List[Dict], List[Dict]]: Tuple of (processed videos, transcript chunks)
        """
        tasks = [self.process_single_video(video, transcript_scraper) for video in chunk]
        results = await asyncio.gather(*tasks)

        videos = []
        chunks = []

        for video_metadata, video_chunks in results:
            if video_metadata:
                videos.append(video_metadata)
                chunks.extend(video_chunks)

        logger.info("Chunk processing completed", processed_videos=len(videos), total_chunks=len(chunks))
        return videos, chunks

    async def save_videos_to_db(self, videos: List[Dict], channel_id: str) -> None:
        """Save scraped videos to the database.

        Args:
            videos: List of video metadata
            channel_id: Channel ID to associate videos with
        """
        try:
            tasks = []
            for video in videos:
                task = self._save_single_video(video, channel_id)
                tasks.append(task)

            await asyncio.gather(*tasks)
            logger.info("Videos saved to database", channel_id=channel_id, videos_count=len(videos))

        except Exception as e:
            logger.error("Failed to save videos batch", channel_id=channel_id, error=e)

    async def _save_single_video(self, video: Dict, channel_id: str) -> None:
        """Save a single video to the database.

        Args:
            video: Video metadata
            channel_id: Channel ID to associate video with
        """
        try:
            await sync_to_async(Video.objects.update_or_create)(
                video_id=video["videoId"],
                defaults={
                    "title": video["title"],
                    "description": video["description"],
                    "thumbnail": video["thumbnail"],
                    "published_at": video["published_at"],
                    "view_count": video["view_count"],
                    "duration": video["duration"],
                    "url": video["url"],
                    "channel_id": channel_id,
                },
            )
        except IntegrityError:
            # Skip if video already exists
            pass
        except Exception as e:
            logger.error("Failed to save video", video_id=video["videoId"], error=e)
