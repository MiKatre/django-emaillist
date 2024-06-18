from django.urls import path

from . import views

urlpatterns = [
    path(
        "unsubscribe/<str:email>/<str:token>/<str:list_name>/",
        views.unsubscribe_view,
        name="email_optout",
    ),
    path(
        "confirm/<str:email>/<str:token>/<str:list_name>/",
        views.confirm_subscription,
        name="confirm_subscription",
    ),
]
