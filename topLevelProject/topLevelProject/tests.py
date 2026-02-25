"""
tests.py  –  Full test suite for the Digital Estate Planning application.

Coverage:
  accounts  – CustomUser model, UserRegistrationForm, UserLoginForm,
               account signals, register/login/logout/payment views
  dashboard – Profile, Contact, Account, Device, DigitalEstateDocument,
               ImportantDocument, FuneralPlan, RelevanceReview models;
               all dashboard forms; all dashboard views; signals;
               mixins; ownership isolation; edge cases

Usage:
  python manage.py test                      # whole project
  python manage.py test dashboard            # dashboard app only
  python manage.py test accounts             # accounts app only
  python manage.py test --verbosity=2        # verbose output

Place this file at:
  <project_root>/tests.py          (or)
  accounts/tests.py + dashboard/tests.py  (split as needed)
"""

import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

User = get_user_model()

# ---------------------------------------------------------------------------
# Import models – guard so test file can be discovered without crashing when
# optional apps aren't installed.
# ---------------------------------------------------------------------------
from dashboard.models import (
    Account,
    Contact,
    Device,
    DigitalEstateDocument,
    FamilyNeedsToKnowSection,
    FuneralPlan,
    ImportantDocument,
    Profile,
    RelevanceReview,
)
from dashboard.forms import (
    AccountForm,
    ContactForm,
    DigitalEstateDocumentForm,
    FuneralPlanAdminForm,
    FuneralPlanPersonalInfoForm,
    FuneralPlanReceptionForm,
    FuneralPlanServiceForm,
    ImportantDocumentForm,
    ProfileForm,
    RelevanceReviewForm,
)
from accounts.forms import UserRegistrationForm, UserLoginForm


# ============================================================================
# FACTORIES & HELPERS
# ============================================================================

class UserFactory:
    """Centralised user creation helpers used across all test cases."""

    @staticmethod
    def create_legacy(username="legacyuser", email="legacy@example.com", **kwargs):
        user = User.objects.create_user(
            username=username, email=email, password="TestPass123!"
        )
        user.upgrade_to_legacy()
        return user

    @staticmethod
    def create_essentials(username="essentialsuser", email="essentials@example.com", **kwargs):
        user = User.objects.create_user(
            username=username, email=email, password="TestPass123!"
        )
        user.upgrade_to_essentials()
        return user

    @staticmethod
    def create_unpaid(username="unpaiduser", email="unpaid@example.com", **kwargs):
        user = User.objects.create_user(
            username=username, email=email, password="TestPass123!"
        )
        return user

    @staticmethod
    def create_expired_essentials(username="expireduser", email="expired@example.com"):
        user = User.objects.create_user(
            username=username, email=email, password="TestPass123!"
        )
        user.subscription_tier = "essentials"
        user.has_paid = True
        user.essentials_expires = timezone.now() - timedelta(days=10)
        user.save()
        return user


def make_profile(user, **overrides):
    defaults = dict(
        first_name="Jane",
        last_name="Doe",
        address_1="123 Main St",
        city="Springfield",
        state="IL",
    )
    defaults.update(overrides)
    return Profile.objects.create(user=user, **defaults)


def make_contact(profile, relation="Spouse", **overrides):
    defaults = dict(
        first_name="John",
        last_name="Smith",
        contact_relation=relation,
        address_1="456 Oak Ave",
        city="Springfield",
        state="IL",
        is_emergency_contact=True,
    )
    defaults.update(overrides)
    return Contact.objects.create(profile=profile, **defaults)


def make_account(profile, contact, **overrides):
    defaults = dict(
        account_name_or_provider="Gmail",
        account_category="Email Account",
        delegated_account_to=contact,
        review_time=30,
    )
    defaults.update(overrides)
    return Account.objects.create(profile=profile, **defaults)


def make_device(profile, contact, **overrides):
    defaults = dict(
        device_name="iPhone 14",
        device_type="Phone",
        delegated_device_to=contact,
        review_time=30,
    )
    defaults.update(overrides)
    return Device.objects.create(profile=profile, **defaults)


def make_estate_doc(profile, contact, **overrides):
    defaults = dict(
        name_or_title="Living Will",
        estate_category="Advance Directive / Living Will",
        delegated_estate_to=contact,
        applies_on_death=True,
        review_time=30,
    )
    defaults.update(overrides)
    return DigitalEstateDocument.objects.create(profile=profile, **defaults)


def make_important_doc(profile, contact, **overrides):
    defaults = dict(
        name_or_title="Birth Certificate",
        document_category="Important Personal Documents",
        delegated_important_document_to=contact,
        applies_on_death=True,
        review_time=30,
    )
    defaults.update(overrides)
    return ImportantDocument.objects.create(profile=profile, **defaults)


# ============================================================================
# 1. CUSTOMUSER MODEL TESTS
# ============================================================================

class CustomUserSubscriptionTierTests(TestCase):

    def test_upgrade_to_legacy_sets_fields(self):
        user = User.objects.create_user("u1", "u1@x.com", "pass")
        user.upgrade_to_legacy()
        self.assertEqual(user.subscription_tier, "legacy")
        self.assertTrue(user.has_paid)
        self.assertIsNotNone(user.legacy_granted_date)

    def test_upgrade_to_essentials_sets_fields(self):
        user = User.objects.create_user("u2", "u2@x.com", "pass")
        user.upgrade_to_essentials()
        self.assertEqual(user.subscription_tier, "essentials")
        self.assertTrue(user.has_paid)
        self.assertIsNotNone(user.essentials_expires)
        delta = (user.essentials_expires - timezone.now()).days
        self.assertGreaterEqual(delta, 364)

    def test_legacy_can_view_and_modify(self):
        user = UserFactory.create_legacy()
        self.assertTrue(user.can_view_data())
        self.assertTrue(user.can_modify_data())

    def test_active_essentials_can_view_and_modify(self):
        user = UserFactory.create_essentials()
        self.assertTrue(user.can_view_data())
        self.assertTrue(user.can_modify_data())

    def test_expired_essentials_can_view_but_not_modify(self):
        user = UserFactory.create_expired_essentials()
        self.assertTrue(user.can_view_data())
        self.assertFalse(user.can_modify_data())

    def test_unpaid_cannot_view_or_modify(self):
        user = UserFactory.create_unpaid()
        self.assertFalse(user.can_view_data())
        self.assertFalse(user.can_modify_data())

    def test_inactive_legacy_user_cannot_view_or_modify(self):
        user = UserFactory.create_legacy(username="inactive_legacy", email="il@x.com")
        user.is_active = False
        user.save()
        self.assertFalse(user.can_view_data())
        self.assertFalse(user.can_modify_data())

    def test_is_essentials_edit_active_true_when_not_expired(self):
        user = UserFactory.create_essentials()
        self.assertTrue(user.is_essentials_edit_active())

    def test_is_essentials_edit_active_false_when_expired(self):
        user = UserFactory.create_expired_essentials()
        self.assertFalse(user.is_essentials_edit_active())

    def test_days_until_essentials_expires_positive_when_active(self):
        user = UserFactory.create_essentials()
        self.assertGreater(user.days_until_essentials_expires(), 0)

    def test_days_until_essentials_expires_zero_when_expired(self):
        user = UserFactory.create_expired_essentials()
        self.assertEqual(user.days_until_essentials_expires(), 0)

    def test_get_tier_display_name_legacy(self):
        user = UserFactory.create_legacy()
        self.assertIn("Legacy", user.get_tier_display_name())

    def test_get_tier_display_name_essentials_active(self):
        user = UserFactory.create_essentials()
        display = user.get_tier_display_name()
        self.assertIn("Essentials", display)
        self.assertIn("days", display.lower())

    def test_get_tier_display_name_essentials_expired(self):
        user = UserFactory.create_expired_essentials()
        self.assertIn("View-only", user.get_tier_display_name())

    def test_get_tier_display_name_no_subscription(self):
        user = UserFactory.create_unpaid()
        self.assertIn("No Subscription", user.get_tier_display_name())

    def test_account_not_locked_by_default(self):
        user = User.objects.create_user("ulock", "ulock@x.com", "pass")
        self.assertFalse(user.is_account_locked())

    def test_account_locked_when_locked_until_in_future(self):
        user = User.objects.create_user("ulocked2", "ulocked2@x.com", "pass")
        user.account_locked_until = timezone.now() + timedelta(hours=1)
        user.save()
        self.assertTrue(user.is_account_locked())

    def test_account_not_locked_when_locked_until_in_past(self):
        user = User.objects.create_user("ulocked3", "ulocked3@x.com", "pass")
        user.account_locked_until = timezone.now() - timedelta(hours=1)
        user.save()
        self.assertFalse(user.is_account_locked())


# ============================================================================
# 2. ACCOUNTS APP FORM TESTS
# ============================================================================

class UserRegistrationFormTests(TestCase):

    def _valid_data(self, **overrides):
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "ComplexPass999!",
            "password2": "ComplexPass999!",
        }
        data.update(overrides)
        return data

    def test_valid_registration_form(self):
        form = UserRegistrationForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_email_rejected(self):
        User.objects.create_user("existing", "dupe@example.com", "pass")
        form = UserRegistrationForm(data=self._valid_data(email="dupe@example.com"))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_duplicate_username_rejected(self):
        User.objects.create_user("taken", "other@example.com", "pass")
        form = UserRegistrationForm(data=self._valid_data(username="taken"))
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_mismatched_passwords_rejected(self):
        form = UserRegistrationForm(data=self._valid_data(password2="WrongPass999!"))
        self.assertFalse(form.is_valid())

    def test_email_stored_lowercase(self):
        form = UserRegistrationForm(data=self._valid_data(email="UPPER@EXAMPLE.COM"))
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "upper@example.com")


class UserLoginFormTests(TestCase):

    def test_login_form_valid_data(self):
        form = UserLoginForm(data={"username_or_email": "user", "password": "pass"})
        self.assertTrue(form.is_valid())

    def test_login_form_missing_password(self):
        form = UserLoginForm(data={"username_or_email": "user", "password": ""})
        self.assertFalse(form.is_valid())

    def test_login_form_missing_username(self):
        form = UserLoginForm(data={"username_or_email": "", "password": "pass"})
        self.assertFalse(form.is_valid())


# ============================================================================
# 3. ACCOUNTS APP VIEW TESTS
# ============================================================================

class RegisterViewTests(TestCase):

    def test_register_page_renders(self):
        r = self.client.get(reverse("accounts:register"))
        self.assertEqual(r.status_code, 200)

    def test_valid_registration_creates_user(self):
        self.client.post(reverse("accounts:register"), {
            "username": "brandnew",
            "email": "brandnew@example.com",
            "password1": "ComplexPass999!",
            "password2": "ComplexPass999!",
        })
        self.assertTrue(User.objects.filter(username="brandnew").exists())

    def test_duplicate_email_does_not_create_user(self):
        User.objects.create_user("existing2", "taken2@example.com", "pass")
        self.client.post(reverse("accounts:register"), {
            "username": "newname",
            "email": "taken2@example.com",
            "password1": "ComplexPass999!",
            "password2": "ComplexPass999!",
        })
        self.assertEqual(User.objects.filter(email="taken2@example.com").count(), 1)

    def test_mismatched_passwords_rejected(self):
        r = self.client.post(reverse("accounts:register"), {
            "username": "mismatch",
            "email": "mismatch@example.com",
            "password1": "ComplexPass999!",
            "password2": "Different999!",
        })
        self.assertFalse(User.objects.filter(username="mismatch").exists())


class LoginViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("logintest", "logintest@x.com", "TestPass123!")

    def test_login_page_renders(self):
        r = self.client.get(reverse("accounts:login"))
        self.assertEqual(r.status_code, 200)

    def test_valid_login_authenticates(self):
        r = self.client.post(reverse("accounts:login"), {
            "username_or_email": "logintest",
            "password": "TestPass123!",
        }, follow=True)
        self.assertTrue(r.wsgi_request.user.is_authenticated)

    def test_invalid_password_rejected(self):
        r = self.client.post(reverse("accounts:login"), {
            "username_or_email": "logintest",
            "password": "WrongPassword!",
        }, follow=True)
        self.assertFalse(r.wsgi_request.user.is_authenticated)

    def test_login_with_email_works(self):
        r = self.client.post(reverse("accounts:login"), {
            "username_or_email": "logintest@x.com",
            "password": "TestPass123!",
        }, follow=True)
        self.assertTrue(r.wsgi_request.user.is_authenticated)


class PaymentViewTests(TestCase):

    def test_payment_page_accessible_to_unauthenticated(self):
        r = self.client.get(reverse("accounts:payment"))
        self.assertIn(r.status_code, [200, 302])

    def test_payment_page_accessible_to_unpaid_user(self):
        user = UserFactory.create_unpaid(username="paytest", email="paytest@x.com")
        self.client.force_login(user)
        r = self.client.get(reverse("accounts:payment"))
        self.assertIn(r.status_code, [200, 302])


# ============================================================================
# 4. PROFILE MODEL TESTS
# ============================================================================

class ProfileModelTests(TestCase):

    def test_str_contains_first_name(self):
        user = UserFactory.create_legacy(username="p1", email="p1@x.com")
        profile = make_profile(user, first_name="Alice")
        self.assertIn("Alice", str(profile))

    def test_one_profile_per_user(self):
        user = UserFactory.create_legacy(username="p2", email="p2@x.com")
        make_profile(user)
        with self.assertRaises(Exception):
            make_profile(user)

    def test_profile_creation_creates_self_contact(self):
        """Signal should auto-create a 'Self' contact."""
        user = UserFactory.create_legacy(username="p3", email="p3@x.com")
        make_profile(user)
        self.assertTrue(
            Contact.objects.filter(profile__user=user, contact_relation="Self").exists()
        )

    def test_profile_update_syncs_self_contact(self):
        """Updating profile.first_name should sync the Self contact."""
        user = UserFactory.create_legacy(username="p4", email="p4@x.com")
        profile = make_profile(user, first_name="Old")
        profile.first_name = "New"
        profile.save()
        self_contact = Contact.objects.get(profile=profile, contact_relation="Self")
        self.assertEqual(self_contact.first_name, "New")

    def test_repeated_saves_do_not_create_duplicate_self_contacts(self):
        user = UserFactory.create_legacy(username="p5", email="p5@x.com")
        profile = make_profile(user)
        profile.save()
        profile.save()
        count = Contact.objects.filter(profile=profile, contact_relation="Self").count()
        self.assertEqual(count, 1)


# ============================================================================
# 5. CONTACT MODEL TESTS
# ============================================================================

class ContactModelTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="ctuser", email="ct@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_str_contains_last_name_and_relation(self):
        s = str(self.contact)
        self.assertIn("Smith", s)
        self.assertIn("Spouse", s)

    def test_get_estate_documents_count_zero(self):
        self.assertEqual(self.contact.get_estate_documents_count(), 0)

    def test_get_important_documents_count_zero(self):
        self.assertEqual(self.contact.get_important_documents_count(), 0)

    def test_get_total_documents_count_sums_both(self):
        make_estate_doc(self.profile, self.contact)
        make_important_doc(self.profile, self.contact)
        self.assertEqual(self.contact.get_total_documents_count(), 2)


# ============================================================================
# 6. ACCOUNT MODEL TESTS
# ============================================================================

class AccountModelTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="acctuser", email="acct@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_str_contains_provider_name(self):
        account = make_account(self.profile, self.contact, account_name_or_provider="Outlook")
        self.assertIn("Outlook", str(account))

    def test_creating_account_creates_relevance_review(self):
        before = RelevanceReview.objects.count()
        make_account(self.profile, self.contact)
        self.assertEqual(RelevanceReview.objects.count(), before + 1)

    def test_review_next_due_matches_review_time(self):
        account = make_account(self.profile, self.contact, review_time=60)
        review = RelevanceReview.objects.filter(account_review=account).first()
        expected = date.today() + timedelta(days=60)
        self.assertEqual(review.next_review_due, expected)

    def test_changing_review_time_updates_latest_review_due(self):
        account = make_account(self.profile, self.contact, review_time=30)
        account.review_time = 365
        account.save()
        review = RelevanceReview.objects.filter(account_review=account).latest("review_date")
        expected = date.today() + timedelta(days=365)
        self.assertEqual(review.next_review_due, expected)


# ============================================================================
# 7. DEVICE MODEL TESTS
# ============================================================================

class DeviceModelTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="devuser", email="dev@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_str_contains_device_name(self):
        device = make_device(self.profile, self.contact, device_name="iPad Pro")
        self.assertIn("iPad Pro", str(device))

    def test_creating_device_creates_review(self):
        before = RelevanceReview.objects.count()
        make_device(self.profile, self.contact)
        self.assertEqual(RelevanceReview.objects.count(), before + 1)


# ============================================================================
# 8. ESTATE DOCUMENT MODEL TESTS
# ============================================================================

class EstateDocumentModelTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="estuser", email="est@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_str_contains_name_and_contact(self):
        doc = make_estate_doc(self.profile, self.contact)
        self.assertIn("Living Will", str(doc))
        self.assertIn("John", str(doc))

    def test_creating_doc_creates_review(self):
        before = RelevanceReview.objects.count()
        make_estate_doc(self.profile, self.contact)
        self.assertEqual(RelevanceReview.objects.count(), before + 1)


# ============================================================================
# 9. IMPORTANT DOCUMENT MODEL TESTS
# ============================================================================

class ImportantDocumentModelTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="imduser", email="imd@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_str_contains_title_and_contact(self):
        doc = make_important_doc(self.profile, self.contact)
        self.assertIn("Birth Certificate", str(doc))

    def test_creating_important_doc_creates_review(self):
        before = RelevanceReview.objects.count()
        make_important_doc(self.profile, self.contact)
        self.assertEqual(RelevanceReview.objects.count(), before + 1)


# ============================================================================
# 10. FUNERAL PLAN MODEL TESTS
# ============================================================================

class FuneralPlanModelTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="fpuser", email="fp@x.com")
        self.profile = make_profile(self.user)

    def _make_plan(self, **kwargs):
        return FuneralPlan.objects.create(profile=self.profile, **kwargs)

    def test_str_contains_funeral_plan(self):
        plan = self._make_plan()
        self.assertIn("Funeral Plan", str(plan))

    def test_is_complete_true_when_all_required_fields_set(self):
        plan = self._make_plan(
            disposition_method="Cremation",
            service_type="Memorial Service",
            officiant_name_freetext="Rev. Smith",
            payment_arrangements="Pre-paid",
        )
        self.assertTrue(plan.is_complete)

    def test_is_complete_false_when_missing_fields(self):
        plan = self._make_plan(disposition_method="Cremation")
        self.assertFalse(plan.is_complete)

    def test_has_disposition_set_true(self):
        plan = self._make_plan(disposition_method="Burial")
        self.assertTrue(plan.has_disposition_set)

    def test_has_disposition_set_false(self):
        plan = self._make_plan()
        self.assertFalse(plan.has_disposition_set)

    def test_has_service_preferences_true(self):
        plan = self._make_plan(service_type="Traditional Funeral")
        self.assertTrue(plan.has_service_preferences)

    def test_one_plan_per_profile(self):
        self._make_plan()
        with self.assertRaises(Exception):
            self._make_plan()


# ============================================================================
# 11. RELEVANCE REVIEW MODEL TESTS
# ============================================================================

class RelevanceReviewModelTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="revuser", email="rev@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_get_item_type_account(self):
        account = make_account(self.profile, self.contact)
        review = RelevanceReview.objects.filter(account_review=account).first()
        self.assertEqual(review.get_item_type(), "Account")

    def test_get_item_type_device(self):
        device = make_device(self.profile, self.contact)
        review = RelevanceReview.objects.filter(device_review=device).first()
        self.assertEqual(review.get_item_type(), "Device")

    def test_get_item_type_estate(self):
        doc = make_estate_doc(self.profile, self.contact)
        review = RelevanceReview.objects.filter(estate_review=doc).first()
        self.assertEqual(review.get_item_type(), "Estate Document")

    def test_get_item_type_important(self):
        doc = make_important_doc(self.profile, self.contact)
        review = RelevanceReview.objects.filter(important_document_review=doc).first()
        self.assertEqual(review.get_item_type(), "Important Document")

    def test_get_item_name_account(self):
        account = make_account(self.profile, self.contact, account_name_or_provider="Dropbox")
        review = RelevanceReview.objects.filter(account_review=account).first()
        self.assertEqual(review.get_item_name(), "Dropbox")

    def test_get_reviewed_item_returns_instance(self):
        account = make_account(self.profile, self.contact)
        review = RelevanceReview.objects.filter(account_review=account).first()
        self.assertEqual(review.get_reviewed_item(), account)

    def test_clean_raises_if_no_target(self):
        review = RelevanceReview(reviewer=self.user)
        with self.assertRaises(ValidationError):
            review.clean()

    def test_clean_raises_if_multiple_targets(self):
        account = make_account(self.profile, self.contact)
        device = make_device(self.profile, self.contact)
        review = RelevanceReview(
            reviewer=self.user,
            account_review=account,
            device_review=device,
        )
        with self.assertRaises(ValidationError):
            review.clean()

    def test_str_contains_item_type(self):
        account = make_account(self.profile, self.contact)
        review = RelevanceReview.objects.filter(account_review=account).first()
        self.assertIn("Account", str(review))


# ============================================================================
# 12. DASHBOARD FORM TESTS
# ============================================================================

class ProfileFormTests(TestCase):

    def _data(self, **overrides):
        d = {
            "first_name": "Alice",
            "last_name": "Wonder",
            "address_1": "1 Magic Lane",
            "city": "Oz",
            "state": "KS",
        }
        d.update(overrides)
        return d

    def test_valid_profile_form(self):
        form = ProfileForm(data=self._data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_first_name_invalid(self):
        form = ProfileForm(data=self._data(first_name=""))
        self.assertFalse(form.is_valid())

    def test_missing_last_name_invalid(self):
        form = ProfileForm(data=self._data(last_name=""))
        self.assertFalse(form.is_valid())

    def test_invalid_email_rejected(self):
        form = ProfileForm(data=self._data(email="not-an-email"))
        self.assertFalse(form.is_valid())

    def test_valid_email_accepted(self):
        form = ProfileForm(data=self._data(email="alice@example.com"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_blank_email_accepted(self):
        form = ProfileForm(data=self._data(email=""))
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_phone_rejected(self):
        form = ProfileForm(data=self._data(phone="abc-def"))
        self.assertFalse(form.is_valid())

    def test_valid_phone_accepted(self):
        form = ProfileForm(data=self._data(phone="+1 (312) 555-0100"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_blank_phone_accepted(self):
        form = ProfileForm(data=self._data(phone=""))
        self.assertTrue(form.is_valid(), form.errors)


class ContactFormTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="cfuser", email="cf@x.com")
        self.profile = make_profile(self.user)

    def _data(self, **overrides):
        d = {
            "first_name": "Bob",
            "last_name": "Jones",
            "contact_relation": "Brother",
            "address_1": "7 Elm St",
            "city": "Shelbyville",
            "state": "IL",
            "is_emergency_contact": True,
        }
        d.update(overrides)
        return d

    def test_valid_contact_form(self):
        form = ContactForm(data=self._data(), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_no_role_raises_non_field_error(self):
        d = self._data()
        d["is_emergency_contact"] = False
        form = ContactForm(data=d, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_multiple_roles_allowed(self):
        d = self._data()
        d["is_digital_executor"] = True
        form = ContactForm(data=d, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_first_name_rejected(self):
        form = ContactForm(data=self._data(first_name=""), user=self.user)
        self.assertFalse(form.is_valid())

    def test_invalid_phone_rejected(self):
        form = ContactForm(data=self._data(phone="!@#$"), user=self.user)
        self.assertFalse(form.is_valid())


class AccountFormTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="afuser", email="af@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def _data(self, **overrides):
        d = {
            "delegated_account_to": self.contact.pk,
            "account_category": "Email Account",
            "account_name_or_provider": "Gmail",
            "review_time": 30,
            "keep_or_close_instruction": "Close Account",
        }
        d.update(overrides)
        return d

    def test_valid_account_form(self):
        form = AccountForm(data=self._data(), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_other_users_contact_not_in_queryset(self):
        other_user = UserFactory.create_legacy(username="other_af", email="oaf@x.com")
        other_profile = make_profile(other_user)
        other_contact = make_contact(other_profile)
        form = AccountForm(data=self._data(delegated_account_to=other_contact.pk), user=self.user)
        self.assertFalse(form.is_valid())

    def test_invalid_url_rejected(self):
        form = AccountForm(data=self._data(website_url="not-a-url"), user=self.user)
        self.assertFalse(form.is_valid())

    def test_valid_url_accepted(self):
        form = AccountForm(data=self._data(website_url="https://gmail.com"), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_blank_url_accepted(self):
        form = AccountForm(data=self._data(website_url=""), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_no_profile_user_gets_empty_queryset(self):
        no_profile_user = UserFactory.create_legacy(username="noprofile_af", email="npaf@x.com")
        form = AccountForm(user=no_profile_user)
        self.assertEqual(form.fields["delegated_account_to"].queryset.count(), 0)


class DigitalEstateDocumentFormTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="dedfuser", email="ded@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def _data(self, **overrides):
        d = {
            "delegated_estate_to": self.contact.pk,
            "estate_category": "Advance Directive / Living Will",
            "name_or_title": "My Living Will",
            "review_time": 30,
            "applies_on_death": True,
        }
        d.update(overrides)
        return d

    def test_valid_estate_form(self):
        form = DigitalEstateDocumentForm(data=self._data(), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_no_declaration_invalid(self):
        d = self._data()
        d["applies_on_death"] = False
        form = DigitalEstateDocumentForm(data=d, user=self.user)
        self.assertFalse(form.is_valid())

    def test_single_declaration_incapacity_valid(self):
        d = self._data()
        d["applies_on_death"] = False
        d["applies_on_incapacity"] = True
        form = DigitalEstateDocumentForm(data=d, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)


class ImportantDocumentFormTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="imdfuser", email="imdf@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def _data(self, **overrides):
        d = {
            "delegated_important_document_to": self.contact.pk,
            "name_or_title": "Passport",
            "document_category": "Important Personal Documents",
            "review_time": 30,
            "applies_on_death": True,
        }
        d.update(overrides)
        return d

    def test_valid_important_doc_form(self):
        form = ImportantDocumentForm(data=self._data(), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_no_declaration_invalid(self):
        d = self._data()
        d["applies_on_death"] = False
        form = ImportantDocumentForm(data=d, user=self.user)
        self.assertFalse(form.is_valid())


class RelevanceReviewFormTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="rrfuser", email="rrf@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.account = make_account(self.profile, self.contact)
        self.device = make_device(self.profile, self.contact)

    def _future(self, days=30):
        return (date.today() + timedelta(days=days)).isoformat()

    def test_valid_review_form(self):
        form = RelevanceReviewForm(
            data={
                "account_review": self.account.pk,
                "matters": True,
                "next_review_due": self._future(),
            },
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_past_next_review_due_rejected(self):
        past = (date.today() - timedelta(days=1)).isoformat()
        form = RelevanceReviewForm(
            data={"account_review": self.account.pk, "matters": True, "next_review_due": past},
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("next_review_due", form.errors)

    def test_today_next_review_due_rejected(self):
        form = RelevanceReviewForm(
            data={
                "account_review": self.account.pk,
                "matters": True,
                "next_review_due": date.today().isoformat(),
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_multiple_targets_rejected(self):
        form = RelevanceReviewForm(
            data={
                "account_review": self.account.pk,
                "device_review": self.device.pk,
                "matters": True,
                "next_review_due": self._future(),
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_no_target_rejected(self):
        form = RelevanceReviewForm(
            data={"matters": True, "next_review_due": self._future()},
            user=self.user,
        )
        self.assertFalse(form.is_valid())


class FuneralPlanPersonalInfoFormTests(TestCase):

    def test_veteran_branch_required_if_is_veteran(self):
        form = FuneralPlanPersonalInfoForm(
            data={"is_veteran": True, "veteran_branch": ""},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("veteran_branch", form.errors)

    def test_veteran_branch_not_required_if_not_veteran(self):
        form = FuneralPlanPersonalInfoForm(
            data={"is_veteran": False, "veteran_branch": ""},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_veteran_with_branch(self):
        form = FuneralPlanPersonalInfoForm(
            data={"is_veteran": True, "veteran_branch": "Army"},
        )
        self.assertTrue(form.is_valid(), form.errors)


class FuneralPlanServiceFormTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="fpsfuser", email="fps@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_both_officiant_fields_raises_error(self):
        form = FuneralPlanServiceForm(
            data={
                "officiant_contact": self.contact.pk,
                "officiant_name_freetext": "Rev. Jones",
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("officiant_name_freetext", form.errors)

    def test_only_freetext_officiant_valid(self):
        form = FuneralPlanServiceForm(
            data={"officiant_name_freetext": "Rev. Jones"},
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)


class FuneralPlanReceptionFormTests(TestCase):

    def test_reception_desired_requires_location(self):
        form = FuneralPlanReceptionForm(
            data={"reception_desired": True, "reception_location": ""},
        )
        self.assertFalse(form.is_valid())

    def test_reception_desired_with_location_valid(self):
        form = FuneralPlanReceptionForm(
            data={"reception_desired": True, "reception_location": "The Grand Ballroom"},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_no_reception_no_location_valid(self):
        form = FuneralPlanReceptionForm(
            data={"reception_desired": False, "reception_location": ""},
        )
        self.assertTrue(form.is_valid(), form.errors)


class FuneralPlanAdminFormTests(TestCase):

    def test_zero_certificates_rejected(self):
        form = FuneralPlanAdminForm(data={"death_certificates_requested": 0})
        self.assertFalse(form.is_valid())

    def test_positive_certificates_accepted(self):
        form = FuneralPlanAdminForm(data={"death_certificates_requested": 8, "review_time": 365})
        self.assertTrue(form.is_valid(), form.errors)

    def test_blank_certificates_accepted(self):
        form = FuneralPlanAdminForm(data={"death_certificates_requested": None, "review_time": 365})
        self.assertTrue(form.is_valid(), form.errors)


# ============================================================================
# 13. DASHBOARD HOME VIEW TESTS
# ============================================================================

class DashboardHomeViewTests(TestCase):

    def setUp(self):
        self.url = reverse("dashboard:dashboard_home")

    def test_unauthenticated_redirects_to_login(self):
        r = self.client.get(self.url)
        self.assertRedirects(r, f"/accounts/login/?next={self.url}", fetch_redirect_response=False)

    def test_unpaid_user_redirects_to_payment(self):
        user = UserFactory.create_unpaid(username="dh_unpaid", email="dh_unpaid@x.com")
        self.client.force_login(user)
        r = self.client.get(self.url)
        self.assertRedirects(r, reverse("accounts:payment"), fetch_redirect_response=False)

    def test_paid_user_without_profile_redirects_to_profile_create(self):
        user = UserFactory.create_legacy(username="dh_noprofile", email="dh_np@x.com")
        self.client.force_login(user)
        r = self.client.get(self.url)
        self.assertRedirects(r, reverse("dashboard:profile_create"), fetch_redirect_response=False)

    def test_paid_user_with_profile_sees_dashboard(self):
        user = UserFactory.create_legacy(username="dh_full", email="dh_full@x.com")
        make_profile(user)
        self.client.force_login(user)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertIn("profile", r.context)

    def test_dashboard_context_contains_counts(self):
        user = UserFactory.create_legacy(username="dh_ctx", email="dh_ctx@x.com")
        make_profile(user)
        self.client.force_login(user)
        r = self.client.get(self.url)
        for key in ("accounts_count", "devices_count", "contacts_count"):
            self.assertIn(key, r.context)

    def test_dashboard_context_progress_is_integer(self):
        user = UserFactory.create_legacy(username="dh_prog", email="dh_prog@x.com")
        make_profile(user)
        self.client.force_login(user)
        r = self.client.get(self.url)
        progress = r.context["progress"]
        self.assertIsInstance(progress, int)
        self.assertGreaterEqual(progress, 0)
        self.assertLessEqual(progress, 100)

    def test_dashboard_can_modify_true_for_legacy(self):
        user = UserFactory.create_legacy(username="dh_mod", email="dh_mod@x.com")
        make_profile(user)
        self.client.force_login(user)
        r = self.client.get(self.url)
        self.assertTrue(r.context["can_modify"])

    def test_dashboard_can_modify_false_for_expired_essentials(self):
        user = UserFactory.create_expired_essentials(username="dh_exp", email="dh_exp@x.com")
        make_profile(user)
        self.client.force_login(user)
        r = self.client.get(self.url)
        self.assertFalse(r.context["can_modify"])


# ============================================================================
# 14. PROFILE VIEW TESTS
# ============================================================================

class ProfileViewTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="pv_user", email="pv@x.com")
        self.client.force_login(self.user)

    def test_profile_create_renders_for_new_user(self):
        r = self.client.get(reverse("dashboard:profile_create"))
        self.assertEqual(r.status_code, 200)

    def test_profile_create_redirects_if_profile_exists(self):
        make_profile(self.user)
        r = self.client.get(reverse("dashboard:profile_create"))
        self.assertIn(r.status_code, [301, 302])

    def test_profile_create_post_creates_profile(self):
        self.client.post(reverse("dashboard:profile_create"), {
            "first_name": "New",
            "last_name": "User",
            "address_1": "1 St",
            "city": "Town",
            "state": "IL",
        })
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_profile_detail_renders(self):
        make_profile(self.user)
        r = self.client.get(reverse("dashboard:profile_detail", kwargs={"pk": 1}))
        self.assertEqual(r.status_code, 200)

    def test_profile_update_renders(self):
        make_profile(self.user)
        r = self.client.get(reverse("dashboard:profile_update"))
        self.assertEqual(r.status_code, 200)

    def test_expired_essentials_cannot_update_profile(self):
        exp_user = UserFactory.create_expired_essentials(username="exp_pv", email="exp_pv@x.com")
        make_profile(exp_user)
        self.client.force_login(exp_user)
        r = self.client.get(reverse("dashboard:profile_update"))
        self.assertIn(r.status_code, [302, 403])

    def test_unpaid_user_redirected_from_profile_create(self):
        unpaid = UserFactory.create_unpaid(username="up_pv", email="up_pv@x.com")
        self.client.force_login(unpaid)
        r = self.client.get(reverse("dashboard:profile_create"))
        self.assertRedirects(r, reverse("accounts:payment"), fetch_redirect_response=False)


# ============================================================================
# 15. ACCOUNT CRUD VIEW TESTS
# ============================================================================

class AccountViewTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="av_user", email="av@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.account = make_account(self.profile, self.contact)
        self.client.force_login(self.user)

    def test_account_list_renders(self):
        r = self.client.get(reverse("dashboard:account_list"))
        self.assertEqual(r.status_code, 200)

    def test_account_detail_renders(self):
        r = self.client.get(reverse("dashboard:account_detail", kwargs={"pk": self.account.pk}))
        self.assertEqual(r.status_code, 200)

    def test_account_create_renders(self):
        r = self.client.get(reverse("dashboard:account_create"))
        self.assertEqual(r.status_code, 200)

    def test_account_create_post_creates_object(self):
        before = Account.objects.count()
        self.client.post(reverse("dashboard:account_create"), {
            "delegated_account_to": self.contact.pk,
            "account_category": "Email Account",
            "account_name_or_provider": "Yahoo Mail",
            "review_time": 30,
            "keep_or_close_instruction": "Close Account",
        })
        self.assertGreater(Account.objects.count(), before)

    def test_account_update_renders(self):
        r = self.client.get(reverse("dashboard:account_update", kwargs={"pk": self.account.pk}))
        self.assertEqual(r.status_code, 200)

    def test_account_delete_renders(self):
        r = self.client.get(reverse("dashboard:account_delete", kwargs={"pk": self.account.pk}))
        self.assertEqual(r.status_code, 200)

    def test_other_user_gets_404_for_account_detail(self):
        other = UserFactory.create_legacy(username="av_other", email="av_other@x.com")
        self.client.force_login(other)
        r = self.client.get(reverse("dashboard:account_detail", kwargs={"pk": self.account.pk}))
        self.assertEqual(r.status_code, 404)

    def test_unpaid_user_cannot_create_account(self):
        unpaid = UserFactory.create_unpaid(username="av_unpaid", email="av_unpaid@x.com")
        self.client.force_login(unpaid)
        r = self.client.get(reverse("dashboard:account_create"))
        self.assertIn(r.status_code, [302, 403])


# ============================================================================
# 16. DEVICE CRUD VIEW TESTS
# ============================================================================

class DeviceViewTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="dv_user", email="dv@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.device = make_device(self.profile, self.contact)
        self.client.force_login(self.user)

    def test_device_list_renders(self):
        r = self.client.get(reverse("dashboard:device_list"))
        self.assertEqual(r.status_code, 200)

    def test_device_detail_renders(self):
        r = self.client.get(reverse("dashboard:device_detail", kwargs={"pk": self.device.pk}))
        self.assertEqual(r.status_code, 200)

    def test_device_create_renders(self):
        r = self.client.get(reverse("dashboard:device_create"))
        self.assertEqual(r.status_code, 200)

    def test_device_create_post(self):
        before = Device.objects.count()
        self.client.post(reverse("dashboard:device_create"), {
            "delegated_device_to": self.contact.pk,
            "device_type": "Laptop",
            "device_name": "MacBook Pro",
            "review_time": 90,
        })
        self.assertGreater(Device.objects.count(), before)

    def test_other_user_gets_404(self):
        other = UserFactory.create_legacy(username="dv_other", email="dv_other@x.com")
        self.client.force_login(other)
        r = self.client.get(reverse("dashboard:device_detail", kwargs={"pk": self.device.pk}))
        self.assertEqual(r.status_code, 404)


# ============================================================================
# 17. CONTACT CRUD VIEW TESTS
# ============================================================================

class ContactViewTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="cv_user", email="cv@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.client.force_login(self.user)

    def test_contact_list_renders(self):
        r = self.client.get(reverse("dashboard:contact_list"))
        self.assertEqual(r.status_code, 200)

    def test_contact_detail_renders(self):
        r = self.client.get(reverse("dashboard:contact_detail", kwargs={"pk": self.contact.pk}))
        self.assertEqual(r.status_code, 200)

    def test_contact_detail_includes_delegated_context(self):
        make_account(self.profile, self.contact)
        r = self.client.get(reverse("dashboard:contact_detail", kwargs={"pk": self.contact.pk}))
        self.assertIn("delegated_accounts", r.context)
        self.assertIn("total_assignments", r.context)

    def test_contact_create_post_creates_object(self):
        before = Contact.objects.filter(profile=self.profile).count()
        self.client.post(reverse("dashboard:contact_create"), {
            "first_name": "Mary",
            "last_name": "Jane",
            "contact_relation": "Sister",
            "address_1": "9 Pine St",
            "city": "Shelby",
            "state": "IL",
            "is_emergency_contact": True,
        })
        self.assertGreater(Contact.objects.filter(profile=self.profile).count(), before)

    def test_cannot_delete_contact_with_assignments(self):
        make_account(self.profile, self.contact)
        r = self.client.post(reverse("dashboard:contact_delete", kwargs={"pk": self.contact.pk}))
        # Should redirect to contact detail, contact should still exist
        self.assertRedirects(
            r,
            reverse("dashboard:contact_detail", kwargs={"pk": self.contact.pk}),
            fetch_redirect_response=False,
        )
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())

    def test_other_user_gets_404_for_contact_detail(self):
        other = UserFactory.create_legacy(username="cv_other", email="cv_other@x.com")
        self.client.force_login(other)
        r = self.client.get(reverse("dashboard:contact_detail", kwargs={"pk": self.contact.pk}))
        self.assertEqual(r.status_code, 404)


# ============================================================================
# 18. ESTATE DOCUMENT VIEW TESTS
# ============================================================================

class EstateDocumentViewTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="ev_user", email="ev@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.doc = make_estate_doc(self.profile, self.contact)
        self.client.force_login(self.user)

    def test_estate_list_renders(self):
        r = self.client.get(reverse("dashboard:estate_list"))
        self.assertEqual(r.status_code, 200)

    def test_estate_detail_renders(self):
        r = self.client.get(reverse("dashboard:estate_detail", kwargs={"pk": self.doc.pk}))
        self.assertEqual(r.status_code, 200)

    def test_estate_create_renders(self):
        r = self.client.get(reverse("dashboard:estate_create"))
        self.assertEqual(r.status_code, 200)

    def test_estate_create_post(self):
        before = DigitalEstateDocument.objects.count()
        self.client.post(reverse("dashboard:estate_create"), {
            "delegated_estate_to": self.contact.pk,
            "estate_category": "Advance Directive / Living Will",
            "name_or_title": "Power of Attorney",
            "review_time": 365,
            "applies_on_incapacity": True,
        })
        self.assertGreater(DigitalEstateDocument.objects.count(), before)

    def test_other_user_gets_404(self):
        other = UserFactory.create_legacy(username="ev_other", email="ev_other@x.com")
        self.client.force_login(other)
        r = self.client.get(reverse("dashboard:estate_detail", kwargs={"pk": self.doc.pk}))
        self.assertEqual(r.status_code, 404)


# ============================================================================
# 19. IMPORTANT DOCUMENT VIEW TESTS
# ============================================================================

class ImportantDocumentViewTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="idv_user", email="idv@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.doc = make_important_doc(self.profile, self.contact)
        self.client.force_login(self.user)

    def test_list_renders(self):
        r = self.client.get(reverse("dashboard:importantdocument_list"))
        self.assertEqual(r.status_code, 200)

    def test_detail_renders(self):
        r = self.client.get(reverse("dashboard:importantdocument_detail", kwargs={"pk": self.doc.pk}))
        self.assertEqual(r.status_code, 200)

    def test_create_post(self):
        before = ImportantDocument.objects.count()
        self.client.post(reverse("dashboard:importantdocument_create"), {
            "delegated_important_document_to": self.contact.pk,
            "name_or_title": "Passport",
            "document_category": "Important Personal Documents",
            "review_time": 365,
            "applies_immediately": True,
        })
        self.assertGreater(ImportantDocument.objects.count(), before)

    def test_other_user_gets_404(self):
        other = UserFactory.create_legacy(username="idv_other", email="idv_other@x.com")
        self.client.force_login(other)
        r = self.client.get(reverse("dashboard:importantdocument_detail", kwargs={"pk": self.doc.pk}))
        self.assertEqual(r.status_code, 404)


# ============================================================================
# 20. FUNERAL PLAN VIEW TESTS
# ============================================================================

class FuneralPlanViewTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="fpv_user", email="fpv@x.com")
        self.profile = make_profile(self.user)
        self.client.force_login(self.user)

    def test_index_creates_plan_on_first_visit(self):
        self.assertFalse(FuneralPlan.objects.filter(profile=self.profile).exists())
        r = self.client.get(reverse("dashboard:funeralplan_index"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(FuneralPlan.objects.filter(profile=self.profile).exists())

    def test_index_shows_plan_in_context(self):
        r = self.client.get(reverse("dashboard:funeralplan_index"))
        self.assertIn("plan", r.context)

    def test_all_steps_render(self):
        self.client.get(reverse("dashboard:funeralplan_index"))  # create plan
        for i in range(1, 9):
            r = self.client.get(reverse(f"dashboard:funeralplan_step{i}"))
            self.assertEqual(r.status_code, 200, f"Step {i} failed")

    def test_step1_post_saves_preferred_name(self):
        self.client.get(reverse("dashboard:funeralplan_index"))
        self.client.post(reverse("dashboard:funeralplan_step1"), {
            "preferred_name": "Johnny",
            "is_veteran": False,
        })
        plan = FuneralPlan.objects.get(profile=self.profile)
        self.assertEqual(plan.preferred_name, "Johnny")

    def test_detail_view_renders(self):
        self.client.get(reverse("dashboard:funeralplan_index"))
        r = self.client.get(reverse("dashboard:funeralplan_detail"))
        self.assertEqual(r.status_code, 200)

    def test_unpaid_user_redirected_from_index(self):
        unpaid = UserFactory.create_unpaid(username="fp_unpaid", email="fp_unpaid@x.com")
        make_profile(unpaid)
        self.client.force_login(unpaid)
        r = self.client.get(reverse("dashboard:funeralplan_index"))
        self.assertRedirects(r, reverse("accounts:payment"), fetch_redirect_response=False)

    def test_delete_wrong_confirm_text_leaves_plan(self):
        self.client.get(reverse("dashboard:funeralplan_index"))
        self.client.post(reverse("dashboard:funeralplan_delete"), {"confirm_text": "delete"})
        self.assertTrue(FuneralPlan.objects.filter(profile=self.profile).exists())

    def test_delete_correct_confirm_removes_plan(self):
        self.client.get(reverse("dashboard:funeralplan_index"))
        self.client.post(reverse("dashboard:funeralplan_delete"), {"confirm_text": "DELETE"})
        self.assertFalse(FuneralPlan.objects.filter(profile=self.profile).exists())

    def test_step1_invalid_veteran_without_branch_fails(self):
        self.client.get(reverse("dashboard:funeralplan_index"))
        r = self.client.post(reverse("dashboard:funeralplan_step1"), {
            "is_veteran": True,
            "veteran_branch": "",
        })
        # Should re-render with errors, not redirect
        self.assertEqual(r.status_code, 200)

    def test_funeralplan_index_without_profile_redirects(self):
        no_profile = UserFactory.create_legacy(username="fp_noprof", email="fp_noprof@x.com")
        self.client.force_login(no_profile)
        r = self.client.get(reverse("dashboard:funeralplan_index"))
        self.assertRedirects(r, reverse("dashboard:profile_create"), fetch_redirect_response=False)


# ============================================================================
# 21. RELEVANCE REVIEW VIEW TESTS
# ============================================================================

class RelevanceReviewViewTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="rrv_user", email="rrv@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.account = make_account(self.profile, self.contact)
        self.review = RelevanceReview.objects.filter(account_review=self.account).first()
        self.client.force_login(self.user)

    def test_review_list_renders(self):
        r = self.client.get(reverse("dashboard:relevancereview_list"))
        self.assertEqual(r.status_code, 200)

    def test_review_detail_renders(self):
        r = self.client.get(reverse("dashboard:relevancereview_detail", kwargs={"pk": self.review.pk}))
        self.assertEqual(r.status_code, 200)

    def test_review_create_renders(self):
        r = self.client.get(reverse("dashboard:relevancereview_create"))
        self.assertEqual(r.status_code, 200)

    def test_review_create_post_creates_review(self):
        before = RelevanceReview.objects.count()
        future = (date.today() + timedelta(days=60)).isoformat()
        self.client.post(reverse("dashboard:relevancereview_create"), {
            "account_review": self.account.pk,
            "matters": True,
            "next_review_due": future,
        })
        self.assertGreater(RelevanceReview.objects.count(), before)

    def test_review_update_renders(self):
        r = self.client.get(reverse("dashboard:relevancereview_update", kwargs={"pk": self.review.pk}))
        self.assertEqual(r.status_code, 200)

    def test_other_user_cannot_access_review(self):
        other = UserFactory.create_legacy(username="rrv_other", email="rrv_other@x.com")
        other_profile = make_profile(other)
        self.client.force_login(other)
        r = self.client.get(reverse("dashboard:relevancereview_detail", kwargs={"pk": self.review.pk}))
        self.assertIn(r.status_code, [403, 404])

    def test_unpaid_user_redirected_from_review_list(self):
        unpaid = UserFactory.create_unpaid(username="rrv_unpaid", email="rrv_unpaid@x.com")
        self.client.force_login(unpaid)
        r = self.client.get(reverse("dashboard:relevancereview_list"))
        self.assertRedirects(r, reverse("accounts:payment"), fetch_redirect_response=False)

    def test_review_list_excludes_other_users_items(self):
        other = UserFactory.create_legacy(username="rrv_excl", email="rrv_excl@x.com")
        other_profile = make_profile(other)
        other_contact = make_contact(other_profile)
        make_account(other_profile, other_contact, account_name_or_provider="Other-Gmail")
        r = self.client.get(reverse("dashboard:relevancereview_list"))
        review_names = [rv.get_item_name() for rv in r.context["reviews"]]
        self.assertNotIn("Other-Gmail", review_names)

    def test_new_user_review_list_is_empty_without_items(self):
        fresh = UserFactory.create_legacy(username="rrv_fresh", email="rrv_fresh@x.com")
        make_profile(fresh)
        self.client.force_login(fresh)
        r = self.client.get(reverse("dashboard:relevancereview_list"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["reviews"].count(), 0)


# ============================================================================
# 22. MARK ITEM REVIEWED (AJAX) VIEW TESTS
# ============================================================================

class MarkItemReviewedViewTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="mir_user", email="mir@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.account = make_account(self.profile, self.contact)
        self.review = RelevanceReview.objects.filter(account_review=self.account).first()
        self.url = reverse("dashboard:mark_item_reviewed", kwargs={"review_pk": self.review.pk})
        self.client.force_login(self.user)

    def test_get_returns_405(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)
        data = json.loads(r.content)
        self.assertFalse(data["success"])

    def test_post_returns_200_with_success(self):
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data["success"])

    def test_post_updates_next_review_due(self):
        old_due = self.review.next_review_due
        self.client.post(self.url)
        self.review.refresh_from_db()
        self.assertNotEqual(self.review.next_review_due, old_due)

    def test_response_contains_required_keys(self):
        r = self.client.post(self.url)
        data = json.loads(r.content)
        for key in ("updated_at", "next_review_due", "message", "item_type", "item_name"):
            self.assertIn(key, data)

    def test_other_user_gets_403(self):
        other = UserFactory.create_legacy(username="mir_other", email="mir_other@x.com")
        make_profile(other)
        self.client.force_login(other)
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 403)
        data = json.loads(r.content)
        self.assertFalse(data["success"])

    def test_expired_essentials_gets_403(self):
        exp = UserFactory.create_expired_essentials(username="mir_exp", email="mir_exp@x.com")
        make_profile(exp)
        self.client.force_login(exp)
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 403)

    def test_nonexistent_review_pk_returns_404(self):
        bad_url = reverse("dashboard:mark_item_reviewed", kwargs={"review_pk": 99999})
        r = self.client.post(bad_url)
        self.assertEqual(r.status_code, 404)
        data = json.loads(r.content)
        self.assertFalse(data["success"])


# ============================================================================
# 23. ONBOARDING VIEW TESTS
# ============================================================================

class OnboardingViewTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="ob_user", email="ob@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.client.force_login(self.user)

    def test_welcome_renders(self):
        r = self.client.get(reverse("dashboard:onboarding_welcome"))
        self.assertEqual(r.status_code, 200)

    def test_welcome_context_has_progress(self):
        r = self.client.get(reverse("dashboard:onboarding_welcome"))
        self.assertIn("progress", r.context)

    def test_contacts_step_renders(self):
        r = self.client.get(reverse("dashboard:onboarding_contacts"))
        self.assertEqual(r.status_code, 200)

    def test_accounts_step_renders(self):
        r = self.client.get(reverse("dashboard:onboarding_accounts"))
        self.assertEqual(r.status_code, 200)

    def test_devices_step_renders(self):
        r = self.client.get(reverse("dashboard:onboarding_devices"))
        self.assertEqual(r.status_code, 200)

    def test_estate_step_renders(self):
        r = self.client.get(reverse("dashboard:onboarding_estate"))
        self.assertEqual(r.status_code, 200)

    def test_documents_step_renders(self):
        r = self.client.get(reverse("dashboard:onboarding_documents"))
        self.assertEqual(r.status_code, 200)

    def test_family_step_renders(self):
        r = self.client.get(reverse("dashboard:onboarding_family"))
        self.assertEqual(r.status_code, 200)

    def test_complete_step_renders(self):
        r = self.client.get(reverse("dashboard:onboarding_complete"))
        self.assertEqual(r.status_code, 200)

    def test_contacts_post_creates_contact(self):
        before = Contact.objects.filter(profile=self.profile).count()
        self.client.post(reverse("dashboard:onboarding_contacts"), {
            "first_name": "Carol",
            "last_name": "King",
            "contact_relation": "Daughter",
            "address_1": "100 Oak",
            "city": "Springfield",
            "state": "IL",
            "is_emergency_contact": True,
        })
        self.assertGreater(Contact.objects.filter(profile=self.profile).count(), before)

    def test_unpaid_redirected_from_onboarding(self):
        unpaid = UserFactory.create_unpaid(username="ob_unpaid", email="ob_unpaid@x.com")
        self.client.force_login(unpaid)
        r = self.client.get(reverse("dashboard:onboarding_welcome"))
        self.assertRedirects(r, reverse("accounts:payment"), fetch_redirect_response=False)


# ============================================================================
# 24. FAMILY AWARENESS VIEW TESTS
# ============================================================================

class FamilyAwarenessViewTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="fa_user", email="fa@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.client.force_login(self.user)

    def test_list_renders(self):
        r = self.client.get(reverse("dashboard:familyawareness_list"))
        self.assertEqual(r.status_code, 200)

    def test_create_post_creates_section(self):
        before = FamilyNeedsToKnowSection.objects.count()
        self.client.post(reverse("dashboard:familyawareness_create"), {
            "relation": self.contact.pk,
            "content": "Here is what you need to know.",
            "is_location_of_legal_will": True,
        })
        self.assertGreater(FamilyNeedsToKnowSection.objects.count(), before)

    def test_detail_renders(self):
        section = FamilyNeedsToKnowSection.objects.create(
            relation=self.contact,
            content="Important note",
            is_location_of_legal_will=True,
        )
        r = self.client.get(reverse("dashboard:familyawareness_detail", kwargs={"pk": section.pk}))
        self.assertEqual(r.status_code, 200)


# ============================================================================
# 25. DASHBOARD SIGNAL TESTS
# ============================================================================

class SignalTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create_legacy(username="sig_user", email="sig@x.com")
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_account_signal_sets_account_review_fk(self):
        account = make_account(self.profile, self.contact)
        review = RelevanceReview.objects.filter(account_review=account).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.account_review, account)

    def test_device_signal_sets_device_review_fk(self):
        device = make_device(self.profile, self.contact)
        review = RelevanceReview.objects.filter(device_review=device).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.device_review, device)

    def test_estate_signal_sets_estate_review_fk(self):
        doc = make_estate_doc(self.profile, self.contact)
        review = RelevanceReview.objects.filter(estate_review=doc).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.estate_review, doc)

    def test_important_doc_signal_sets_fk(self):
        doc = make_important_doc(self.profile, self.contact)
        review = RelevanceReview.objects.filter(important_document_review=doc).first()
        self.assertIsNotNone(review)

    def test_review_time_change_updates_next_due(self):
        account = make_account(self.profile, self.contact, review_time=30)
        account.review_time = 365
        account.save()
        review = RelevanceReview.objects.filter(account_review=account).latest("review_date")
        expected = date.today() + timedelta(days=365)
        self.assertEqual(review.next_review_due, expected)

    def test_profile_update_syncs_self_contact_name(self):
        self.profile.first_name = "Updated"
        self.profile.save()
        sc = Contact.objects.get(profile=self.profile, contact_relation="Self")
        self.assertEqual(sc.first_name, "Updated")


# ============================================================================
# 26. MIXIN PERMISSION LOGIC TESTS
# ============================================================================

class MixinPermissionLogicTests(TestCase):

    def test_legacy_can_modify(self):
        user = UserFactory.create_legacy(username="mx_leg", email="mx_leg@x.com")
        self.assertTrue(user.can_modify_data())

    def test_active_essentials_can_modify(self):
        user = UserFactory.create_essentials(username="mx_ess", email="mx_ess@x.com")
        self.assertTrue(user.can_modify_data())

    def test_expired_essentials_cannot_modify(self):
        user = UserFactory.create_expired_essentials(username="mx_exp", email="mx_exp@x.com")
        self.assertFalse(user.can_modify_data())

    def test_unpaid_cannot_modify(self):
        user = UserFactory.create_unpaid(username="mx_unp", email="mx_unp@x.com")
        self.assertFalse(user.can_modify_data())

    def test_legacy_can_view(self):
        user = UserFactory.create_legacy(username="mx_vleg", email="mx_vleg@x.com")
        self.assertTrue(user.can_view_data())

    def test_active_essentials_can_view(self):
        user = UserFactory.create_essentials(username="mx_vess", email="mx_vess@x.com")
        self.assertTrue(user.can_view_data())

    def test_expired_essentials_can_view(self):
        user = UserFactory.create_expired_essentials(username="mx_vexp", email="mx_vexp@x.com")
        self.assertTrue(user.can_view_data())

    def test_unpaid_cannot_view(self):
        user = UserFactory.create_unpaid(username="mx_vunp", email="mx_vunp@x.com")
        self.assertFalse(user.can_view_data())


# ============================================================================
# 27. OWNERSHIP ISOLATION TESTS
# ============================================================================

class OwnershipIsolationTests(TestCase):

    def setUp(self):
        # User A
        self.userA = UserFactory.create_legacy(username="oi_a", email="oi_a@x.com")
        self.profileA = make_profile(self.userA)
        self.contactA = make_contact(self.profileA)
        self.accountA = make_account(self.profileA, self.contactA)
        self.deviceA = make_device(self.profileA, self.contactA)
        self.estateA = make_estate_doc(self.profileA, self.contactA)
        self.iDocA = make_important_doc(self.profileA, self.contactA)

        # User B
        self.userB = UserFactory.create_legacy(username="oi_b", email="oi_b@x.com")
        self.profileB = make_profile(self.userB)
        self.contactB = make_contact(self.profileB)
        self.accountB = make_account(self.profileB, self.contactB, account_name_or_provider="B-Gmail")

        # Log in as User B
        self.client.force_login(self.userB)

    def test_user_b_cannot_see_user_a_account(self):
        r = self.client.get(reverse("dashboard:account_detail", kwargs={"pk": self.accountA.pk}))
        self.assertEqual(r.status_code, 404)

    def test_user_b_cannot_see_user_a_device(self):
        r = self.client.get(reverse("dashboard:device_detail", kwargs={"pk": self.deviceA.pk}))
        self.assertEqual(r.status_code, 404)

    def test_user_b_cannot_see_user_a_contact(self):
        r = self.client.get(reverse("dashboard:contact_detail", kwargs={"pk": self.contactA.pk}))
        self.assertEqual(r.status_code, 404)

    def test_user_b_cannot_see_user_a_estate_doc(self):
        r = self.client.get(reverse("dashboard:estate_detail", kwargs={"pk": self.estateA.pk}))
        self.assertEqual(r.status_code, 404)

    def test_user_b_cannot_see_user_a_important_doc(self):
        r = self.client.get(reverse("dashboard:importantdocument_detail", kwargs={"pk": self.iDocA.pk}))
        self.assertEqual(r.status_code, 404)

    def test_review_list_excludes_user_a_items(self):
        r = self.client.get(reverse("dashboard:relevancereview_list"))
        review_names = [rv.get_item_name() for rv in r.context["reviews"]]
        self.assertNotIn("Gmail", review_names)

    def test_user_b_cannot_update_user_a_account(self):
        r = self.client.post(
            reverse("dashboard:account_update", kwargs={"pk": self.accountA.pk}),
            {
                "delegated_account_to": self.contactA.pk,
                "account_category": "Email Account",
                "account_name_or_provider": "HACKED",
                "review_time": 30,
                "keep_or_close_instruction": "Keep Active",
            },
        )
        self.assertEqual(r.status_code, 404)
        self.accountA.refresh_from_db()
        self.assertNotEqual(self.accountA.account_name_or_provider, "HACKED")


# ============================================================================
# 28. EDGE CASES & REGRESSION TESTS
# ============================================================================

class EdgeCaseTests(TestCase):

    def test_profile_create_redirects_unpaid_user_to_payment(self):
        unpaid = UserFactory.create_unpaid(username="ec_unp", email="ec_unp@x.com")
        self.client.force_login(unpaid)
        r = self.client.get(reverse("dashboard:profile_create"))
        self.assertRedirects(r, reverse("accounts:payment"), fetch_redirect_response=False)

    def test_dashboard_without_profile_redirects_to_profile_create(self):
        user = UserFactory.create_legacy(username="ec_nop", email="ec_nop@x.com")
        self.client.force_login(user)
        r = self.client.get(reverse("dashboard:dashboard_home"))
        self.assertRedirects(r, reverse("dashboard:profile_create"), fetch_redirect_response=False)

    def test_account_form_no_profile_user_empty_queryset(self):
        user = UserFactory.create_legacy(username="ec_aq", email="ec_aq@x.com")
        form = AccountForm(user=user)
        self.assertEqual(form.fields["delegated_account_to"].queryset.count(), 0)

    def test_relevance_review_list_empty_for_new_user(self):
        fresh = UserFactory.create_legacy(username="ec_fresh", email="ec_fresh@x.com")
        make_profile(fresh)
        self.client.force_login(fresh)
        r = self.client.get(reverse("dashboard:relevancereview_list"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["reviews"].count(), 0)

    def test_mark_reviewed_invalid_pk_returns_404_json(self):
        user = UserFactory.create_legacy(username="ec_404", email="ec_404@x.com")
        make_profile(user)
        self.client.force_login(user)
        bad_url = reverse("dashboard:mark_item_reviewed", kwargs={"review_pk": 99999})
        r = self.client.post(bad_url)
        self.assertEqual(r.status_code, 404)
        data = json.loads(r.content)
        self.assertFalse(data["success"])

    def test_veteran_branch_required_when_veteran_true(self):
        form = FuneralPlanPersonalInfoForm(data={"is_veteran": True, "veteran_branch": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("veteran_branch", form.errors)

    def test_reception_location_required_when_reception_desired(self):
        form = FuneralPlanReceptionForm(data={"reception_desired": True, "reception_location": ""})
        self.assertFalse(form.is_valid())

    def test_death_certificates_must_be_positive(self):
        form = FuneralPlanAdminForm(data={"death_certificates_requested": 0, "review_time": 365})
        self.assertFalse(form.is_valid())

    def test_death_certificates_positive_accepted(self):
        form = FuneralPlanAdminForm(data={"death_certificates_requested": 6, "review_time": 365})
        self.assertTrue(form.is_valid(), form.errors)

    def test_multiple_items_each_get_own_review(self):
        user = UserFactory.create_legacy(username="ec_multi", email="ec_multi@x.com")
        profile = make_profile(user)
        contact = make_contact(profile)
        a1 = make_account(profile, contact, account_name_or_provider="Acc1")
        a2 = make_account(profile, contact, account_name_or_provider="Acc2")
        self.assertEqual(RelevanceReview.objects.filter(account_review__in=[a1, a2]).count(), 2)