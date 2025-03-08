"""Models for the app."""

from django.db import models


class VideoChunk(models.Model):
    """Video chunk model.

    A chunk represents a segment of a video with start and end times and the transcribed text.

    Attributes:
        video (ForeignKey): Reference to the Video model this chunk belongs to.
        start (TimeField): Start time of the video chunk.
        end (TimeField): End time of the video chunk.
        text (TextField): Transcribed text content of the video chunk.
    """

    video = models.ForeignKey("Video", on_delete=models.CASCADE, related_name="chunks")
    start = models.TimeField()
    end = models.TimeField()
    text = models.TextField()

    def dict(self):
        """Convert the model instance to a dictionary.

        Returns:
            dict: Dictionary representation of the video chunk with id, video_id, start, end, and text.
        """
        return {"id": self.id, "video_id": self.video.id, "start": self.start, "end": self.end, "text": self.text}

    def __str__(self):
        """Return a string representation of the video chunk.

        Returns:
            str: String representation showing text and time range.
        """
        return f"KeyWord search - {self.text} ({self.start} - {self.end})"

    class Meta:
        """Meta class for the video chunk model."""

        db_table = "app_videochunk"
