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

# Language settings
LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = True

LANGUAGES = [
    ('en', 'English'),
    ('es', 'Spanish'),
]

LOCALE_PATHS = [
    'emaillist/locale',
]

MIDDLEWARE = [
    'django.middleware.locale.LocaleMiddleware',
]
