import importlib
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import clear_url_caches, reverse
from django.utils import timezone

from dashboard.models import Profile

User = get_user_model()


# ═══════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ═══════════════════════════════════════════════════════════════

def make_user(username='recuser', email='recuser@x.com', password='StrongPass1!', **kw):
    return User.objects.create_user(username=username, email=email, password=password, **kw)


def make_legacy(username='recleg', email='recleg@x.com'):
    u = make_user(username=username, email=email)
    u.subscription_tier = 'legacy'
    u.stripe_subscription_id = 'sub_rec'
    u.subscription_status = 'active'
    u.has_paid = True
    u.payment_date = timezone.now()
    u.save()
    return u


def make_profile(user, **kw):
    defaults = dict(
        first_name='Jane', last_name='Doe',
        address_1='123 Main', city='Des Moines', state='IA', zipcode=50309,
    )
    defaults.update(kw)
    return Profile.objects.get_or_create(user=user, defaults=defaults)[0]


def make_recovery_request(profile, **kw):
    from recovery.models import RecoveryRequest
    defaults = dict(
        requester_email='req@x.com',
        requester_first_name='Bob',
        target_description='Need access',
        reason='Death',
        status='Pending Verification',
    )
    defaults.update(kw)
    req = RecoveryRequest(**defaults, profile=profile)
    req.generate_verification_token()
    req.save()
    return req


def _reload_urls():
    import topLevelProject.urls as urls_module
    importlib.reload(urls_module)
    clear_url_caches()


# ═══════════════════════════════════════════════════════════════
#  RecoveryRequest MODEL TESTS
# ═══════════════════════════════════════════════════════════════

class RecoveryRequestModelTest(TestCase):

    def setUp(self):
        from recovery.models import RecoveryRequest
        self.RecoveryRequest = RecoveryRequest
        self.owner = make_legacy()
        self.profile = make_profile(self.owner)
        self.req = make_recovery_request(self.profile)

    # ── get_requester_name ────────────────────────────────────────────────────

    def test_get_requester_name_external_with_name(self):
        self.assertEqual(self.req.get_requester_name(), 'Bob')

    def test_get_requester_name_external_full_name(self):
        req = self.RecoveryRequest(
            profile=self.profile,
            requester_first_name='Bob',
            requester_last_name='Smith',
            target_description='Help',
            reason='Death',
        )
        self.assertEqual(req.get_requester_name(), 'Bob Smith')

    def test_get_requester_name_anonymous(self):
        req = self.RecoveryRequest(
            profile=self.profile,
            target_description='Help',
            reason='Death',
        )
        self.assertEqual(req.get_requester_name(), 'Anonymous')

    def test_get_requester_name_authenticated_user(self):
        req = self.RecoveryRequest(
            profile=self.profile,
            requested_by_user=self.owner,
            target_description='Help',
            reason='Death',
        )
        self.assertIn(str(self.owner), req.get_requester_name())

    # ── get_requester_email ───────────────────────────────────────────────────

    def test_get_requester_email_external(self):
        self.assertEqual(self.req.get_requester_email(), 'req@x.com')

    def test_get_requester_email_authenticated_user(self):
        req = self.RecoveryRequest(
            profile=self.profile,
            requested_by_user=self.owner,
            target_description='Help',
            reason='Death',
        )
        self.assertEqual(req.get_requester_email(), self.owner.email)

    # ── is_verified ───────────────────────────────────────────────────────────

    def test_not_verified_before_verify_called(self):
        self.assertFalse(self.req.is_verified())

    def test_verified_after_verify_called(self):
        self.req.verify()
        self.assertTrue(self.req.is_verified())

    # ── is_external_request ───────────────────────────────────────────────────

    def test_is_external_when_no_user(self):
        self.assertTrue(self.req.is_external_request())

    def test_not_external_when_authenticated_user_set(self):
        req = self.RecoveryRequest(
            profile=self.profile,
            requested_by_user=self.owner,
            target_description='Help',
            reason='Death',
        )
        self.assertFalse(req.is_external_request())

    # ── generate_verification_token ───────────────────────────────────────────

    def test_generate_token_creates_non_empty_token(self):
        self.assertIsNotNone(self.req.verification_token)
        self.assertGreater(len(self.req.verification_token), 0)

    def test_generate_token_creates_unique_tokens(self):
        req2 = make_recovery_request(
            self.profile, requester_email='req2@x.com', requester_first_name='Al'
        )
        self.assertNotEqual(self.req.verification_token, req2.verification_token)

    # ── verify ────────────────────────────────────────────────────────────────

    def test_verify_sets_verified_at(self):
        self.req.verify()
        self.assertIsNotNone(self.req.verified_at)

    def test_verify_updates_status_from_pending(self):
        self.req.verify()
        self.assertEqual(self.req.status, 'Verified')

    def test_verify_does_not_change_non_pending_status(self):
        self.req.status = 'In Progress'
        self.req.save()
        self.req.verify()
        self.assertEqual(self.req.status, 'In Progress')

    # ── clean ─────────────────────────────────────────────────────────────────

    def test_clean_raises_when_no_user_and_no_external_info(self):
        req = self.RecoveryRequest(
            profile=self.profile,
            target_description='Help',
            reason='Death',
        )
        with self.assertRaises(ValidationError):
            req.clean()

    def test_clean_passes_with_authenticated_user_only(self):
        req = self.RecoveryRequest(
            profile=self.profile,
            requested_by_user=self.owner,
            target_description='Help',
            reason='Death',
        )
        req.clean()  # should not raise

    def test_clean_passes_with_external_email_only(self):
        req = self.RecoveryRequest(
            profile=self.profile,
            requester_email='ext@x.com',
            target_description='Help',
            reason='Death',
        )
        req.clean()  # should not raise

    def test_clean_passes_with_external_first_name_only(self):
        req = self.RecoveryRequest(
            profile=self.profile,
            requester_first_name='Bob',
            target_description='Help',
            reason='Death',
        )
        req.clean()  # should not raise


# ═══════════════════════════════════════════════════════════════
#  ProfileAccessGrant MODEL TESTS
# ═══════════════════════════════════════════════════════════════

class ProfileAccessGrantModelTest(TestCase):

    def setUp(self):
        from recovery.models import ProfileAccessGrant
        self.ProfileAccessGrant = ProfileAccessGrant
        self.owner = make_legacy(username='grant_owner', email='go@x.com')
        self.profile = make_profile(self.owner)
        self.grantee = make_user(username='grantee1', email='grantee1@x.com')
        self.admin = make_user(username='grant_admin', email='gadmin@x.com', is_staff=True)
        self.grant = ProfileAccessGrant.objects.create(
            profile=self.profile,
            granted_to=self.grantee,
            granted_by=self.admin,
        )

    def test_is_expired_false_when_no_expiry(self):
        self.assertFalse(self.grant.is_expired())

    def test_is_expired_true_when_past_expiry(self):
        self.grant.expires_at = timezone.now() - timedelta(hours=1)
        self.grant.save()
        self.assertTrue(self.grant.is_expired())

    def test_is_expired_false_when_future_expiry(self):
        self.grant.expires_at = timezone.now() + timedelta(days=30)
        self.grant.save()
        self.assertFalse(self.grant.is_expired())

    def test_is_valid_true_when_active_and_not_expired(self):
        self.assertTrue(self.grant.is_valid())

    def test_is_valid_false_when_inactive(self):
        self.grant.is_active = False
        self.grant.save()
        self.assertFalse(self.grant.is_valid())

    def test_is_valid_false_when_expired(self):
        self.grant.expires_at = timezone.now() - timedelta(seconds=1)
        self.grant.save()
        self.assertFalse(self.grant.is_valid())

    def test_str_contains_grantee_and_active_status(self):
        s = str(self.grant)
        self.assertIn('active', s)

    def test_str_revoked_when_inactive(self):
        self.grant.is_active = False
        self.grant.save()
        s = str(self.grant)
        self.assertIn('revoked', s)

    def test_unique_together_prevents_duplicate_grant(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            self.ProfileAccessGrant.objects.create(
                profile=self.profile,
                granted_to=self.grantee,
                granted_by=self.admin,
            )


# ═══════════════════════════════════════════════════════════════
#  RECOVERY VIEW TESTS (require RECOVERY_ENABLED=True)
# ═══════════════════════════════════════════════════════════════

@override_settings(RECOVERY_ENABLED=True)
class ExternalRecoveryRequestViewTest(TestCase):

    def setUp(self):
        _reload_urls()
        self.owner = make_legacy(username='rr_owner', email='rr_owner@x.com')
        self.profile = make_profile(self.owner)
        self.url = reverse('recovery:external_recovery_request')
        self.valid_data = {
            'deceased_user_email': 'rr_owner@x.com',
            'requester_first_name': 'Bob',
            'requester_last_name': 'Smith',
            'requester_email': 'bob@x.com',
            'requester_phone': '555-1234',
            'requester_relationship': 'Spouse',
            'reason': 'Death',
            'target_description': 'Need access to estate plan',
            'accept_terms': True,
        }

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @patch('recovery.forms.ExternalRecoveryRequestForm.send_verification_email')
    def test_valid_post_creates_recovery_request(self, mock_send):
        from recovery.models import RecoveryRequest
        count = RecoveryRequest.objects.count()
        self.client.post(self.url, self.valid_data)
        self.assertEqual(RecoveryRequest.objects.count(), count + 1)

    @patch('recovery.forms.ExternalRecoveryRequestForm.send_verification_email')
    def test_valid_post_redirects_to_status(self, mock_send):
        from recovery.models import RecoveryRequest
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, 302)
        req = RecoveryRequest.objects.latest('created_at')
        self.assertIn(str(req.pk), response['Location'])

    @patch('recovery.forms.ExternalRecoveryRequestForm.send_verification_email')
    def test_valid_post_sets_session_key(self, mock_send):
        from recovery.models import RecoveryRequest
        self.client.post(self.url, self.valid_data)
        req = RecoveryRequest.objects.latest('created_at')
        session_key = f'verified_recovery_{req.pk}'
        self.assertTrue(self.client.session.get(session_key))

    def test_nonexistent_deceased_email_fails(self):
        data = {**self.valid_data, 'deceased_user_email': 'nobody@x.com'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors.get('deceased_user_email'))

    def test_missing_requester_email_fails(self):
        data = {**self.valid_data}
        data.pop('requester_email')
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)

    def test_unchecked_accept_terms_fails(self):
        data = {**self.valid_data}
        data.pop('accept_terms')
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('accept_terms', response.context['form'].errors)


@override_settings(RECOVERY_ENABLED=True)
class VerifyRecoveryRequestViewTest(TestCase):

    def setUp(self):
        _reload_urls()
        self.owner = make_legacy(username='vrv_owner', email='vrv@x.com')
        self.profile = make_profile(self.owner)
        self.req = make_recovery_request(self.profile)

    def _verify_url(self):
        return reverse('recovery:verify_recovery_request',
                       kwargs={'token': self.req.verification_token})

    @patch('recovery.views._send_admin_notification')
    def test_valid_token_verifies_request(self, mock_notify):
        self.client.get(self._verify_url())
        self.req.refresh_from_db()
        self.assertTrue(self.req.is_verified())

    @patch('recovery.views._send_admin_notification')
    def test_valid_token_redirects_to_status(self, mock_notify):
        response = self.client.get(self._verify_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.req.pk), response['Location'])

    def test_invalid_token_returns_404(self):
        url = reverse('recovery:verify_recovery_request',
                      kwargs={'token': 'completely-invalid-token-xyz'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_expired_token_redirects_without_verifying(self):
        self.req.created_at = timezone.now() - timedelta(hours=49)
        self.req.save()
        response = self.client.get(self._verify_url())
        self.req.refresh_from_db()
        self.assertFalse(self.req.is_verified())
        self.assertEqual(response.status_code, 302)

    @patch('recovery.views._send_admin_notification')
    def test_already_verified_shows_info_and_redirects(self, mock_notify):
        self.req.verify()
        response = self.client.get(self._verify_url())
        self.assertEqual(response.status_code, 302)

    def test_five_attempts_blocks_verification(self):
        self.req.verification_attempts = 5
        self.req.save()
        self.client.get(self._verify_url())
        self.req.refresh_from_db()
        self.assertFalse(self.req.is_verified())


@override_settings(RECOVERY_ENABLED=True)
class RecoveryRequestStatusViewTest(TestCase):

    def setUp(self):
        _reload_urls()
        self.owner = make_legacy(username='rrs_owner', email='rrs@x.com')
        self.profile = make_profile(self.owner)
        self.req = make_recovery_request(
            self.profile, requested_by_user=self.owner,
            requester_email='', requester_first_name=''
        )
        self.req.verify()
        self.status_url = reverse('recovery:recovery_request_status',
                                  kwargs={'pk': self.req.pk})

    def test_authenticated_owner_can_view_status(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_with_session_key_can_view_status(self):
        session = self.client.session
        session[f'verified_recovery_{self.req.pk}'] = True
        session.save()
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 200)

    def test_staff_user_can_view_any_status(self):
        staff = make_user(username='rrs_staff', email='rrsstaff@x.com', is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_user_gets_403(self):
        other = make_user(username='rrs_other', email='rrsother@x.com')
        self.client.force_login(other)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_without_session_gets_403(self):
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 403)

    def test_verified_query_param_grants_access(self):
        response = self.client.get(self.status_url + '?verified=true')
        self.assertEqual(response.status_code, 200)
