"""
URL configuration for yt_navigator project.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("app.urls")),
]

# Configure error handlers
handler404 = "yt_navigator.views.page_not_found"
handler500 = "yt_navigator.views.server_error"
