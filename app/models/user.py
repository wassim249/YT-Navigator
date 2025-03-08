from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    channel = models.ForeignKey("Channel", on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"""username: {self.username} , email: {self.email}"""

    def dict(self):
        return {"username": self.username, "email": self.email}
