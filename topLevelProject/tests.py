# tests.py  (project root — next to manage.py)
"""
Project-wide integration and smoke tests.

Covers every app in one place so you can quickly check whether the whole
site is alive after a change.  Granular unit/model tests live in each app:

    dashboard/tests.py           — models, signals, forms, views in depth
    accounts/tests_mixins.py     — mixin permission logic

Run ALL project tests:
    python manage.py test --verbosity=2

Run only this file:
    python manage.py test tests --verbosity=2

Run a single class:
    python manage.py test tests.PublicPageTests --verbosity=2
"""

from datetime import timedelta

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from dashboard.models import (
    Account,
    Contact,
    Device,
    DigitalEstateDocument,
    ImportantDocument,
    Profile,
)
from infrapps.models import VaultAccessLog, VaultEntry
from recovery.models import RecoveryRequest

User = get_user_model()

# ═══════════════════════════════════════════════════════════════════════════
#  SHARED HELPERS  (mirrors the fixtures in dashboard/tests.py)
# ═══════════════════════════════════════════════════════════════════════════

def make_user(username="tuser", email="tuser@example.com",
              password="StrongPass1!", **kw):
    return User.objects.create_user(
        username=username, email=email, password=password, **kw
    )


def make_stripe_user(username="leg", email="leg@example.com", tier='legacy'):
    u = make_user(username=username, email=email)
    u.subscription_tier = tier
    u.stripe_subscription_id = 'sub_test'
    u.subscription_status = 'active'
    u.has_paid = True
    u.payment_date = timezone.now()
    u.save()
    return u


def make_profile(user, **kw):
    defaults = dict(
        first_name="Jane", last_name="Doe",
        address_1="123 Main St", city="Des Moines",
        state="IA", zipcode=50309,
        email="jane@example.com", phone="515-555-1234",
    )
    defaults.update(kw)
    return Profile.objects.create(user=user, **defaults)


def make_contact(profile, **kw):
    defaults = dict(first_name="Bob", last_name="Smith",
                    contact_relation="Friend")
    defaults.update(kw)
    return Contact.objects.create(profile=profile, **defaults)


def make_account(profile, contact, **kw):
    defaults = dict(
        account_name_or_provider="Gmail",
        account_category="email",
        username_or_email="jane@gmail.com",
        delegated_account_to=contact,
        keep_or_close_instruction="close",
    )
    defaults.update(kw)
    return Account.objects.create(profile=profile, **defaults)


def make_device(profile, contact, **kw):
    defaults = dict(
        device_type="Laptop",
        device_name="My MacBook",
        delegated_device_to=contact,
    )
    defaults.update(kw)
    return Device.objects.create(profile=profile, **defaults)


def make_estate_doc(profile, contact, **kw):
    defaults = dict(
        name_or_title="Last Will and Testament",
        estate_category="will_testament",
        delegated_estate_to=contact,
    )
    defaults.update(kw)
    return DigitalEstateDocument.objects.create(profile=profile, **defaults)


def make_important_doc(profile, contact, **kw):
    defaults = dict(
        name_or_title="Birth Certificate",
        document_category="birth_certificate",
        delegated_important_document_to=contact,
    )
    defaults.update(kw)
    return ImportantDocument.objects.create(profile=profile, **defaults)


# ───────────────────────────────────────────────────────────────────────────
#  Vault helper — needs an encryption key injected via override_settings
# ───────────────────────────────────────────────────────────────────────────

TEST_FERNET_KEY = Fernet.generate_key().decode()


def make_vault_user():
    """User with a paid subscription AND an active add-on (vault access)."""
    u = make_stripe_user(username="vaultuser", email="vault@example.com")
    u.activate_addon()
    return u


# ═══════════════════════════════════════════════════════════════════════════
#  1. PUBLIC PAGE SMOKE TESTS
#     All of these should return 200 for an anonymous (not logged-in) visitor.
# ═══════════════════════════════════════════════════════════════════════════

class PublicPageTests(TestCase):
    """Every public URL must load without authentication."""

    def setUp(self):
        self.c = Client()

    # --- baseapp ---
    def test_home(self):
        r = self.c.get(reverse("baseapp_main:home"))
        self.assertEqual(r.status_code, 200)

    def test_privacy_policy(self):
        r = self.c.get(reverse("baseapp_main:privacy_policy"))
        self.assertEqual(r.status_code, 200)

    def test_terms_and_conditions(self):
        r = self.c.get(reverse("baseapp_main:terms_and_conditions"))
        self.assertEqual(r.status_code, 200)

    def test_cookie_policy(self):
        r = self.c.get(reverse("baseapp_main:cookie_policy"))
        self.assertEqual(r.status_code, 200)

    def test_data_collection(self):
        r = self.c.get(reverse("baseapp_main:data_collection"))
        self.assertEqual(r.status_code, 200)

    def test_data_retention(self):
        r = self.c.get(reverse("baseapp_main:data_retention"))
        self.assertEqual(r.status_code, 200)

    def test_accessibility(self):
        r = self.c.get(reverse("baseapp_main:accessibility"))
        self.assertEqual(r.status_code, 200)

    def test_checklist_download(self):
        r = self.c.get(reverse("baseapp_main:checklist_download"))
        # 200 (PDF served) or 404 if file missing in test env — both fine
        self.assertIn(r.status_code, [200, 404])

    # --- faqs ---
    def test_faqs_page(self):
        r = self.c.get(reverse("faqs_page:faqs"))
        self.assertEqual(r.status_code, 200)

    # --- accounts public ---
    def test_register_page(self):
        r = self.c.get(reverse("accounts:register"))
        self.assertEqual(r.status_code, 200)

    def test_login_page(self):
        r = self.c.get(reverse("accounts:login"))
        self.assertEqual(r.status_code, 200)

    def test_password_reset_page(self):
        r = self.c.get(reverse("accounts:password_reset"))
        self.assertEqual(r.status_code, 200)

    # --- recovery public ---
    def test_external_recovery_request_page(self):
        r = self.c.get(reverse("recovery:external_recovery_request"))
        self.assertEqual(r.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════
#  2. AUTHENTICATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class AuthenticationTests(TestCase):

    def setUp(self):
        self.c = Client()
        self.password = "StrongPass1!"
        self.user = make_user(username="authuser", email="auth@example.com",
                              password=self.password)

    def test_login_with_username(self):
        r = self.c.post(reverse("accounts:login"), {
            "username_or_email": "authuser",
            "password": self.password,
        }, follow=True)
        self.assertTrue(r.wsgi_request.user.is_authenticated)

    def test_login_with_email(self):
        """Custom EmailOrUsernameBackend allows login via email address."""
        r = self.c.post(reverse("accounts:login"), {
            "username_or_email": "auth@example.com",
            "password": self.password,
        }, follow=True)
        self.assertTrue(r.wsgi_request.user.is_authenticated)

    def test_login_wrong_password(self):
        r = self.c.post(reverse("accounts:login"), {
            "username": "authuser",
            "password": "WrongPass999!",
        }, follow=True)
        self.assertFalse(r.wsgi_request.user.is_authenticated)

    def test_logout(self):
        self.c.login(username="authuser", password=self.password)
        r = self.c.post(reverse("accounts:logout"), follow=True)
        self.assertFalse(r.wsgi_request.user.is_authenticated)

    def test_register_creates_user(self):
        before = User.objects.count()
        self.c.post(reverse("accounts:register"), {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "StrongNewPass1!",
            "password2": "StrongNewPass1!",
        })
        self.assertEqual(User.objects.count(), before + 1)

    def test_register_duplicate_email_rejected(self):
        before = User.objects.count()
        self.c.post(reverse("accounts:register"), {
            "username": "another",
            "email": "auth@example.com",   # already taken
            "password1": "StrongNewPass1!",
            "password2": "StrongNewPass1!",
        })
        self.assertEqual(User.objects.count(), before)

    def test_locked_account_cannot_login(self):
        self.user.account_locked_until = timezone.now() + timedelta(hours=1)
        self.user.save(update_fields=["account_locked_until"])
        r = self.c.post(reverse("accounts:login"), {
            "username": "authuser",
            "password": self.password,
        }, follow=True)
        self.assertFalse(r.wsgi_request.user.is_authenticated)


# ═══════════════════════════════════════════════════════════════════════════
#  3. SUBSCRIPTION TIER & ACCESS CONTROL
# ═══════════════════════════════════════════════════════════════════════════

class SubscriptionTierTests(TestCase):
    """
    Dashboard requires has_paid=True.  Redirect behaviour for unpaid users
    and access differences between tiers are tested here.
    """

    DASHBOARD_URL = reverse("dashboard_home:dashboard_home")

    def _login(self, user):
        self.c.force_login(user)

    def setUp(self):
        self.c = Client()

    def test_anonymous_redirected_from_dashboard(self):
        r = self.c.get(self.DASHBOARD_URL)
        self.assertIn(r.status_code, [302, 301])

    def test_unpaid_user_redirected_from_dashboard(self):
        u = make_user(username="unpaid", email="unpaid@example.com")
        self._login(u)
        r = self.c.get(self.DASHBOARD_URL, follow=True)
        # Should NOT land on the dashboard — redirect to payment or elsewhere
        self.assertNotEqual(r.request["PATH_INFO"], self.DASHBOARD_URL)

    def test_essentials_user_can_access_dashboard(self):
        u = make_stripe_user(username="e2", email="e2@example.com", tier='essentials')
        make_profile(u)
        self._login(u)
        r = self.c.get(self.DASHBOARD_URL)
        self.assertEqual(r.status_code, 200)

    def test_legacy_user_can_access_dashboard(self):
        u = make_stripe_user(username="l2", email="l2@example.com")
        make_profile(u)
        self._login(u)
        r = self.c.get(self.DASHBOARD_URL)
        self.assertEqual(r.status_code, 200)

    def test_essentials_can_modify_data(self):
        u = make_stripe_user(username="em", email="em@example.com", tier='essentials')
        self.assertTrue(u.can_modify_data())

    def test_lapsed_subscriber_cannot_modify(self):
        u = make_stripe_user(username="ex2", email="ex2@example.com")
        u.subscription_status = 'canceled'
        u.save()
        self.assertFalse(u.can_modify_data())

    def test_lapsed_subscriber_can_still_view(self):
        u = make_stripe_user(username="exv", email="exv@example.com")
        u.subscription_status = 'canceled'
        u.save()
        self.assertTrue(u.can_view_data())

    def test_legacy_can_modify_data(self):
        u = make_stripe_user(username="lm", email="lm@example.com")
        self.assertTrue(u.can_modify_data())

    def test_unpaid_cannot_view_data(self):
        u = make_user(username="nv", email="nv@example.com")
        self.assertFalse(u.can_view_data())


# ═══════════════════════════════════════════════════════════════════════════
#  4. DASHBOARD CORE
# ═══════════════════════════════════════════════════════════════════════════

class DashboardCoreTests(TestCase):
    """Dashboard home, profile create/view/edit."""

    def setUp(self):
        self.c = Client()
        self.user = make_stripe_user(username="core", email="core@example.com")
        self.c.force_login(self.user)

    def test_no_profile_redirects_to_profile_create(self):
        """User with payment but no Profile should be sent to profile create."""
        r = self.c.get(reverse("dashboard_home:dashboard_home"), follow=True)
        # Final URL should be profile_create
        self.assertEqual(r.request["PATH_INFO"],
                         reverse("dashboard_home:profile_create"))

    def test_profile_create_get(self):
        r = self.c.get(reverse("dashboard_home:profile_create"))
        self.assertEqual(r.status_code, 200)

    def test_profile_create_post(self):
        r = self.c.post(reverse("dashboard_home:profile_create"), {
            "first_name": "Jane",
            "last_name": "Doe",
            "address_1": "123 Main St",
            "city": "Des Moines",
            "state": "IA",
            "zipcode": 50309,
            "email": "jane@example.com",
            "phone": "515-555-1234",
        }, follow=True)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_dashboard_home_200_with_profile(self):
        make_profile(self.user)
        r = self.c.get(reverse("dashboard_home:dashboard_home"))
        self.assertEqual(r.status_code, 200)

    def test_profile_detail_200(self):
        make_profile(self.user)
        r = self.c.get(reverse("dashboard_home:profile_detail"))
        self.assertEqual(r.status_code, 200)

    def test_profile_update_200(self):
        make_profile(self.user)
        r = self.c.get(reverse("dashboard_home:profile_update"))
        self.assertEqual(r.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════
#  5. CONTACT CRUD
# ═══════════════════════════════════════════════════════════════════════════

class ContactCRUDTests(TestCase):

    def setUp(self):
        self.c = Client()
        self.user = make_stripe_user(username="ctct", email="ctct@example.com")
        self.c.force_login(self.user)
        self.profile = make_profile(self.user)

    def test_contact_list_200(self):
        r = self.c.get(reverse("dashboard_home:contact_list"))
        self.assertEqual(r.status_code, 200)

    def test_contact_create_get(self):
        r = self.c.get(reverse("dashboard_home:contact_create"))
        self.assertEqual(r.status_code, 200)

    def test_contact_create_post(self):
        before = Contact.objects.filter(profile=self.profile).count()
        self.c.post(reverse("dashboard_home:contact_create"), {
            "first_name": "Alice",
            "last_name": "Wonder",
            "contact_relation": "Other",
            "address_1": "111 Plain View",
            "city": "Des Moines",
            "state": "Iowa",
            "is_emergency_contact": True,
        })
        self.assertGreater(
            Contact.objects.filter(profile=self.profile).count(), before
        )

    def test_contact_detail_200(self):
        # Signal auto-creates a "Self" contact; grab it
        contact = Contact.objects.filter(profile=self.profile).first()
        r = self.c.get(reverse("dashboard_home:contact_detail",
                               kwargs={"slug": contact.slug}))
        self.assertEqual(r.status_code, 200)

    def test_contact_update_200(self):
        contact = Contact.objects.filter(profile=self.profile).first()
        r = self.c.get(reverse("dashboard_home:contact_update",
                               kwargs={"slug": contact.slug}))
        self.assertEqual(r.status_code, 200)

    def test_other_user_cannot_view_contact(self):
        """Ownership isolation: a second user gets 404 on the first user's slug."""
        other = make_stripe_user(username="other_c", email="other_c@example.com")
        other_profile = make_profile(other, email="other@example.com")
        contact = Contact.objects.filter(profile=self.profile).first()

        self.c.force_login(other)
        r = self.c.get(reverse("dashboard_home:contact_detail",
                               kwargs={"slug": contact.slug}))
        self.assertEqual(r.status_code, 404)


# ═══════════════════════════════════════════════════════════════════════════
#  6. ACCOUNT (digital account) CRUD
# ═══════════════════════════════════════════════════════════════════════════

class AccountCRUDTests(TestCase):

    def setUp(self):
        self.c = Client()
        self.user = make_stripe_user(username="acct", email="acct@example.com")
        self.c.force_login(self.user)
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_account_list_200(self):
        r = self.c.get(reverse("dashboard_home:account_list"))
        self.assertEqual(r.status_code, 200)

    def test_account_create_get(self):
        r = self.c.get(reverse("dashboard_home:account_create"))
        self.assertEqual(r.status_code, 200)

    def test_account_create_post(self):
        self.c.post(reverse("dashboard_home:account_create"), {
            "account_name_or_provider": "Gmail",
            "account_category": "Email Account",
            "username_or_email": "jane@gmail.com",
            "delegated_account_to": self.contact.pk,
            "keep_or_close_instruction": "Close Account",
            "review_time": 365,
        })
        self.assertTrue(
            Account.objects.filter(profile=self.profile,
                                   account_name_or_provider="Gmail").exists()
        )

    def test_account_detail_200(self):
        acct = make_account(self.profile, self.contact)
        r = self.c.get(reverse("dashboard_home:account_detail",
                               kwargs={"slug": acct.slug}))
        self.assertEqual(r.status_code, 200)

    def test_account_update_200(self):
        acct = make_account(self.profile, self.contact)
        r = self.c.get(reverse("dashboard_home:account_update",
                               kwargs={"slug": acct.slug}))
        self.assertEqual(r.status_code, 200)

    def test_account_ownership_isolation(self):
        other = make_stripe_user(username="other_a", email="other_a@example.com")
        other_profile = make_profile(other, email="oa@example.com")
        acct = make_account(self.profile, self.contact)

        self.c.force_login(other)
        r = self.c.get(reverse("dashboard_home:account_detail",
                               kwargs={"slug": acct.slug}))
        self.assertEqual(r.status_code, 404)


# ═══════════════════════════════════════════════════════════════════════════
#  7. DEVICE CRUD
# ═══════════════════════════════════════════════════════════════════════════

class DeviceCRUDTests(TestCase):

    def setUp(self):
        self.c = Client()
        self.user = make_stripe_user(username="dvc", email="dvc@example.com")
        self.c.force_login(self.user)
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_device_list_200(self):
        r = self.c.get(reverse("dashboard_home:device_list"))
        self.assertEqual(r.status_code, 200)

    def test_device_create_get(self):
        r = self.c.get(reverse("dashboard_home:device_create"))
        self.assertEqual(r.status_code, 200)

    def test_device_create_post(self):
        self.c.post(reverse("dashboard_home:device_create"), {
            "device_type": "Laptop",
            "device_name": "Work Laptop",
            "delegated_device_to": self.contact.pk,
            "review_time": 365,
        })
        self.assertTrue(
            Device.objects.filter(profile=self.profile,
                                  device_name="Work Laptop").exists()
        )

    def test_device_detail_200(self):
        dev = make_device(self.profile, self.contact)
        r = self.c.get(reverse("dashboard_home:device_detail",
                               kwargs={"slug": dev.slug}))
        self.assertEqual(r.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════
#  8. ESTATE & IMPORTANT DOCUMENTS CRUD
# ═══════════════════════════════════════════════════════════════════════════

class EstateDocumentCRUDTests(TestCase):

    def setUp(self):
        self.c = Client()
        self.user = make_stripe_user(username="estdoc", email="estdoc@example.com")
        self.c.force_login(self.user)
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_estate_list_200(self):
        r = self.c.get(reverse("dashboard_home:estate_list"))
        self.assertEqual(r.status_code, 200)

    def test_estate_create_get(self):
        r = self.c.get(reverse("dashboard_home:estate_create"))
        self.assertEqual(r.status_code, 200)

    def test_estate_detail_200(self):
        doc = make_estate_doc(self.profile, self.contact)
        r = self.c.get(reverse("dashboard_home:estate_detail",
                               kwargs={"slug": doc.slug}))
        self.assertEqual(r.status_code, 200)


class ImportantDocumentCRUDTests(TestCase):

    def setUp(self):
        self.c = Client()
        self.user = make_stripe_user(username="idoc", email="idoc@example.com")
        self.c.force_login(self.user)
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_important_document_list_200(self):
        r = self.c.get(reverse("dashboard_home:important_document_list"))
        self.assertEqual(r.status_code, 200)

    def test_important_document_create_get(self):
        r = self.c.get(reverse("dashboard_home:important_document_create"))
        self.assertEqual(r.status_code, 200)

    def test_important_document_detail_200(self):
        doc = make_important_doc(self.profile, self.contact)
        r = self.c.get(reverse("dashboard_home:important_document_detail",
                               kwargs={"slug": doc.slug}))
        self.assertEqual(r.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════
#  9. FUNERAL PLAN
# ═══════════════════════════════════════════════════════════════════════════

class FuneralPlanTests(TestCase):

    def setUp(self):
        self.c = Client()
        self.user = make_stripe_user(username="fun", email="fun@example.com")
        self.c.force_login(self.user)
        make_profile(self.user)

    def test_funeral_plan_index_200(self):
        r = self.c.get(reverse("dashboard_home:funeralplan_index"))
        self.assertEqual(r.status_code, 200)

    def test_funeral_plan_step1_200(self):
        r = self.c.get(reverse("dashboard_home:funeralplan_step1"))
        self.assertEqual(r.status_code, 200)

    def test_funeral_plan_step2_200(self):
        r = self.c.get(reverse("dashboard_home:funeralplan_step2"))
        self.assertEqual(r.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════
#  10. ONBOARDING
# ═══════════════════════════════════════════════════════════════════════════

class OnboardingTests(TestCase):

    def setUp(self):
        self.c = Client()
        self.user = make_stripe_user(username="onb", email="onb@example.com")
        self.c.force_login(self.user)
        make_profile(self.user)

    def test_onboarding_welcome_200(self):
        r = self.c.get(reverse("dashboard_home:onboarding_welcome"))
        self.assertEqual(r.status_code, 200)

    def test_onboarding_contacts_200(self):
        r = self.c.get(reverse("dashboard_home:onboarding_contacts"))
        self.assertEqual(r.status_code, 200)

    def test_onboarding_complete_200(self):
        r = self.c.get(reverse("dashboard_home:onboarding_complete"))
        self.assertEqual(r.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════
#  11. VAULT (infrapps) — requires encryption key + active add-on
# ═══════════════════════════════════════════════════════════════════════════

@override_settings(VAULT_ENCRYPTION_KEY=TEST_FERNET_KEY)
class VaultTests(TestCase):

    def setUp(self):
        self.c = Client()
        self.user = make_vault_user()
        self.c.force_login(self.user)
        self.profile = make_profile(self.user, email="vault@example.com")

    def test_vault_list_200(self):
        r = self.c.get(reverse("vault:vault_list"))
        self.assertEqual(r.status_code, 200)

    def test_vault_create_get(self):
        r = self.c.get(reverse("vault:vault_create"))
        self.assertEqual(r.status_code, 200)

    def test_vault_create_post(self):
        r = self.c.post(reverse("vault:vault_create"), {
            "label": "My Gmail Password",
            "entry_type": "other",
            "username_or_email": "jane@gmail.com",
            "raw_password": "SuperSecret99!",
            "notes": "",
        }, follow=True)
        self.assertTrue(
            VaultEntry.objects.filter(profile=self.profile,
                                      label="My Gmail Password").exists()
        )

    def test_vault_password_is_encrypted_at_rest(self):
        entry = VaultEntry(profile=self.profile, label="Test", entry_type="other")
        entry.set_password("PlainText123!")
        entry.save()
        # The raw DB value must not contain the plaintext
        raw = VaultEntry.objects.get(pk=entry.pk).encrypted_password
        self.assertNotIn("PlainText123!", raw)

    def test_vault_password_decrypts_correctly(self):
        entry = VaultEntry(profile=self.profile, label="DecryptTest", entry_type="other")
        entry.set_password("MySecret99!")
        entry.save()
        fetched = VaultEntry.objects.get(pk=entry.pk)
        self.assertEqual(fetched.get_password(), "MySecret99!")

    def test_vault_reveal_creates_access_log(self):
        entry = VaultEntry(profile=self.profile, label="LogTest", entry_type="other")
        entry.set_password("LogPass1!")
        entry.save()
        before = VaultAccessLog.objects.filter(entry=entry).count()
        self.c.post(reverse("vault:vault_reveal", kwargs={"slug": entry.slug}))
        self.assertGreater(
            VaultAccessLog.objects.filter(entry=entry).count(), before
        )

    def test_vault_detail_200(self):
        entry = VaultEntry(profile=self.profile, label="DetailTest", entry_type="other")
        entry.set_password("DetailPass1!")
        entry.save()
        r = self.c.get(reverse("vault:vault_detail", kwargs={"slug": entry.slug}))
        self.assertEqual(r.status_code, 200)

    def test_vault_requires_addon(self):
        """A user without an active add-on subscription cannot reach the vault."""
        no_addon = make_stripe_user(username="noaddon", email="noaddon@example.com")
        make_profile(no_addon, email="noaddon@example.com")
        self.c.force_login(no_addon)
        r = self.c.get(reverse("vault:vault_list"))
        # Should redirect away (403 or 302)
        self.assertIn(r.status_code, [302, 403])


# ═══════════════════════════════════════════════════════════════════════════
#  12. RECOVERY FLOW
# ═══════════════════════════════════════════════════════════════════════════

class RecoveryPublicFlowTests(TestCase):
    """
    Tests the external recovery journey:
      anonymous visitor submits a request → receives verification token →
      verifies it → checks status page.
    """

    def setUp(self):
        self.c = Client()
        # Create a target user whose estate data is being requested
        self.target_user = make_stripe_user(username="target", email="target@example.com")
        self.target_profile = make_profile(self.target_user,
                                           email="target@example.com")

    def test_external_request_form_loads(self):
        r = self.c.get(reverse("recovery:external_recovery_request"))
        self.assertEqual(r.status_code, 200)

    def test_external_request_creates_record(self):
        before = RecoveryRequest.objects.count()
        self.c.post(reverse("recovery:external_recovery_request"), {
            "deceased_user_email": "target@example.com",
            "requester_first_name": "Family",
            "requester_last_name": "Member",
            "requester_email": "family@example.com",
            "requester_phone": "515-555-9999",
            "requester_relationship": "Spouse",
            "reason": "Death",
            "target_description": "Need access to banking details.",
            "accept_terms": True,
        })
        self.assertGreater(RecoveryRequest.objects.count(), before)

    def test_verify_token_marks_request_verified(self):
        req = RecoveryRequest.objects.create(
            profile=self.target_profile,
            requester_first_name="Family",
            requester_last_name="Member",
            requester_email="family@example.com",
            requester_relationship="Spouse",
            reason="Death",
            target_description="Test",
        )
        req.generate_verification_token()
        req.save()
        token = req.verification_token
        self.c.get(reverse("recovery:verify_recovery_request",
                           kwargs={"token": token}))
        req.refresh_from_db()
        self.assertTrue(req.is_verified())

    def test_invalid_token_does_not_crash(self):
        r = self.c.get(reverse("recovery:verify_recovery_request",
                               kwargs={"token": "invalid-token-xyz"}))
        # Should return a graceful error page, not a 500
        self.assertIn(r.status_code, [200, 302, 404])

    def test_status_page_200(self):
        req = RecoveryRequest.objects.create(
            profile=self.target_profile,
            requester_first_name="Family",
            requester_last_name="Member",
            requester_email="family@example.com",
            requester_relationship="Spouse",
            reason="Death",
            target_description="Test",
        )
        r = self.c.get(reverse("recovery:recovery_request_status",
                               kwargs={"pk": req.pk}) + "?verified=true")
        self.assertEqual(r.status_code, 200)


class RecoveryAuthenticatedFlowTests(TestCase):
    """Authenticated user submitting a recovery request for another profile."""

    def setUp(self):
        self.c = Client()
        self.requester = make_stripe_user(username="requser", email="req@example.com")
        self.c.force_login(self.requester)
        self.target_user = make_stripe_user(username="tgt2", email="tgt2@example.com")
        self.target_profile = make_profile(self.target_user,
                                           email="tgt2@example.com")

    def test_authenticated_request_form_loads(self):
        r = self.c.get(reverse("recovery:authenticated_recovery_request",
                               kwargs={"profile_id": self.target_profile.pk}))
        self.assertEqual(r.status_code, 200)

    def test_my_requests_list_200(self):
        r = self.c.get(reverse("recovery:my_recovery_requests"))
        self.assertEqual(r.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════
#  13. SIGNALS SMOKE TEST
#     Signals are tested in depth in dashboard/tests.py; these are
#     quick sanity checks at the integration level.
# ═══════════════════════════════════════════════════════════════════════════

class SignalSmokeTests(TestCase):

    def test_self_contact_created_on_profile_save(self):
        """Creating a Profile should auto-create a 'Self' contact via signal."""
        user = make_stripe_user(username="sig", email="sig@example.com")
        profile = make_profile(user)
        self.assertTrue(
            Contact.objects.filter(profile=profile, first_name=user.username).exists()
            or Contact.objects.filter(profile=profile).exists()
        )

    def test_account_creation_creates_relevance_review(self):
        from dashboard.models import RelevanceReview
        user = make_stripe_user(username="sig2", email="sig2@example.com")
        profile = make_profile(user)
        contact = make_contact(profile)
        acct = make_account(profile, contact)
        self.assertTrue(
            RelevanceReview.objects.filter(account_review=acct).exists()
        )

    def test_device_creation_creates_relevance_review(self):
        from dashboard.models import RelevanceReview
        user = make_stripe_user(username="sig3", email="sig3@example.com")
        profile = make_profile(user)
        contact = make_contact(profile)
        dev = make_device(profile, contact)
        self.assertTrue(
            RelevanceReview.objects.filter(device_review=dev).exists()
        )
