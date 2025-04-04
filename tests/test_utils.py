from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from django.utils import translation
from django.urls import reverse
from django.template.loader import render_to_string
from django.http import HttpResponse
from unittest.mock import patch
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
    get_unsubscribe_url,
    make_token,
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
        # Create an initial subscription
        subscribe(self.user, "unique_list")
        
        # Subscribe again to the same list - should not raise exception now,
        # but should update the existing subscription
        second_subscription = subscribe(self.user, "unique_list")
        
        # Verify there's only one subscription for this user and list
        count = Subscription.objects.filter(
            email=self.user.email, list_name="unique_list"
        ).count()
        self.assertEqual(count, 1)
        
        # Verify subscription is still active
        self.assertTrue(second_subscription.is_subscribed)
        self.assertTrue(second_subscription.is_confirmed)

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

    def test_unsubscribe_url_generation(self):
        # Test unsubscribe URL for a user
        user_url = get_unsubscribe_url(self.user, "test_list")
        self.assertIn(self.user.email, user_url)
        self.assertIn("test_list", user_url)
        self.assertIn("/unsubscribe/", user_url)

        # Test unsubscribe URL for a non-user email
        non_user_url = get_unsubscribe_url("test@example.com", "test_list")
        self.assertIn("test@example.com", non_user_url)
        self.assertIn("test_list", non_user_url)
        self.assertIn("/unsubscribe/", non_user_url)

        # Verify URLs are different for different emails
        self.assertNotEqual(user_url, non_user_url)

    def test_unsubscribe_url_generation_multiple_lists(self):
        # Subscribe user to multiple lists
        subscribe(self.user, "list1")
        subscribe(self.user, "list2")
        subscribe(self.user, "list3")

        # Generate unsubscribe URLs for each list
        url1 = get_unsubscribe_url(self.user, "list1")
        url2 = get_unsubscribe_url(self.user, "list2")
        url3 = get_unsubscribe_url(self.user, "list3")

        # Verify each URL contains the correct list name
        self.assertIn("list1", url1)
        self.assertIn("list2", url2)
        self.assertIn("list3", url3)

        # Verify URLs are different for different lists
        self.assertNotEqual(url1, url2)
        self.assertNotEqual(url2, url3)
        self.assertNotEqual(url1, url3)

        # Verify each URL contains the user's email
        self.assertIn(self.user.email, url1)
        self.assertIn(self.user.email, url2)
        self.assertIn(self.user.email, url3)

    @patch('django.template.response.TemplateResponse.render')
    def test_user_resubscribe_behavior(self, mock_render):
        """Test that when a user unsubscribes and then resubscribes, 
        the subscription remains confirmed and associated with the user."""
        
        # Setup mock render to prevent template errors
        mock_render.return_value = HttpResponse('Mocked response')
        
        # 1. Create initial subscription for user
        list_name = "test_newsletter"
        subscribe(self.user, list_name)
        
        # Verify initial subscription state
        subscription = Subscription.objects.get(email=self.user.email, list_name=list_name)
        self.assertTrue(subscription.is_subscribed)
        self.assertFalse(subscription.is_unsubscribed)
        self.assertTrue(subscription.is_confirmed)  # User subscriptions are auto-confirmed
        self.assertEqual(subscription.user, self.user)
        
        # 2. Generate token for unsubscribe URL
        token = make_token(self.user.email)
        
        # 3. Unsubscribe the user directly rather than using the view
        unsubscribe(self.user, list_name)
        
        # 4. Verify unsubscribed state
        subscription.refresh_from_db()
        self.assertFalse(subscription.is_subscribed)
        self.assertTrue(subscription.is_unsubscribed)
        self.assertTrue(subscription.is_confirmed)  # Confirmation status shouldn't change
        self.assertEqual(subscription.user, self.user)  # User association shouldn't change
        
        # 5. Resubscribe the user
        subscribe(self.user, list_name)
        
        # 6. Verify resubscribed state
        subscription.refresh_from_db()
        self.assertTrue(subscription.is_subscribed)
        self.assertFalse(subscription.is_unsubscribed)
        self.assertTrue(subscription.is_confirmed)  # Should remain confirmed
        self.assertEqual(subscription.user, self.user)  # User association should remain

    @patch('django.template.response.TemplateResponse.render')
    def test_non_user_resubscribe_behavior(self, mock_render):
        """Test that when a non-user email unsubscribes and then resubscribes,
        the subscription maintains its confirmed status."""
        
        # Setup mock render to prevent template errors
        mock_render.return_value = HttpResponse('Mocked response')
        
        # 1. Create initial subscription for non-user email
        email = "nonuser@example.com"
        list_name = "test_newsletter"
        subscribe(email, list_name)
        
        # 2. Manually confirm the subscription (simulating email confirmation)
        subscription = Subscription.objects.get(email=email, list_name=list_name)
        subscription.is_confirmed = True
        subscription.save()
        
        # Verify initial subscription state
        subscription.refresh_from_db()
        self.assertTrue(subscription.is_subscribed)
        self.assertFalse(subscription.is_unsubscribed)
        self.assertTrue(subscription.is_confirmed)
        self.assertIsNone(subscription.user)
        
        # 3. Unsubscribe the email directly rather than using the view
        unsubscribe(email, list_name)
        
        # 4. Verify unsubscribed state
        subscription.refresh_from_db()
        self.assertFalse(subscription.is_subscribed)
        self.assertTrue(subscription.is_unsubscribed)
        self.assertTrue(subscription.is_confirmed)  # Confirmation status shouldn't change
        self.assertIsNone(subscription.user)
        
        # 5. Resubscribe the email
        subscribe(email, list_name)
        
        # 6. Verify resubscribed state
        subscription.refresh_from_db()
        self.assertTrue(subscription.is_subscribed)
        self.assertFalse(subscription.is_unsubscribed)
        self.assertTrue(subscription.is_confirmed)  # Should remain confirmed
        self.assertIsNone(subscription.user)

    def test_subscribe_already_confirmed(self):
        """Test that subscribing an already confirmed subscription returns the existing subscription
        without modification."""
        
        # 1. Create initial subscription for non-user email
        email = "test@example.com"
        list_name = "test_list"
        initial_subscription = subscribe(email, list_name)
        
        # 2. Manually confirm the subscription
        initial_subscription.is_confirmed = True
        initial_subscription.save()
        
        # 3. Subscribe again
        second_subscription = subscribe(email, list_name)
        
        # 4. Verify that we got back the same subscription object
        self.assertEqual(initial_subscription.id, second_subscription.id)
        
        # 5. Verify that no changes were made to the subscription
        self.assertEqual(initial_subscription.is_confirmed, second_subscription.is_confirmed)
        self.assertEqual(initial_subscription.is_subscribed, second_subscription.is_subscribed)
        self.assertEqual(initial_subscription.is_unsubscribed, second_subscription.is_unsubscribed)
        self.assertEqual(initial_subscription.user, second_subscription.user)
        
        # 6. Verify that no confirmation email was sent
        self.assertEqual(len(mail.outbox), 1)  # Only the initial subscription email
