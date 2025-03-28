# Django Email List

<!-- Incredibly useful conversation: https://chat.openai.com/c/01d78616-2bec-41e5-b650-0f14791bd60b -->

## Description

Django Email List manages email subscriptions to mailing lists. It supports subscribing/unsubscribing users and emails to arbitrary lists, with features like unique unsubscribe links, rate limiting, and double opt-in. The templates extend "base.html" and use inline styles compatible with CSS frameworks (Bootstrap, Tailwind, etc.).


## Installation

1. **Install** 

*The package is not yet on pypi*.

```Shell
pip install git+https://github.com/MiKatre/django-emaillist.git
```

2. **Add the App to Your Django Project**:
In your `settings.py`, add the app to the `INSTALLED_APPS` list:
```python
INSTALLED_APPS = [
    # ... other installed apps ...
    'emaillist',
]
```

3. **Include the URLs**:
In your project's `urls.py`, include the emaillist urls:
```python
from django.urls import path, include

urlpatterns = [
    # ... other urls ...
    path('email/', include('emaillist.urls')),
]
```

4. **Run Migrations**: 
Run the Django migrations to create the database tables:
```bash
python manage.py migrate
```

## Configuration

Set the `WEBSITE_URL` in your `settings.py`. This is used for generating unsubscribe links and double opt-in links.
```python
WEBSITE_URL = 'http://yourwebsite.com'
```

## Usage



```Python
from emaillist.utils import subscribe, unsubscribe
```

Subscribe a guest to a list
```Python
subscribe("someone@email.com", "newsletter")
```

Subscribe a user to a list
```Python
user = User.objects.get(username="someone")
subscribe(user, "newsletter")
```

Unsubscribe from a list
```Python
unsubscribe("someone@email.com", "newsletter")
```

Check if subscribed
```Python
is_subscribed("someone@email.com", "newsletter")
```

Get subscribers for a list (use this for sending emails)
```Python
# Get all email subscribers
get_list_members("newsletter")

# Get only logged in users emails
get_user_list_members("newsletter")

# Get only subscribers without account
get_non_user_list_members("newsletter")

```

Get all mailing lists
```Python
get_lists()
```



### Utility Functions
- `subscribe(identifier, list_name)`: Subscribe a user or email to a mailing list and send confirmation link by email (if not user).
- `unsubscribe(identifier, list_name)`: Unsubscribe a user or email from a mailing list.
- `is_subscribed(identifier, list_name)`: Check if a user or email is subscribed to a mailing list.
- `is_unsubscribed(identifier, list_name)`: Check if a user or email is unsubscribed from a mailing list.
- `get_unsubscribe_url(identifier, list_name)`: Generate a secure unsubscribe URL.
- `get_list_members(list_name)`: Get a list of all members subscribed to a given list.
- `get_lists()`: Get a list of all unique list names.
- `get_user_list_members(list_name)`: Get a queryset of `User` objects who are subscribed to a given list.
- `get_non_user_list_members(list_name)`: Retrieve emails of non-user subscribers to a specific list.

### Views
- `unsubscribe_view`: A view to handle unsubscription requests from unsubscribe links.
- `confirm_subscription`: A view to handle subscription confirmation requests.

### Signals
Django Email List provides two signals that you can connect to for additional functionality:

- `subscription_confirmed`: Sent when a subscription is confirmed.
- `unsubscription_confirmed`: Sent when an unsubscription is confirmed.

You can connect to these signals in your code like this:

```python
from django.dispatch import receiver
from emaillist.signals import subscription_confirmed, unsubscription_confirmed

@receiver(subscription_confirmed)
def handle_subscription_confirmed(sender, email, list_name, **kwargs):
    print(f"Subscription confirmed for {email} to {list_name}")

@receiver(unsubscription_confirmed)
def handle_unsubscription_confirmed(sender, email, list_name, **kwargs):
    print(f"Unsubscription confirmed for {email} from {list_name}")
```

### Contributing

Everyone is encouraged to help improve this project. Here are a few ways you can help:

- Report bugs
- Fix bugs and submit pull requests
- Write, clarify, or fix documentation
- Suggest or add new features

Run tests (pipenv required)
```Shell
pipenv install --python 3.9
pipenv run python runtests.py 
```

Translate
```Shell
django-admin makemessages -l es
django-admin makemessages -l fr
django-admin compilemessages
```
