"""Chatbot views."""

import traceback

import structlog
from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from app.services.agent.main_graph import get_graph_instance

logger = structlog.get_logger(__name__)


@login_required
@require_http_methods(["GET"])
async def chatbot_page(request):
    """Render the chatbot page with chat history."""
    channel = await sync_to_async(lambda: request.user.channel)()
    user_id = await sync_to_async(lambda: str(request.user.id))()

    graph = await get_graph_instance()
    chat_history = await graph.get_chat_history(user_id)

    try:

        return render(
            request,
            "chatbot.html",
            {
                "channel": channel,
                "chat_history": chat_history,
            },
        )
    except Exception as e:
        logger.error("Failed to load chatbot page", error=str(e), traceback=traceback.format_exc())
        return render(request, "chatbot.html")


@login_required
@require_http_methods(["POST"])
async def send_message(request):
    """Process a message from the user and return a response."""
    user = await sync_to_async(lambda: request.user)()
    user_id = await sync_to_async(lambda: str(user.id))()
    message = request.POST.get("message", "").strip()

    if not message:
        logger.warning("Empty message received", user_id=user_id, message=message)
        return JsonResponse(
            {"error": True, "response": "Please enter a message before sending."},
            status=400,
        )

    try:
        # Get user channel using sync_to_async to avoid async database access
        user_channel = await sync_to_async(lambda: user.channel)()

        # Get graph instance for the current event loop
        graph = await get_graph_instance()

        response = await graph.process_message(
            message=message,
            channel=user_channel,
            user=user,
        )

        return JsonResponse(response, safe=False)

    except Exception as e:
        error_message = str(e)
        status_code = 500

        if "Rate limit reached" in error_message:
            import re

            wait_time_match = re.search(r"try again in (\d+m\d+\.\d+s)", error_message)
            wait_time = wait_time_match.group(1) if wait_time_match else "a few minutes"
            error_message = f"Rate limit reached. Please wait {wait_time} before trying again."
            status_code = 429
        else:
            error_message = f"An error occurred: {error_message}"

        logger.error("Message processing failed", error=error_message, traceback=traceback.format_exc())
        return JsonResponse(
            {"error": True, "response": error_message},
            status=status_code,
        )
