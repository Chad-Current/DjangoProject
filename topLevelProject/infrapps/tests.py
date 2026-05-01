import json

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Account, Contact, Device, Profile

User = get_user_model()

# Generate a fresh test key at import time — used across all test classes.
TEST_FERNET_KEY = Fernet.generate_key().decode()


# ═══════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ═══════════════════════════════════════════════════════════════

def make_user(username='vault_user', email='vault@x.com', password='StrongPass1!', **kw):
    return User.objects.create_user(username=username, email=email, password=password, **kw)


def make_legacy(username='vault_leg', email='vaultleg@x.com'):
    u = make_user(username=username, email=email)
    u.subscription_tier = 'legacy'
    u.stripe_subscription_id = 'sub_vault'
    u.subscription_status = 'active'
    u.has_paid = True
    u.payment_date = timezone.now()
    u.save()
    return u


def make_profile(user, **kw):
    defaults = dict(
        first_name='Vault', last_name='User',
        address_1='1 Vault St', city='Ames', state='IA', zipcode=50010,
    )
    defaults.update(kw)
    return Profile.objects.get_or_create(user=user, defaults=defaults)[0]


def make_account(profile, **kw):
    contact, _ = Contact.objects.get_or_create(
        profile=profile,
        contact_relation='Self',
        defaults={'first_name': 'Self', 'last_name': 'Contact',
                  'address_1': '1 St', 'city': 'Ames', 'state': 'IA'},
    )
    defaults = dict(
        account_name_or_provider='TestBank',
        account_category='Email Account',
        delegated_account_to=contact,
        review_time=30,
    )
    defaults.update(kw)
    return Account.objects.create(profile=profile, **defaults)


def make_vault_entry(profile, account, plaintext='secret'):
    from infrapps.models import VaultEntry
    entry = VaultEntry(profile=profile, linked_account=account)
    entry.set_password(plaintext)
    entry.save()
    return entry


# ═══════════════════════════════════════════════════════════════
#  ENCRYPTION HELPER TESTS
# ═══════════════════════════════════════════════════════════════

@override_settings(VAULT_ENCRYPTION_KEY=TEST_FERNET_KEY)
class EncryptionHelperTest(TestCase):

    def test_encrypt_returns_non_empty_string(self):
        from infrapps.models import encrypt_password
        token = encrypt_password('my_secret')
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)

    def test_encrypt_empty_string_returns_empty(self):
        from infrapps.models import encrypt_password
        self.assertEqual(encrypt_password(''), '')

    def test_decrypt_returns_original_plaintext(self):
        from infrapps.models import encrypt_password, decrypt_password
        original = 'super_secret_123!'
        token = encrypt_password(original)
        self.assertEqual(decrypt_password(token), original)

    def test_decrypt_empty_token_returns_empty(self):
        from infrapps.models import decrypt_password
        self.assertEqual(decrypt_password(''), '')

    def test_decrypt_invalid_token_returns_decryption_error(self):
        from infrapps.models import decrypt_password
        self.assertEqual(decrypt_password('not_a_valid_token'), '[decryption error]')

    def test_roundtrip_preserves_special_characters(self):
        from infrapps.models import encrypt_password, decrypt_password
        original = 'P@$$w0rd! #&*()_+-=[]{}|;:,.<>?'
        self.assertEqual(decrypt_password(encrypt_password(original)), original)

    def test_fernet_key_missing_raises_improperly_configured(self):
        from django.core.exceptions import ImproperlyConfigured
        with self.settings(VAULT_ENCRYPTION_KEY=None):
            from infrapps import models as vault_models
            with self.assertRaises(ImproperlyConfigured):
                vault_models._get_fernet()


# ═══════════════════════════════════════════════════════════════
#  VaultEntry MODEL TESTS
# ═══════════════════════════════════════════════════════════════

@override_settings(VAULT_ENCRYPTION_KEY=TEST_FERNET_KEY)
class VaultEntryModelTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.account = make_account(self.profile)
        self.entry = make_vault_entry(self.profile, self.account, 'TestPassword1!')

    def test_set_and_get_password_roundtrip(self):
        result = self.entry.get_password()
        self.assertEqual(result, 'TestPassword1!')

    def test_get_password_updates_last_accessed(self):
        self.assertIsNone(self.entry.last_accessed)
        self.entry.get_password()
        self.entry.refresh_from_db()
        self.assertIsNotNone(self.entry.last_accessed)

    def test_clean_raises_when_both_linked(self):
        from infrapps.models import VaultEntry
        contact = Contact.objects.get(profile=self.profile, contact_relation='Self')
        device = Device.objects.create(
            profile=self.profile,
            device_name='iPhone',
            device_type='Phone',
            delegated_device_to=contact,
            review_time=30,
        )
        entry = VaultEntry(
            profile=self.profile,
            linked_account=self.account,
            linked_device=device,
            encrypted_password='fake',
        )
        with self.assertRaises(ValidationError):
            entry.clean()

    def test_clean_raises_when_neither_linked(self):
        from infrapps.models import VaultEntry
        entry = VaultEntry(profile=self.profile, encrypted_password='fake')
        with self.assertRaises(ValidationError):
            entry.clean()

    def test_save_auto_generates_slug(self):
        self.assertIsNotNone(self.entry.slug)
        self.assertGreater(len(self.entry.slug), 0)

    def test_slug_derived_from_account_name(self):
        self.assertIn('testbank', self.entry.slug.lower())

    def test_source_name_returns_account_name(self):
        self.assertEqual(self.entry.source_name, 'TestBank')

    def test_has_linked_source_true_when_account_set(self):
        self.assertTrue(self.entry.has_linked_source)

    def test_has_linked_source_false_when_neither_set(self):
        from infrapps.models import VaultEntry
        e = VaultEntry(profile=self.profile, encrypted_password='x')
        self.assertFalse(e.has_linked_source)

    def test_str_returns_source_name(self):
        self.assertEqual(str(self.entry), 'TestBank')


# ═══════════════════════════════════════════════════════════════
#  VaultAccessLog MODEL TESTS
# ═══════════════════════════════════════════════════════════════

@override_settings(VAULT_ENCRYPTION_KEY=TEST_FERNET_KEY)
class VaultAccessLogTest(TestCase):

    def setUp(self):
        from infrapps.models import VaultAccessLog
        self.VaultAccessLog = VaultAccessLog
        self.user = make_legacy(username='val_user', email='val@x.com')
        self.profile = make_profile(self.user)
        self.account = make_account(self.profile)
        self.entry = make_vault_entry(self.profile, self.account, 'Secret!')

    def test_access_log_can_be_created(self):
        count = self.VaultAccessLog.objects.count()
        self.VaultAccessLog.objects.create(
            entry=self.entry,
            accessed_by=self.user,
            ip_address='127.0.0.1',
        )
        self.assertEqual(self.VaultAccessLog.objects.count(), count + 1)

    def test_access_log_str_contains_entry_source_name(self):
        log = self.VaultAccessLog.objects.create(
            entry=self.entry,
            accessed_by=self.user,
            ip_address='127.0.0.1',
        )
        self.assertIn('TestBank', str(log))

    def test_access_log_str_contains_user(self):
        log = self.VaultAccessLog.objects.create(
            entry=self.entry,
            accessed_by=self.user,
        )
        self.assertIn(str(self.user), str(log))


# ═══════════════════════════════════════════════════════════════
#  VaultAccessMixin TESTS
# ═══════════════════════════════════════════════════════════════

@override_settings(VAULT_ENCRYPTION_KEY=TEST_FERNET_KEY)
class VaultAccessMixinTest(TestCase):

    def setUp(self):
        self.legacy = make_legacy()
        make_profile(self.legacy)

    def test_legacy_user_can_access_vault_list(self):
        self.client.force_login(self.legacy)
        response = self.client.get(reverse('vault:vault_list'))
        self.assertEqual(response.status_code, 200)

    def test_essentials_user_redirected_from_vault(self):
        ess = make_user(username='vault_ess', email='vaultess@x.com')
        ess.subscription_tier = 'essentials'
        ess.stripe_subscription_id = 'sub_ess'
        ess.subscription_status = 'active'
        ess.has_paid = True
        ess.save()
        make_profile(ess)
        self.client.force_login(ess)
        response = self.client.get(reverse('vault:vault_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('payment', response['Location'])

    def test_unauthenticated_redirected_to_login(self):
        response = self.client.get(reverse('vault:vault_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    def test_free_tier_user_redirected_from_vault(self):
        free = make_user(username='vault_free', email='vaultfree@x.com')
        make_profile(free)
        self.client.force_login(free)
        response = self.client.get(reverse('vault:vault_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('payment', response['Location'])


# ═══════════════════════════════════════════════════════════════
#  VaultRevealPasswordView TESTS
# ═══════════════════════════════════════════════════════════════

@override_settings(VAULT_ENCRYPTION_KEY=TEST_FERNET_KEY)
class VaultRevealPasswordViewTest(TestCase):

    def setUp(self):
        from infrapps.models import VaultAccessLog
        self.VaultAccessLog = VaultAccessLog
        self.user = make_legacy(username='reveal_user', email='reveal@x.com')
        self.profile = make_profile(self.user)
        self.account = make_account(self.profile)
        self.entry = make_vault_entry(self.profile, self.account, 'RevealMe!')
        self.client.force_login(self.user)
        self.reveal_url = reverse('vault:vault_reveal', kwargs={'slug': self.entry.slug})

    def test_get_returns_405(self):
        response = self.client.get(self.reveal_url)
        self.assertEqual(response.status_code, 405)

    def test_post_returns_decrypted_password(self):
        response = self.client.post(self.reveal_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['password'], 'RevealMe!')

    def test_post_creates_vault_access_log(self):
        count = self.VaultAccessLog.objects.count()
        self.client.post(self.reveal_url)
        self.assertEqual(self.VaultAccessLog.objects.count(), count + 1)
        log = self.VaultAccessLog.objects.latest('accessed_at')
        self.assertEqual(log.accessed_by, self.user)
        self.assertEqual(log.entry, self.entry)

    def test_non_owner_gets_404(self):
        other = make_legacy(username='reveal_other', email='revealother@x.com')
        make_profile(other)
        self.client.force_login(other)
        response = self.client.post(self.reveal_url)
        self.assertEqual(response.status_code, 404)

    def test_essentials_user_redirected_before_reveal(self):
        ess = make_user(username='reveal_ess', email='revealess@x.com')
        ess.subscription_tier = 'essentials'
        ess.stripe_subscription_id = 'sub_re'
        ess.subscription_status = 'active'
        ess.has_paid = True
        ess.save()
        make_profile(ess)
        self.client.force_login(ess)
        response = self.client.post(self.reveal_url)
        # VaultAccessMixin redirects non-legacy users before reaching post()
        self.assertEqual(response.status_code, 302)


# ═══════════════════════════════════════════════════════════════
#  GrantedVaultRevealView TESTS
# ═══════════════════════════════════════════════════════════════

@override_settings(VAULT_ENCRYPTION_KEY=TEST_FERNET_KEY)
class GrantedVaultRevealViewTest(TestCase):

    def setUp(self):
        from infrapps.models import VaultAccessLog
        from recovery.models import ProfileAccessGrant
        self.VaultAccessLog = VaultAccessLog
        self.ProfileAccessGrant = ProfileAccessGrant
        # Owner (legacy) has vault entry
        self.owner = make_legacy(username='gr_owner', email='growner@x.com')
        self.profile = make_profile(self.owner)
        self.account = make_account(self.profile)
        self.entry = make_vault_entry(self.profile, self.account, 'GrantedSecret!')
        # Grantee does NOT need legacy — that's the point of GrantedVaultRevealView
        self.grantee = make_user(username='grantee2', email='grantee2@x.com')
        self.admin = make_user(username='gr_admin', email='gradmin@x.com', is_staff=True)
        self.grant = ProfileAccessGrant.objects.create(
            profile=self.profile,
            granted_to=self.grantee,
            granted_by=self.admin,
        )
        self.client.force_login(self.grantee)
        self.reveal_url = reverse('vault:vault_granted_reveal',
                                  kwargs={'slug': self.entry.slug})

    def test_get_returns_405(self):
        response = self.client.get(self.reveal_url)
        self.assertEqual(response.status_code, 405)

    def test_valid_grant_returns_decrypted_password(self):
        response = self.client.post(self.reveal_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['password'], 'GrantedSecret!')

    def test_valid_grant_creates_access_log(self):
        count = self.VaultAccessLog.objects.count()
        self.client.post(self.reveal_url)
        self.assertEqual(self.VaultAccessLog.objects.count(), count + 1)

    def test_expired_grant_returns_403(self):
        from datetime import timedelta
        self.grant.expires_at = timezone.now() - timedelta(hours=1)
        self.grant.save()
        response = self.client.post(self.reveal_url)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    def test_inactive_grant_returns_403(self):
        self.grant.is_active = False
        self.grant.save()
        response = self.client.post(self.reveal_url)
        self.assertEqual(response.status_code, 403)

    def test_user_without_grant_returns_403(self):
        no_grant_user = make_user(username='nogrant2', email='nogrant2@x.com')
        self.client.force_login(no_grant_user)
        response = self.client.post(self.reveal_url)
        self.assertEqual(response.status_code, 403)

    def test_grantee_without_legacy_subscription_can_still_reveal(self):
        # Grantee has no subscription at all — grant alone should be sufficient
        self.assertFalse(self.grantee.is_subscription_active())
        response = self.client.post(self.reveal_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
