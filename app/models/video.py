from django.db import models


class Video(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    title = models.CharField(max_length=100)
    thumbnail = models.URLField()
    published_at = models.DateTimeField()
    channel = models.ForeignKey("Channel", on_delete=models.CASCADE)

    def __str__(self):
        return """
        Title: {title}
        Channel: {channel}
        """.format(
            title=self.title, channel=self.channel
        )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "thumbnail": self.thumbnail,
            "published_at": self.published_at,
            "channel": self.channel.id,
        }

    class Meta:
        verbose_name_plural = "Videos"
        db_table = "app_video"
