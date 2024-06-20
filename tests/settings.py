INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "emaillist",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",  # In-memory database for testing
    }
}

ROOT_URLCONF = "emaillist.urls"

WEBSITE_URL = "http://example.com"

SECRET_KEY = "fake-key-for-testing"
