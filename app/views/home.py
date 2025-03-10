"""Views for the home page."""

import structlog
from django.contrib.auth.decorators import login_required
from django.core.paginator import (
    EmptyPage,
    PageNotAnInteger,
    Paginator,
)
from django.shortcuts import render
from django.views.decorators.http import require_GET

from app.models import Video

logger = structlog.get_logger(__name__)


@require_GET
@login_required
def home_view(request):
    """Home view displaying user's channel and paginated videos.

    Args:
        request: The HTTP request object.

    Returns:
        Rendered home page with paginated videos and channel information.
    """
    channel = request.user.channel
    videos_list = Video.objects.filter(channel=channel)
    total_videos = videos_list.count()
    # sort videos by published date in descending order
    videos_list = videos_list.order_by("-published_at")

    # Set up pagination
    paginator = Paginator(videos_list, 12)  # Show 12 videos per page
    page = request.GET.get("page")

    try:
        videos = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        videos = paginator.page(1)
        logger.info("Non-integer page requested, showing first page", page_number=page)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        videos = paginator.page(paginator.num_pages)
        logger.info("Page out of range, showing last page", requested_page=page, max_pages=paginator.num_pages)

    return render(
        request,
        "home.html",
        {
            "videos": videos,
            "channel": channel,
            "page_obj": videos,
            "total_videos": total_videos,
        },
    )
