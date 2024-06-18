from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        null=True,
    )
    email = models.EmailField()
    list_name = models.CharField(max_length=100)
    is_subscribed = models.BooleanField(default=True)
    is_unsubscribed = models.BooleanField(default=False)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_confirmed = models.BooleanField(default=False)  # Double opt-in for email only

    class Meta:
        unique_together = ("user", "list_name")

    def __str__(self):
        return f"{self.email} - {self.list_name}"
