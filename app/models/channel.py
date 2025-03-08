"""Channel model for YouTube channels."""

from django.db import models


class Channel(models.Model):
    """A model representing a YouTube channel.

    This model stores information about YouTube channels including their
    unique identifier, name, profile image, description, and username.

    Attributes:
        id: A string representing the unique YouTube channel ID.
        name: A string representing the channel's display name.
        profile_image_url: A URL to the channel's profile image.
        description: A text field containing the channel's description.
        username: A string representing the channel's username.
    """

    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    profile_image_url = models.URLField()
    description = models.TextField()
    username = models.CharField(max_length=100)
    url = models.URLField(default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Returns a string representation of the channel.

        Returns:
            A formatted string with the channel's ID, name, username, and description.
        """
        return """
        ID: {id}
        Name: {name}
        Username: {username}
        Description: {description}
        """.format(
            name=self.name, username=self.username, description=self.description, id=self.id
        )

    class Meta:
        """Metadata options for the Channel model."""

        verbose_name_plural = "Channels"

    def dict(self):
        """Converts the channel model instance to a dictionary.

        Returns:
            A dictionary containing the channel's attributes.
        """
        return {
            "id": self.id,
            "name": self.name,
            "profile_image_url": self.profile_image_url,
            "description": self.description,
            "username": self.username,
        }
