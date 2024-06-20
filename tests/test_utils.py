from django.test import TestCase
from django.core import mail
from django.contrib.auth import get_user_model
from emaillist.models import Subscription
from emaillist.utils import subscribe, unsubscribe, is_subscribed, is_unsubscribed

User = get_user_model()


class SubscriptionTests(TestCase):

    def setUp(self):
        # Create a user for testing
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="password"
        )

    def test_subscribe_user(self):
        # Test subscribing a user
        subscription = subscribe(self.user, "test_list")
        self.assertTrue(subscription.is_subscribed)
        self.assertFalse(subscription.is_unsubscribed)
        self.assertTrue(is_subscribed(self.user, "test_list"))
        self.assertFalse(is_unsubscribed(self.user, "test_list"))
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.email, "testuser@example.com")
        self.assertEqual(subscription.list_name, "test_list")
        self.assertTrue(subscription.is_confirmed)

    def test_unsubscribe_user(self):
        # Subscribe and then unsubscribe the user
        subscribe(self.user, "test_list")
        subscription = unsubscribe(self.user, "test_list")
        self.assertFalse(subscription.is_subscribed)
        self.assertTrue(subscription.is_unsubscribed)
        self.assertFalse(is_subscribed(self.user, "test_list"))
        self.assertTrue(is_unsubscribed(self.user, "test_list"))

    def test_subscription_uniqueness(self):
        # Ensuring that a user can't be subscribed to the same list more than once
        subscribe(self.user, "unique_list")
        with self.assertRaises(
            Exception
        ):  # This should raise an IntegrityError or similar exception
            subscribe(self.user, "unique_list")

    def test_subscribe_non_user(self):
        # Test subscribing with an email address that is not linked to a user
        subscription = subscribe(
            "nonuser@example.com", "guest_list", auto_send_confirmation=False
        )
        self.assertTrue(subscription.is_subscribed)
        self.assertIsNone(subscription.user)
        self.assertEqual(subscription.email, "nonuser@example.com")
        self.assertFalse(
            subscription.is_confirmed
        )  # Confirmation should be false by default for non-users until double opt-in via email

    def test_confirmation_email(self):
        # Test that a confirmation email is sent when subscribing a non-user
        subscription = subscribe("nonuser@example.com", "guest_list")
        self.assertTrue(subscription.is_subscribed)
        self.assertEqual(len(mail.outbox), 1)

    def test_resubscribe_user(self):
        # Test the resubscription logic
        subscribe(self.user, "test_list")
        unsubscribe(self.user, "test_list")
        subscription = subscribe(self.user, "test_list")
        self.assertTrue(subscription.is_subscribed)
        self.assertFalse(subscription.is_unsubscribed)
        self.assertTrue(is_subscribed(self.user, "test_list"))
