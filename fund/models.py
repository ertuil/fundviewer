from django.db import models

# Create your models here.


class WatchFund(models.Model):
    username = models.CharField(max_length=150)
    fundcode = models.CharField(max_length=20)
    fundname = models.CharField(max_length=100, null=True)

    def __str__(self):
        return self.username + ":" + self.fundcode
