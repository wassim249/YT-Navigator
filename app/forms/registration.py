"""Forms for the registration process."""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from app.models import User


class RegistrationForm(UserCreationForm):
    """Form for user registration.

    This form extends Django's UserCreationForm to include additional fields
    for username, email, and password confirmation.

    Attributes:
        username: The username of the user.
        email: The email of the user.
        password1: The password of the user.
        password2: The password confirmation of the user.
    """

    class Meta:
        """Meta class for the RegistrationForm."""

        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        """Initialize the RegistrationForm.

        This method adds classes to the form fields to style them.
        """
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
