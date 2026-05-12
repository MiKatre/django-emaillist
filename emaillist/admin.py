from django.contrib import admin

from .models import Subscription
from .utils import (
    get_subscription_projection,
    get_subscription_stats,
    get_subscription_trend,
)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    change_list_template = "admin/emaillist/subscription/change_list.html"

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

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        list_name = request.GET.get("list_name__exact") or request.GET.get("list_name")
        trend = get_subscription_trend(period="week", periods=12, list_name=list_name)
        max_count = max((item["count"] for item in trend), default=0)

        extra_context.update(
            {
                "emaillist_stats": get_subscription_stats(list_name=list_name),
                "emaillist_projection": get_subscription_projection(list_name=list_name),
                "emaillist_trend": [
                    {
                        **item,
                        "bar_width": round(item["count"] / max_count * 100)
                        if max_count
                        else 0,
                    }
                    for item in trend
                ],
            }
        )
        return super().changelist_view(request, extra_context=extra_context)
