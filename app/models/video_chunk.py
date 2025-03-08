from django.db import models


class VideoChunk(models.Model):
    video = models.ForeignKey("Video", on_delete=models.CASCADE, related_name="chunks")
    start = models.TimeField()
    end = models.TimeField()
    text = models.TextField()

    def dict(self):
        return {"id": self.id, "video_id": self.video.id, "start": self.start, "end": self.end, "text": self.text}

    def __str__(self):
        return f"KeyWord search - {self.text} ({self.start} - {self.end})"

    class Meta:
        db_table = "app_videochunk"
