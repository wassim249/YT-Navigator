"""Views for the app."""

from .authentication import register_view
from .chatbot import (
    chatbot_page,
    send_message,
)
from .home import home_view
from .profile import profile_view
from .query import (
    query,
    query_page,
)
from .scan import (
    delete_video,
    get_channel_information,
    scan_channel,
)

__all__ = [
    "home_view",
    "register_view",
    "profile_view",
    "get_channel_information",
    "scan_channel",
    "delete_video",
    "query_page",
    "query",
    "send_message",
    "chatbot_page",
]
