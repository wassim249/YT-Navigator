from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from app.forms import RegistrationForm


def register_view(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        print(request.POST)  # Debugging form values

        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful! You can now log in.")
            # login user
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password1")
            user = authenticate(request, username=username, password=password)
            login(request, user)
            return redirect("app:home")
        else:
            for field in form:
                for error in field.errors:
                    print(f"Error in {field.name}: {error}")  # Check errors in each field
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
    else:
        form = RegistrationForm()

    return render(request, "registration/register.html", {"form": form})
