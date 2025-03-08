"""Video model."""

from django.db import models


class Video(models.Model):
    """A model representing a video from a YouTube channel.

    Attributes:
        id (str): The unique identifier of the video.
        title (str): The title of the video.
        thumbnail (str): The URL of the video's thumbnail image.
        published_at (datetime): The timestamp when the video was published.
        channel (Channel): The YouTube channel that uploaded the video.
    """

    id = models.CharField(max_length=100, primary_key=True)
    title = models.CharField(max_length=100)
    thumbnail = models.URLField(default="https://i.ytimg.com/vi/default/default.jpg")
    published_at = models.DateTimeField()
    channel = models.ForeignKey("Channel", on_delete=models.CASCADE)

    def __str__(self):
        """Returns a string representation of the video.

        Returns:
            str: A formatted string with the video's title and channel.
        """
        return """
        Title: {title}
        Channel: {channel}
        """.format(
            title=self.title, channel=self.channel
        )

    def to_dict(self):
        """Converts the video model instance to a dictionary.

        Returns:
            dict: A dictionary representation of the video with its attributes.
        """
        return {
            "id": self.id,
            "title": self.title,
            "thumbnail": self.thumbnail,
            "published_at": self.published_at,
            "channel": self.channel.id,
        }

    class Meta:
        """Meta class for the video model."""

        verbose_name_plural = "Videos"
        db_table = "app_video"
