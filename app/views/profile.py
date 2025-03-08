"""Views for the profile app."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    redirect,
    render,
)


@login_required
def profile_view(request):
    """Profile view."""
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")

        # Update user profile
        request.user.username = username
        request.user.email = email
        request.user.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("profile")

    return render(request, "profile.html")
