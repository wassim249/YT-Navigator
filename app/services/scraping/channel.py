"""Channel-related functionality for YouTube scraping."""

from typing import (
    Dict,
    Optional,
)

import httpx
import structlog
from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup
from django.utils import timezone

from app.models import Channel
from app.services.scraping.utils import get_channel_username

logger = structlog.get_logger(__name__)


class ChannelScraper:
    """Channel-related functionality for YouTube scraping."""

    def __init__(self, request_timeout: int = 10):
        """Initialize the channel scraper.

        Args:
            request_timeout: Timeout for HTTP requests in seconds
        """
        self.request_timeout = request_timeout
        self.client = None

    async def __aenter__(self):
        """Initialize async client for context manager usage."""
        self.client = httpx.AsyncClient(timeout=self.request_timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup async client."""
        if self.client:
            await self.client.aclose()

    async def get_channel_data(self, channel_link: str, channel_username: Optional[str] = None) -> Optional[Channel]:
        """Fetch and store channel data from a YouTube channel link.

        Args:
            channel_link: The YouTube channel link
            channel_username: Optional channel username (will be extracted from link if not provided)

        Returns:
            Optional[Channel]: The channel object if successful, None otherwise
        """
        try:
            if channel_username is None:
                channel_username = get_channel_username(channel_link)

            logger.info("Fetching channel data", channel_link=channel_link, channel_username=channel_username)

            # Create client if not in context manager
            if not self.client:
                self.client = httpx.AsyncClient(timeout=self.request_timeout)

            # Fetch channel page
            response = await self.client.get(
                f"https://www.youtube.com/@{channel_username}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
            )
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract channel metadata
            channel_data = self._extract_channel_metadata(soup)
            if not channel_data:
                return None

            # Create or update channel in database
            channel, created = await sync_to_async(Channel.objects.get_or_create)(
                channel_id=channel_data["id"],
                defaults={
                    "name": channel_data["name"],
                    "description": channel_data["description"],
                    "url": channel_data["url"],
                    "thumbnail": channel_data["thumbnail"],
                    "last_scraped": timezone.now(),
                },
            )

            if not created:
                channel.name = channel_data["name"]
                channel.description = channel_data["description"]
                channel.url = channel_data["url"]
                channel.thumbnail = channel_data["thumbnail"]
                channel.last_scraped = timezone.now()
                await sync_to_async(channel.save)()

            logger.info("Channel data processed", channel_id=channel_data["id"], channel_name=channel.name)
            return channel

        except httpx.RequestError as e:
            logger.error("YouTube API request failed", channel_link=channel_link, error=e)
        except Exception as e:
            logger.error("Unexpected error in get_channel_data", channel_link=channel_link, error=e)
        finally:
            # Close client if not in context manager
            if self.client and not hasattr(self, "__aenter__"):
                await self.client.aclose()
        return None

    def _extract_channel_metadata(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract channel metadata from BeautifulSoup object.

        Args:
            soup: BeautifulSoup object of the channel page

        Returns:
            Optional[Dict]: Dictionary with channel metadata if successful, None otherwise
        """
        try:
            metadata = {"name": "Unknown Channel", "description": "N/A", "url": "N/A", "thumbnail": "N/A", "id": "N/A"}

            # Extract channel name
            channel_name = soup.find("meta", property="og:title")
            if channel_name:
                metadata["name"] = channel_name["content"]

            # Extract channel description
            channel_desc = soup.find("meta", property="og:description")
            if channel_desc:
                metadata["description"] = channel_desc["content"]

            # Extract channel URL and ID
            channel_url = soup.find("meta", property="og:url")
            if channel_url:
                metadata["url"] = channel_url["content"]

            if "youtube.com/channel/" in metadata["url"]:
                metadata["id"] = metadata["url"].split("https://www.youtube.com/channel/")[1]

            return metadata
        except Exception as e:
            logger.error("Failed to extract channel metadata", error=e)
            return None
