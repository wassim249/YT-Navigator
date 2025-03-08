"""Views for the home page."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from app.models import Video


@require_GET
@login_required
def home_view(request):
    """Home view."""
    channel = request.user.channel
    videos = Video.objects.filter(channel=channel)
    # sort videos by published date in descending order
    videos = videos.order_by("-published_at")
    return render(request, "home.html", {"videos": videos, "channel": channel})
