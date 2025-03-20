from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


from .models import Subscription
from django.contrib.auth import get_user_model

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
