from django.test import TestCase
from django.core import mail
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from django.utils import translation
from emaillist.models import Subscription
from emaillist.utils import (
    subscribe,
    unsubscribe,
    is_subscribed,
    is_unsubscribed,
    get_list_members,
    get_user_list_members,
    get_non_user_list_members,
    send_confirmation_email,
)

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

    def test_get_list_members(self):
        # Create subscriptions
        subscribe(self.user, "test_list")
        subscribe("nonuser@example.com", "test_list")
        # Manually confirm the non-user subscription
        Subscription.objects.filter(
            email="nonuser@example.com", list_name="test_list"
        ).update(is_confirmed=True)
        unsubscribe("unsubscribed@example.com", "test_list")
        subscribe("unconfirmed@example.com", "test_list", auto_send_confirmation=False)

        # Get list members
        members = get_list_members("test_list")

        # Check results
        self.assertEqual(len(members), 2)
        self.assertIn(self.user.email, members)
        self.assertIn("nonuser@example.com", members)
        self.assertNotIn("unsubscribed@example.com", members)
        self.assertNotIn("unconfirmed@example.com", members)

    def test_get_user_list_members(self):
        # Create subscriptions
        subscribe(self.user, "test_list")
        subscribe("nonuser@example.com", "test_list")
        unsubscribed_user = User.objects.create_user(
            username="unsubscribed", email="unsubscribed@example.com"
        )
        unsubscribe(unsubscribed_user, "test_list")

        # Get user list members
        user_members = get_user_list_members("test_list")

        # Check results
        self.assertIn(
            self.user, user_members, "The subscribed user should be in the list"
        )
        self.assertNotIn(
            unsubscribed_user,
            user_members,
            "The unsubscribed user should not be in the list",
        )
        self.assertEqual(
            user_members.count(), 1, "Expected only one confirmed and subscribed user"
        )

    def test_get_non_user_list_members(self):
        # Create subscriptions
        subscribe(self.user, "test_list")
        subscribe("nonuser@example.com", "test_list")
        # Manually confirm the non-user subscription
        Subscription.objects.filter(
            email="nonuser@example.com", list_name="test_list"
        ).update(is_confirmed=True)
        unsubscribe("unsubscribed@example.com", "test_list")
        subscribe("unconfirmed@example.com", "test_list", auto_send_confirmation=False)

        # Get non-user list members
        non_user_members = get_non_user_list_members("test_list")

        # Check results
        self.assertEqual(len(non_user_members), 1)
        self.assertIn("nonuser@example.com", non_user_members)
        self.assertNotIn(self.user.email, non_user_members)
        self.assertNotIn("unsubscribed@example.com", non_user_members)
        self.assertNotIn("unconfirmed@example.com", non_user_members)

    def test_send_confirmation_email_no_error(self):
        # Test that send_confirmation_email doesn't raise any exceptions
        try:
            send_confirmation_email("test@example.com", "test_list")
        except Exception as e:
            self.fail(f"send_confirmation_email raised an exception: {str(e)}")

        # Check that an email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Confirm your subscription")
        self.assertEqual(mail.outbox[0].to, ["test@example.com"])

    def test_spanish_translation(self):
        with translation.override('es'):
            # Test a simple string that should be translated
            translated_text = _("Confirm your subscription")
            self.assertEqual(translated_text, "Confirma tu suscripción")

        # Switch back to default language
        translation.activate('en')
