"""URLs for the app."""

from django.contrib.auth.views import (
    LoginView,
    LogoutView,
)
from django.urls import path

from .views import (
    chatbot_page,
    clear_chat_history,
    delete_video,
    get_channel_information,
    home_view,
    profile_view,
    query,
    query_page,
    register_view,
    scan_channel,
    send_message,
)

app_name = "app"

urlpatterns = [
    # authentication
    path("register/", register_view, name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # home page
    path("", home_view, name="home"),
    # profile page
    path("profile/", profile_view, name="profile"),
    # scan page
    path("get-channel-information/", get_channel_information, name="get_channel_information"),
    path("scan-channel/", scan_channel, name="scan_channel"),
    path("delete-video/<str:video_id>/", delete_video, name="delete_video"),
    # query page
    path("query/", query_page, name="query_page"),
    path("query-request/", query, name="query_request"),
    # chatbot
    path("chatbot/", chatbot_page, name="chatbot_page"),
    path("send-message/", send_message, name="send_message"),
    path("clear-chat-history/", clear_chat_history, name="clear_chat_history"),
]
