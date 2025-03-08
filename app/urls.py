from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .views import home_view, register_view

app_name = "app"

urlpatterns = [
    # authentication
    path("register/", register_view, name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # home page
    path("", home_view, name="home"),
]
