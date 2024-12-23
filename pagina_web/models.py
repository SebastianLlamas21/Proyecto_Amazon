from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mongo_user_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.user.username