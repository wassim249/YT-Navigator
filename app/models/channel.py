from django.db import models


class Channel(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    profile_image_url = models.URLField()
    description = models.TextField()
    username = models.CharField(max_length=100)

    def __str__(self):
        return """
        ID: {id}
        Name: {name}
        Username: {username}
        Description: {description}
        """.format(
            name=self.name, username=self.username, description=self.description, id=self.id
        )

    class Meta:
        verbose_name_plural = "Channels"

    def dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "profile_image_url": self.profile_image_url,
            "description": self.description,
            "username": self.username,
        }
