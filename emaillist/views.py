from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django_ratelimit.decorators import ratelimit

from .models import Subscription
from .signals import subscription_confirmed, unsubscription_confirmed

from .utils import check_token, subscribe, unsubscribe

User = get_user_model()


@ratelimit(key="ip", rate="5/m", block=True)
def unsubscribe_view(request, email, token, list_name):
    # Attempt to retrieve the user by username; if not found, use identifier as email
    try:
        user = User.objects.get(email=email)
        email = user.email
    except User.DoesNotExist:
        email = email

    if not check_token(token):
        return HttpResponse("Invalid or expired unsubscribe link.", status=400)

    # If the request is POST, means the user has clicked the "Resubscribe" btn.
    if request.method == "POST":
        subscribe(email, list_name)
        subscription_confirmed.send(
            sender=Subscription, email=email, list_name=list_name
        )
        # Redirect to a success page or show a success message
        return TemplateResponse(
            request,
            "emaillist/resubscribed.html",
            {"email": email, "list_name": list_name, "token": token},
        )

    unsubscribe(email, list_name)
    unsubscription_confirmed.send(sender=Subscription, email=email, list_name=list_name)
    return TemplateResponse(request, "emaillist/unsubscribed.html", {"email": email})


def confirm_subscription(request, email, token, list_name):
    is_valid = check_token(token)
    if is_valid:
        # Find the subscription and update it to be confirmed
        Subscription.objects.filter(email=email, list_name=list_name).update(
            is_confirmed=True
        )
        subscription_confirmed.send(
            sender=Subscription, email=email, list_name=list_name
        )
        return TemplateResponse(request, "emaillist/subscription_confirmed.html", {})
    else:
        return TemplateResponse(request, "emaillist/subscription_error.html", {})
