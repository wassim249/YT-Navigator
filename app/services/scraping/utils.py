"""Utility functions for YouTube scraping."""

import itertools
import re
from typing import (
    Any,
    List,
    Optional,
)

import scrapetube
import structlog

logger = structlog.get_logger(__name__)


def get_channel_username(channel_link: str) -> str:
    """Extract the username from a YouTube channel link.

    Args:
        channel_link: The full YouTube channel URL

    Returns:
        str: The extracted channel username
    """
    username = channel_link.split("https://www.youtube.com/@")[1].strip()
    logger.debug("Extracted channel username", username=username)
    return username


def validate_channel_link(channel_link: str) -> str:
    """Validate the YouTube channel link format and existence.

    Args:
        channel_link: The YouTube channel link to validate

    Returns:
        str: The validated channel username

    Raises:
        ValueError: If the channel link is invalid or the channel doesn't exist
    """
    if not channel_link:
        error_msg = "Channel link cannot be empty"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not re.match(r"https://www.youtube.com/@.*", channel_link.strip()):
        error_msg = "Invalid YouTube channel link format"
        logger.error(error_msg, channel_link=channel_link)
        raise ValueError(error_msg)

    channel_username = get_channel_username(channel_link)

    try:
        scrapetube.get_channel(channel_username)
        logger.info("Channel validated successfully", channel_username=channel_username)
        return channel_username
    except Exception as e:
        logger.error("Channel validation failed", channel_username=channel_username, error=e)
        raise ValueError(f"Invalid YouTube channel: {str(e)}") from e


def chunk_generator(items: List[Any], chunk_size: int):
    """Generate chunks of items with a specified size.

    Args:
        items: List of items to chunk
        chunk_size: Size of each chunk

    Yields:
        List[Any]: Chunks of items
    """
    iterator = iter(items)
    chunk_count = 0

    while chunk := list(itertools.islice(iterator, chunk_size)):
        chunk_count += 1
        logger.debug(f"Processing chunk {chunk_count}", chunk_size=len(chunk))
        yield chunk
