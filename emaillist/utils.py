from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Subscription

User = get_user_model()


def get_email(identifier):
    if isinstance(identifier, User):
        return identifier.email
    return identifier


def send_confirmation_email(email, list_name):
    token = make_token(email)
    confirm_url = reverse(
        "confirm_subscription",
        kwargs={"email": email, "token": token, "list_name": list_name},
    )
    full_confirm_url = f"{settings.WEBSITE_URL}{confirm_url}"

    subject = _("Confirm your subscription")
    body_text = _("Please click on the following link to confirm your subscription: ")
    text_content = body_text + full_confirm_url
    html_content = f"""
    <html>
    <body>
        <p>{body_text}</p>
        <p><a href="{full_confirm_url}">{subject}</a></p>
    </body>
    </html>
    """

    msg = EmailMultiAlternatives(
        subject, text_content, settings.DEFAULT_FROM_EMAIL, [email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)


def subscribe(identifier, list_name, auto_send_confirmation=True):
    # auto_send_confirmation can be set to False for migration operations
    email = get_email(identifier)
    user = identifier if isinstance(identifier, User) else None
    
    # Get existing subscription if it exists
    existing_subscription = Subscription.objects.filter(
        email=email, list_name=list_name
    ).first()
    
    # If the user is already subscribed and confirmed, we don't need to create a new subscription
    if existing_subscription and existing_subscription.is_subscribed and existing_subscription.is_confirmed:
        return existing_subscription
    
    # Determine if we should keep the existing confirmation status
    is_confirmed = True if user else (existing_subscription.is_confirmed if existing_subscription else False)
    
    subscription, created = Subscription.objects.update_or_create(
        email=email,
        list_name=list_name,
        defaults={
            "is_subscribed": True,
            "is_unsubscribed": False,
            "user": user,
            "is_confirmed": is_confirmed,
        },
    )

    # Send confirmation email only for guests (non-users) and only if it's a new subscription
    if created and not user and auto_send_confirmation:
        send_confirmation_email(email, list_name)

    return subscription


def unsubscribe(identifier, list_name):
    email = get_email(identifier)
    subscription, created = Subscription.objects.update_or_create(
        email=email,
        list_name=list_name,
        defaults={"is_subscribed": False, "is_unsubscribed": True},
    )
    return subscription


def is_subscribed(identifier, list_name):
    email = get_email(identifier)
    return Subscription.objects.filter(
        email=email, list_name=list_name, is_subscribed=True
    ).exists()


def is_unsubscribed(identifier, list_name):
    return not is_subscribed(identifier, list_name)


def get_unsubscribe_url(identifier, list_name):
    email = get_email(identifier)
    token = make_token(email)
    unsubscribe_url = reverse(
        "email_optout", kwargs={"email": email, "token": token, "list_name": list_name}
    )
    return f"{settings.WEBSITE_URL}{unsubscribe_url}"


def make_token(email):
    signer = TimestampSigner()
    return signer.sign(email)


def check_token(token):
    email, token = token.split(":", 1)
    signer = TimestampSigner()
    key = f"{email}:{token}"
    try:
        signer.unsign(key, max_age=3600 * 24 * 7)  # Valid for 7 days
        return True
    except (BadSignature, SignatureExpired):
        return False


def get_list_members(list_name):
    """
    Returns a list of email addresses that are subscribed to the list.
    Users and non-users are included. Only confirmed and subscribed members are returned.
    """
    return list(
        Subscription.objects.filter(
            list_name=list_name, is_subscribed=True, is_confirmed=True
        ).values_list("email", flat=True)
    )


def get_user_list_members(list_name):
    """
    Returns a queryset of users that are subscribed to the list.
    Only confirmed and subscribed users are returned.
    """
    return User.objects.filter(
        subscriptions__list_name=list_name,
        subscriptions__is_subscribed=True,
        subscriptions__is_confirmed=True,
    ).distinct()


def get_non_user_list_members(list_name):
    """
    Returns a list of email addresses that are subscribed to the list but are not
    associated with a user account. Only confirmed and subscribed members are returned.
    """
    return list(
        Subscription.objects.filter(
            list_name=list_name,
            is_subscribed=True,
            is_confirmed=True,
            user__isnull=True,
        ).values_list("email", flat=True)
    )


def get_lists():
    return list(Subscription.objects.values_list("list_name", flat=True).distinct())


def _current_date(now=None):
    if now is None:
        now = timezone.now()

    if timezone.is_aware(now):
        return timezone.localtime(now).date()

    return now.date()


def _subscription_queryset(list_name=None):
    queryset = Subscription.objects.all()
    if list_name:
        queryset = queryset.filter(list_name=list_name)
    return queryset


def get_subscription_stats(list_name=None, now=None):
    """
    Return high-level subscription counts for admin dashboards or custom views.
    """
    today = _current_date(now)
    yesterday = today - timedelta(days=1)
    last_7_days = today - timedelta(days=6)
    last_30_days = today - timedelta(days=29)
    queryset = _subscription_queryset(list_name)
    active_queryset = queryset.filter(is_subscribed=True, is_confirmed=True)

    by_list = list(
        queryset.values("list_name")
        .annotate(
            total=Count("id"),
            active=Count("id", filter=Q(is_subscribed=True, is_confirmed=True)),
            unconfirmed=Count(
                "id", filter=Q(is_subscribed=True, is_confirmed=False)
            ),
            unsubscribed=Count("id", filter=Q(is_unsubscribed=True)),
        )
        .order_by("-active", "list_name")
    )

    return {
        "list_name": list_name,
        "new_today": active_queryset.filter(subscribed_at__date=today).count(),
        "new_yesterday": active_queryset.filter(subscribed_at__date=yesterday).count(),
        "new_last_7_days": active_queryset.filter(
            subscribed_at__date__gte=last_7_days
        ).count(),
        "new_last_30_days": active_queryset.filter(
            subscribed_at__date__gte=last_30_days
        ).count(),
        "total": queryset.count(),
        "active": active_queryset.count(),
        "unconfirmed": queryset.filter(
            is_subscribed=True, is_confirmed=False
        ).count(),
        "unsubscribed": queryset.filter(is_unsubscribed=True).count(),
        "by_list": by_list,
    }


def _active_subscription_queryset(list_name=None):
    return _subscription_queryset(list_name).filter(
        is_subscribed=True,
        is_confirmed=True,
    )


def _subscription_count_since(queryset, date):
    return queryset.filter(subscribed_at__date__gte=date).count()


def get_subscription_projection(
    list_name=None,
    now=None,
    baseline_days=60,
    recent_days=14,
    recent_weight=0.3,
):
    """
    Project active confirmed subscribers from a blended baseline/recent pace.
    """
    if baseline_days < 1:
        raise ValueError("baseline_days must be greater than zero")
    if recent_days < 1:
        raise ValueError("recent_days must be greater than zero")
    if not 0 <= recent_weight <= 1:
        raise ValueError("recent_weight must be between 0 and 1")

    today = _current_date(now)
    queryset = _active_subscription_queryset(list_name)
    active = queryset.count()
    baseline_count = _subscription_count_since(
        queryset,
        today - timedelta(days=baseline_days - 1),
    )
    recent_count = _subscription_count_since(
        queryset,
        today - timedelta(days=recent_days - 1),
    )
    baseline_daily_rate = baseline_count / baseline_days
    recent_daily_rate = recent_count / recent_days
    projected_daily_rate = (
        baseline_daily_rate * (1 - recent_weight)
        + recent_daily_rate * recent_weight
    )

    if baseline_daily_rate == 0:
        momentum = "rising" if recent_daily_rate > 0 else "steady"
    elif recent_daily_rate > baseline_daily_rate * 1.15:
        momentum = "rising"
    elif recent_daily_rate < baseline_daily_rate * 0.85:
        momentum = "slowing"
    else:
        momentum = "steady"

    return {
        "list_name": list_name,
        "active": active,
        "baseline_days": baseline_days,
        "recent_days": recent_days,
        "baseline_count": baseline_count,
        "recent_count": recent_count,
        "baseline_daily_rate": baseline_daily_rate,
        "recent_daily_rate": recent_daily_rate,
        "projected_daily_rate": projected_daily_rate,
        "momentum": momentum,
        "in_30_days": round(active + projected_daily_rate * 30),
        "in_6_months": round(active + projected_daily_rate * 182),
        "in_1_year": round(active + projected_daily_rate * 365),
    }


def _add_months(value, months):
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    return value.replace(year=year, month=month, day=1)


def _period_start(value, period):
    if period == "day":
        return value
    if period == "week":
        return value - timedelta(days=value.weekday())
    if period == "month":
        return value.replace(day=1)
    raise ValueError("period must be one of: day, week, month")


def _period_offset(value, period, offset):
    if period == "day":
        return value + timedelta(days=offset)
    if period == "week":
        return value + timedelta(weeks=offset)
    return _add_months(value, offset)


def get_subscription_trend(
    days=30,
    list_name=None,
    now=None,
    period="day",
    periods=None,
):
    """
    Return zero-filled subscription counts by day, week, or month.

    ``days`` keeps the previous daily API working. For weekly/monthly trends,
    pass ``period="week"`` or ``period="month"`` with ``periods``.
    """
    if period not in {"day", "week", "month"}:
        raise ValueError("period must be one of: day, week, month")

    if periods is None:
        periods = days if period == "day" else 12

    if periods < 1:
        raise ValueError("periods must be greater than zero")

    end_date = _period_start(_current_date(now), period)
    start_date = _period_offset(end_date, period, -(periods - 1))
    queryset = _subscription_queryset(list_name)

    dates = queryset.filter(
        subscribed_at__date__gte=start_date,
        subscribed_at__date__lte=_current_date(now),
        is_subscribed=True,
        is_confirmed=True,
    ).values_list("subscribed_at", flat=True)

    counts_by_period = {}
    for subscribed_at in dates:
        if timezone.is_aware(subscribed_at):
            subscribed_at = timezone.localtime(subscribed_at)
        bucket = _period_start(subscribed_at.date(), period)
        counts_by_period[bucket] = counts_by_period.get(bucket, 0) + 1

    return [
        {
            "day": _period_offset(start_date, period, offset),
            "period": period,
            "count": counts_by_period.get(
                _period_offset(start_date, period, offset), 0
            ),
        }
        for offset in range(periods)
    ]
