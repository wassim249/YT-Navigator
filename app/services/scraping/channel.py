"""Channel-related functionality for YouTube scraping."""

import asyncio
import traceback
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
            try:
                await self.client.aclose()
            except RuntimeError as e:
                # Handle event loop closed errors gracefully
                if "Event loop is closed" in str(e):
                    logger.warning("Event loop closed during client cleanup", error=str(e))
                else:
                    logger.error("Error closing HTTP client", error=str(e), traceback=traceback.format_exc())

    async def _ensure_client(self):
        """Ensure the HTTP client is initialized and using the current event loop.

        Returns:
            httpx.AsyncClient: The HTTP client
        """
        try:
            # Get the current event loop
            current_loop = asyncio.get_running_loop()

            # Create a new client if it doesn't exist
            if not self.client:
                logger.debug("Creating new HTTP client in event loop", loop_id=id(current_loop))
                self.client = httpx.AsyncClient(timeout=self.request_timeout)

            return self.client
        except RuntimeError as e:
            logger.error("Error ensuring HTTP client", error=str(e), traceback=traceback.format_exc())
            raise

    async def get_channel_data(self, channel_link: str, channel_username: Optional[str] = None) -> Optional[Channel]:
        """Fetch channel data from YouTube.

        Args:
            channel_link: The YouTube channel link
            channel_username: Optional channel username (extracted from link if not provided)

        Returns:
            Optional[Channel]: The channel object if successful, None otherwise
        """
        try:
            if channel_username is None:
                channel_username = get_channel_username(channel_link)

            logger.info("Fetching channel data", channel_link=channel_link, channel_username=channel_username)

            # Ensure client is initialized
            client = await self._ensure_client()

            # Fetch channel page
            try:
                response = await client.get(
                    f"https://www.youtube.com/@{channel_username}",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    },
                )
                response.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("HTTP error fetching channel data", error=str(e), channel_username=channel_username)
                return None
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    logger.error("Event loop closed during HTTP request", error=str(e))
                    # Recreate client and try again
                    self.client = None
                    client = await self._ensure_client()
                    response = await client.get(
                        f"https://www.youtube.com/@{channel_username}",
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                        },
                    )
                    response.raise_for_status()
                else:
                    raise

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract channel metadata
            channel_data = self._extract_channel_metadata(soup)
            if not channel_data:
                logger.warning("Failed to extract channel metadata", channel_username=channel_username)
                return None

            # Create or update channel in database
            try:
                channel, created = await sync_to_async(Channel.objects.get_or_create, thread_sensitive=True)(
                    id=channel_data["id"],
                    defaults={
                        "name": channel_data["name"],
                        "thumbnail": channel_data["thumbnail"],
                        "subscribers": channel_data["subscribers"],
                        "last_updated": timezone.now(),
                    },
                )

                # Update channel if it already exists
                if not created:
                    channel.name = channel_data["name"]
                    channel.thumbnail = channel_data["thumbnail"]
                    channel.subscribers = channel_data["subscribers"]
                    channel.last_updated = timezone.now()
                    await sync_to_async(channel.save, thread_sensitive=True)()

                logger.info(
                    "Channel data fetched successfully",
                    channel_id=channel.id,
                    channel_name=channel.name,
                    created=created,
                )
                return channel
            except Exception as e:
                logger.error("Database error saving channel", error=str(e), traceback=traceback.format_exc())
                return None

        except httpx.RequestError as e:
            logger.error("YouTube API request failed", channel_link=channel_link, error=str(e))
        except Exception as e:
            logger.error(
                "Unexpected error in get_channel_data",
                channel_link=channel_link,
                error=str(e),
                traceback=traceback.format_exc(),
            )
        return None

    def _extract_channel_metadata(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract channel metadata from BeautifulSoup object.

        Args:
            soup: BeautifulSoup object of the channel page

        Returns:
            Optional[Dict]: Dictionary with channel metadata if successful, None otherwise
        """
        try:
            metadata = {
                "name": "Unknown Channel",
                "description": "N/A",
                "url": "N/A",
                "profile_image_url": "N/A",
                "id": "N/A",
            }

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

            # Extract channel profile image URL
            metadata["profile_image_url"] = (
                soup.find("meta", property="og:image")["content"] if soup.find("meta", property="og:image") else "N/A"
            )

            # Extract channel ID
            if "youtube.com/channel/" in metadata["url"]:
                metadata["id"] = metadata["url"].split("https://www.youtube.com/channel/")[1]

            return metadata
        except Exception as e:
            logger.error("Failed to extract channel metadata", error=e)
            return None
