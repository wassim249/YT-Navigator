"""
Forms for the registration process.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from app.models import User


class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]  # Corrected to include password1 and password2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add classes to form fields
        self.fields["username"].widget.attrs.update(
            {
                "class": "w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 focus:outline-none"
            }
        )
        self.fields["email"].widget.attrs.update(
            {
                "class": "w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 focus:outline-none"
            }
        )
        self.fields["password1"].widget.attrs.update(
            {
                "class": "w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 focus:outline-none"
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "class": "w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 focus:outline-none"
            }
        )
