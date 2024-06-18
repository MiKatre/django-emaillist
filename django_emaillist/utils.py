from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.urls import reverse

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
    send_mail(
        "Confirm your subscription",
        f"Please click on the following link to confirm your subscription: {full_confirm_url}",
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )


def subscribe(identifier, list_name, auto_send_confirmation=True):
    # auto_send_confirmation can be set to False for migration operations
    email = get_email(identifier)
    user = identifier if isinstance(identifier, User) else None
    subscription, created = Subscription.objects.update_or_create(
        email=email,
        list_name=list_name,
        defaults={
            "is_subscribed": True,
            "is_unsubscribed": False,
            "user": user,
            "is_confirmed": True if user else False,
        },
    )

    # Send confirmation email only for guests (non-users)
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
    Users amd non-users are included.
    """
    return [
        subscription.email
        for subscription in Subscription.objects.filter(
            list_name=list_name, is_subscribed=True
        )
    ]


def get_user_list_members(list_name):
    """
    Returns a queryset of users that are subscribed to the list.
    Ignore emails that are not associated with a user account.
    """
    return User.objects.filter(
        subscriptions__list_name=list_name, subscriptions__is_subscribed=True
    )


def get_non_user_list_members(list_name):
    """
    Returns a list of email addresses that are subscribed to the list but are not
    associated with a user account.
    """
    return [
        subscription.email
        for subscription in Subscription.objects.filter(
            list_name=list_name, is_subscribed=True, user__isnull=True
        )
    ]


def get_lists():
    return list(Subscription.objects.values_list("list_name", flat=True).distinct())
