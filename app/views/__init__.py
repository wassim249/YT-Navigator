"""Views for the app."""

from .authentication import register_view
from .home import home_view
from .profile import profile_view
from .scan import get_channel_information

__all__ = ["home_view", "register_view", "profile_view", "get_channel_information"]
