"""User model."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A custom user model extending Django's AbstractUser.

    Attributes:
        channel (ForeignKey): Optional reference to a YouTube channel associated with the user.
    """

    channel = models.ForeignKey("Channel", on_delete=models.CASCADE, null=True)

    def __str__(self):
        """Returns a string representation of the user.

        Returns:
            str: A formatted string with the user's username and email.
        """
        return f"""username: {self.username} , email: {self.email}"""

    def dict(self):
        """Converts the user model instance to a dictionary.

        Returns:
            dict: A dictionary containing the user's username and email.
        """
        return {"username": self.username, "email": self.email}
