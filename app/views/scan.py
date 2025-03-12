"""Views for the scan feature."""

import asyncio
import traceback
from functools import lru_cache

from asgiref.sync import sync_to_async
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods
from structlog import get_logger

from app.services.scraping import YoutubeScraper
from app.services.vector_database import VectorDatabaseService

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_youtube_scraper():
    """Get the YouTube scraper.

    Returns:
        YoutubeScraper: A singleton instance of the YouTube scraper.
    """
    try:
        # Create a new scraper with default settings
        return YoutubeScraper()
    except Exception as e:
        logger.error("Error creating YouTube scraper", error=str(e), traceback=traceback.format_exc())
        # Return a default scraper as fallback
        return YoutubeScraper()


@lru_cache(maxsize=1)
def get_vector_database():
    """Get the vector database."""
    return VectorDatabaseService()


@login_required
@require_http_methods(["POST"])
async def get_channel_information(request):
    """Get and store channel information from YouTube.

    Args:
        request: The HTTP request object containing the channel link.

    Returns:
        HttpResponseRedirect: Redirects to home page after processing.

    Raises:
        ValueError: If the channel link is invalid.
        Exception: For any unexpected errors during processing.
    """
    try:
        from django.contrib import messages
        from django.shortcuts import redirect

        channel_link = request.POST.get("channel_link")

        if not channel_link:
            logger.error("Missing channel link")
            messages.error(request, "Please enter a valid YouTube channel link.")
            return redirect("app:home")

        try:
            # Get the current event loop
            current_loop = asyncio.get_running_loop()
            logger.debug("Processing channel information in event loop", loop_id=id(current_loop))

            # Get a YouTube scraper instance
            scraper = get_youtube_scraper()

            # Validate the channel link
            try:
                channel_username = await sync_to_async(scraper.validate_channel_link, thread_sensitive=True)(
                    channel_link,
                )
            except ValueError as e:
                logger.warning("Invalid channel link", error=str(e), channel_link=channel_link)
                messages.error(request, str(e))
                return redirect("app:home")

            # Get channel data
            channel = await scraper.get_channel_data(
                channel_link,
                channel_username,
            )

            if channel:
                # Update user's channel
                try:
                    await sync_to_async(lambda: setattr(request.user, "channel", channel), thread_sensitive=True)()
                    await sync_to_async(request.user.save, thread_sensitive=True)()

                    logger.info("Channel information fetched successfully", channel_id=channel.id)
                    messages.success(request, f"Successfully connected to channel: {channel.name}")
                except Exception as e:
                    logger.error("Error updating user channel", error=str(e), traceback=traceback.format_exc())
                    messages.error(request, "Error connecting to channel. Please try again.")
            else:
                logger.error("Failed to fetch channel information", channel_link=channel_link)
                messages.error(request, "Could not fetch channel information. Please try again.")
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                logger.error("Event loop closed during channel processing", error=str(e))
                messages.error(request, "An error occurred. Please try again.")
            else:
                logger.error("Runtime error processing channel", error=str(e), traceback=traceback.format_exc())
                messages.error(request, "An unexpected error occurred. Please try again.")
    except Exception as e:
        logger.error("Unexpected error in get_channel_information", error=str(e), traceback=traceback.format_exc())
        messages.error(request, "An unexpected error occurred. Please try again.")

    return redirect("app:home")


@login_required
@require_http_methods(["POST"])
async def scan_channel(request):
    """Scan channel videos and store them in the database.

    Args:
        request: The HTTP request object containing optional videos_limit parameter.

    Returns:
        HttpResponseRedirect: A redirect to the home page with a success or error message.

    Raises:
        Exception: For any errors during the scanning process.
    """
    try:
        from django.contrib import messages
        from django.shortcuts import redirect

        channel = await sync_to_async(lambda: request.user.channel)()

        videos_limit = request.POST.get("videos_limit", 10)
        videos_limit = int(videos_limit)

        if not channel:
            logger.warning("No channel found for user", user_id=request.user.id)
            messages.error(request, "No channel found")
            return redirect("app:home")

        logger.info(
            "Starting channel scan",
            channel_id=channel.id,
            channel_username=channel.username,
            videos_limit=videos_limit,
        )

        # Pass the parent span to maintain the trace
        videos, chunks = await get_youtube_scraper().scrape(
            videos_limit=videos_limit,
            channel_username=channel.username,
            channel_id=channel.id,
        )

        logger.info("Scraped videos", scraped_videos=len(videos))
        logger.info("Scraped chunks", scraped_chunks=len(chunks))

        # Pass the parent span to vector database operations
        await get_vector_database().add_chunks(
            chunks,
            channel_id=channel.id,
        )

        logger.info(
            "Channel scan completed successfully",
            channel_id=channel.id,
            channel_username=channel.username,
            videos_count=len(videos),
            chunks_count=len(chunks),
        )

        messages.success(request, f"Successfully scanned {len(videos)} videos and extracted {len(chunks)} chunks.")
        return redirect("app:home")

    except Exception as e:
        logger.error(
            "Error during channel scan",
            channel_id=channel.id if "channel" in locals() and channel else None,
            error=e,
            traceback=traceback.format_exc(),
        )
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("app:home")


@login_required
@require_http_methods(["GET"])
async def delete_video(request, video_id: str):
    """Delete a video and its associated data.

    Args:
        request: The HTTP request object.
        video_id: The ID of the video to delete.

    Returns:
        HttpResponseRedirect: A redirect to the videos page on success or error.

    Raises:
        Exception: For any errors during the deletion process.
    """
    try:
        if not video_id:
            logger.error("No video ID provided")
            messages.error(request, "No video ID provided.")
            return redirect("app:home")

        # Pass the parent span to maintain the trace
        deleted = await get_vector_database().delete_video(
            video_id,
        )

        if deleted:
            logger.info("Video deleted successfully", video_id=video_id)
            messages.success(request, "Video deleted successfully.")
            return redirect("app:home")
        else:
            logger.error("Failed to delete video", video_id=video_id)
            messages.error(request, "Failed to delete video.")
            return redirect("app:home")

    except Exception as e:
        logger.error("Error deleting video", video_id=video_id, error=e, traceback=traceback.format_exc())
        messages.error(request, f"Error: {str(e)}")
        return redirect("app:home")
