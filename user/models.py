from django.db import models

# Create your models here.


class Token(models.Model):
    username = models.CharField(max_length=150)
    token = models.CharField(max_length=150)

    def __str__(self):
        return self.username + ":" + self.token