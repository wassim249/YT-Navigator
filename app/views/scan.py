"""Views for the scan feature."""

from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from structlog import get_logger

from app.services.scraping import YoutubeScraper

youtube_scraper = YoutubeScraper()

logger = get_logger(__name__)


@login_required
@require_http_methods(["POST"])
async def get_channel_information(request):
    """Get and store channel information from YouTube."""
    try:
        channel_link = request.POST.get("channel_link")

        if not channel_link:
            logger.error("Missing channel link")
            return JsonResponse({"error": "Please enter a valid YouTube channel link."}, status=400)

        try:
            channel_username = await sync_to_async(youtube_scraper.validate_channel_link)(
                channel_link,
            )
        except ValueError as e:
            logger.warning("Invalid channel link", error=str(e), channel_link=channel_link)
            return JsonResponse({"error": str(e)}, status=400)

        channel = await youtube_scraper.get_channel_data(
            channel_link,
            channel_username,
        )

        if channel:
            # Update user's channel
            request.user.channel = channel
            await sync_to_async(request.user.save)()

            logger.info("Channel information fetched successfully", channel_id=channel.id)

            return JsonResponse(
                {
                    "status": "success",
                    "channel": {"id": channel.id, "name": channel.name, "username": channel.username},
                }
            )
        else:
            logger.error("Failed to fetch channel information", channel_link=channel_link)
            return JsonResponse({"error": "Failed to fetch channel information."}, status=500)

    except Exception as e:
        logger.error("Unexpected error in get_channel_information", error=str(e))
        return JsonResponse({"error": str(e)}, status=500)
