"""Transcript-related functionality for YouTube scraping."""

from typing import (
    Dict,
    List,
)

import structlog
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

from app.helpers import convert_seconds_to_timestamp

logger = structlog.get_logger(__name__)


class TranscriptScraper:
    """Transcript-related functionality for YouTube scraping."""

    def __init__(self, max_transcript_segment_duration: int = 40):
        """Initialize the transcript scraper.

        Args:
            max_transcript_segment_duration: Maximum duration for transcript segments in seconds
        """
        self.max_transcript_segment_duration = max_transcript_segment_duration

    def get_video_transcript(self, video_metadata: Dict) -> List[Dict]:
        """Fetches and formats the transcript of a YouTube video.

        Args:
            video_metadata: Dictionary containing video metadata

        Returns:
            List[Dict]: List of transcript segments
        """
        video_id = video_metadata["videoId"]

        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return self._format_transcript(transcript, video_metadata)

        except NoTranscriptFound:
            logger.warning(
                f"No transcript available for https://www.youtube.com/watch?v={video_metadata['videoId']}",
                video_id=video_id,
            )
            return []

        except TranscriptsDisabled:
            logger.warning(
                f"Transcripts are disabled for https://www.youtube.com/watch?v={video_metadata['videoId']}",
                video_id=video_id,
            )
            return []

        except Exception as e:
            logger.error(
                f"Failed to fetch transcript for https://www.youtube.com/watch?v={video_metadata['videoId']}",
                video_id=video_id,
                error=e,
            )
            return []

    def _format_transcript(self, transcript: List[Dict], video_metadata: Dict) -> List[Dict]:
        """Formats the video transcript into segments with a maximum duration.

        Args:
            transcript: Raw transcript data from YouTube API
            video_metadata: Dictionary containing video metadata

        Returns:
            List[Dict]: List of formatted transcript segments
        """
        formatted_transcript = []
        segment_text, start_time = "", 0
        current_duration = 0

        try:
            for i, item in enumerate(transcript):
                # If this is the first item or we're starting a new segment
                if i == 0 or current_duration >= self.max_transcript_segment_duration:
                    # Save the previous segment if it exists
                    if segment_text and i > 0:
                        formatted_transcript.append(
                            {
                                "video_id": video_metadata["videoId"],
                                "start_time": start_time,
                                "timestamp": convert_seconds_to_timestamp(start_time),
                                "text": segment_text.strip(),
                                "duration": current_duration,
                            }
                        )

                    # Start a new segment
                    segment_text = item["text"]
                    start_time = item["start"]
                    current_duration = item["duration"]
                else:
                    # Continue the current segment
                    segment_text += " " + item["text"]
                    current_duration += item["duration"]

            # Add the last segment
            if segment_text:
                formatted_transcript.append(
                    {
                        "video_id": video_metadata["videoId"],
                        "start_time": start_time,
                        "timestamp": convert_seconds_to_timestamp(start_time),
                        "text": segment_text.strip(),
                        "duration": current_duration,
                    }
                )

            return formatted_transcript

        except Exception as e:
            logger.error("Error formatting transcript", video_id=video_metadata["videoId"], error=e)
            return []
