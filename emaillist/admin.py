from django.contrib import admin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "list_name",
        "is_subscribed",
        "is_confirmed",
        "is_unsubscribed",
        "user",
        "subscribed_at",
    )
    list_filter = ("list_name", "is_subscribed", "is_unsubscribed", "is_confirmed")
    search_fields = ("email", "user__username")

    # Make it look better
    fieldsets = (
        (None, {"fields": ("email", "list_name", "user")}),
        (
            "Subscription Status",
            {"fields": ("is_subscribed", "is_unsubscribed", "is_confirmed")},
        ),
    )
