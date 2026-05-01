from io import BytesIO
from unittest.mock import patch

from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .models import ChecklistEmailLog


# ═══════════════════════════════════════════════════════════════
#  PUBLIC TEMPLATE VIEW TESTS
# ═══════════════════════════════════════════════════════════════

class PublicTemplateViewTest(TestCase):
    """All public pages must return HTTP 200 with no auth required."""

    def _get(self, url_name):
        return self.client.get(reverse(f'baseapp_main:{url_name}'))

    def test_home_returns_200(self):
        self.assertEqual(self._get('home').status_code, 200)

    def test_about_returns_200(self):
        self.assertEqual(self._get('about').status_code, 200)

    def test_what_it_does_returns_200(self):
        self.assertEqual(self._get('what_it_does').status_code, 200)

    def test_pricing_returns_200(self):
        self.assertEqual(self._get('pricing').status_code, 200)

    def test_privacy_policy_returns_200(self):
        self.assertEqual(self._get('privacy_policy').status_code, 200)

    def test_terms_and_conditions_returns_200(self):
        self.assertEqual(self._get('terms_and_conditions').status_code, 200)

    def test_cookie_policy_returns_200(self):
        self.assertEqual(self._get('cookie_policy').status_code, 200)

    def test_data_collection_returns_200(self):
        self.assertEqual(self._get('data_collection').status_code, 200)

    def test_data_retention_returns_200(self):
        self.assertEqual(self._get('data_retention').status_code, 200)

    def test_accessibility_returns_200(self):
        self.assertEqual(self._get('accessibility').status_code, 200)

    def test_roles_returns_200(self):
        self.assertEqual(self._get('roles').status_code, 200)

    def test_checklist_email_success_returns_200(self):
        self.assertEqual(self._get('checklist_email_success').status_code, 200)

    def test_checklist_email_form_returns_200(self):
        self.assertEqual(self._get('checklist_email').status_code, 200)


# ═══════════════════════════════════════════════════════════════
#  CHECKLIST DOWNLOAD VIEW TESTS
# ═══════════════════════════════════════════════════════════════

class ChecklistDownloadViewTest(TestCase):

    @patch('baseapp.views.os.path.exists', return_value=False)
    def test_download_404_when_file_missing(self, mock_exists):
        response = self.client.get(reverse('baseapp_main:checklist_download'))
        self.assertEqual(response.status_code, 404)

    @patch('builtins.open', return_value=BytesIO(b'%PDF-1.4 fake'))
    @patch('baseapp.views.os.path.exists', return_value=True)
    def test_download_returns_pdf_content_type(self, mock_exists, mock_open):
        response = self.client.get(reverse('baseapp_main:checklist_download'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    @patch('builtins.open', return_value=BytesIO(b'%PDF-1.4 fake'))
    @patch('baseapp.views.os.path.exists', return_value=True)
    def test_download_has_attachment_disposition(self, mock_exists, mock_open):
        response = self.client.get(reverse('baseapp_main:checklist_download'))
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('digital-estate-checklist.pdf', response['Content-Disposition'])


# ═══════════════════════════════════════════════════════════════
#  CHECKLIST EMAIL VIEW TESTS
# ═══════════════════════════════════════════════════════════════

_LOCMEM_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'checklist-test',
    }
}


@override_settings(CACHES=_LOCMEM_CACHE)
class ChecklistEmailViewTest(TestCase):

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _valid_post(self, email='prospect@example.com', first_name='John', ip='127.0.0.1'):
        return self.client.post(
            reverse('baseapp_main:checklist_email'),
            {'email': email, 'first_name': first_name},
            REMOTE_ADDR=ip,
        )

    # ── basic GET ─────────────────────────────────────────────────────────────

    def test_get_returns_200(self):
        response = self.client.get(reverse('baseapp_main:checklist_email'))
        self.assertEqual(response.status_code, 200)

    # ── successful send ───────────────────────────────────────────────────────

    @patch('baseapp.views.ChecklistEmailView._send_checklist')
    @patch('baseapp.views.os.path.exists', return_value=True)
    def test_valid_post_creates_log_entry(self, mock_exists, mock_send):
        count_before = ChecklistEmailLog.objects.count()
        self._valid_post()
        self.assertEqual(ChecklistEmailLog.objects.count(), count_before + 1)
        log = ChecklistEmailLog.objects.latest('sent_at')
        self.assertEqual(log.email, 'prospect@example.com')
        self.assertEqual(log.first_name, 'John')

    @patch('baseapp.views.ChecklistEmailView._send_checklist')
    @patch('baseapp.views.os.path.exists', return_value=True)
    def test_valid_post_redirects_to_success(self, mock_exists, mock_send):
        response = self._valid_post(email='redirect@example.com')
        self.assertEqual(response.status_code, 302)
        self.assertIn('checklist', response['Location'])

    # ── rate limiting — email ─────────────────────────────────────────────────

    @patch('baseapp.views.ChecklistEmailView._send_checklist')
    @patch('baseapp.views.os.path.exists', return_value=True)
    def test_email_rate_limit_blocks_after_3_sends(self, mock_exists, mock_send):
        for i in range(3):
            self._valid_post(email='rl@example.com', first_name=f'U{i}')

        # 4th request from same email
        response = self._valid_post(email='rl@example.com', first_name='Blocked')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'too many times')
        self.assertEqual(ChecklistEmailLog.objects.filter(email='rl@example.com').count(), 3)

    @patch('baseapp.views.ChecklistEmailView._send_checklist')
    @patch('baseapp.views.os.path.exists', return_value=True)
    def test_fourth_email_send_not_logged(self, mock_exists, mock_send):
        for i in range(3):
            self._valid_post(email='rl2@example.com', first_name=f'U{i}')
        self._valid_post(email='rl2@example.com', first_name='NoLog')
        # Still only 3 log entries, not 4
        self.assertEqual(ChecklistEmailLog.objects.filter(email='rl2@example.com').count(), 3)

    # ── rate limiting — IP ────────────────────────────────────────────────────

    @patch('baseapp.views.ChecklistEmailView._send_checklist')
    @patch('baseapp.views.os.path.exists', return_value=True)
    def test_ip_rate_limit_blocks_after_10_sends(self, mock_exists, mock_send):
        for i in range(10):
            self._valid_post(email=f'iprl{i}@example.com', ip='10.0.0.99')

        response = self._valid_post(email='iprl11@example.com', ip='10.0.0.99')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'too many times')

    # ── PDF file missing ──────────────────────────────────────────────────────

    @patch('baseapp.views.os.path.exists', return_value=False)
    def test_missing_pdf_shows_error_message(self, mock_exists):
        response = self._valid_post(email='nofile@example.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'temporarily unavailable')
        self.assertEqual(ChecklistEmailLog.objects.count(), 0)

    # ── send failure ──────────────────────────────────────────────────────────

    @patch('baseapp.views.ChecklistEmailView._send_checklist', side_effect=Exception('SMTP err'))
    @patch('baseapp.views.os.path.exists', return_value=True)
    def test_send_failure_shows_error_message(self, mock_exists, mock_send):
        response = self._valid_post(email='sendfail@example.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'went wrong')

    @patch('baseapp.views.ChecklistEmailView._send_checklist', side_effect=Exception('SMTP err'))
    @patch('baseapp.views.os.path.exists', return_value=True)
    def test_send_failure_does_not_create_log(self, mock_exists, mock_send):
        self._valid_post(email='sendfail2@example.com')
        self.assertEqual(ChecklistEmailLog.objects.filter(email='sendfail2@example.com').count(), 0)

    # ── invalid form ──────────────────────────────────────────────────────────

    def test_invalid_email_rerenders_form(self):
        response = self.client.post(
            reverse('baseapp_main:checklist_email'),
            {'email': 'not-an-email', 'first_name': 'Test'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)


# ═══════════════════════════════════════════════════════════════
#  CHECKLIST EMAIL LOG MODEL TESTS
# ═══════════════════════════════════════════════════════════════

class ChecklistEmailLogModelTest(TestCase):

    def test_str_with_first_name(self):
        log = ChecklistEmailLog.objects.create(
            email='test@example.com',
            first_name='Alice',
            ip_address='127.0.0.1',
        )
        s = str(log)
        self.assertIn('test@example.com', s)
        self.assertIn('Alice', s)

    def test_str_without_first_name_has_no_empty_parens(self):
        log = ChecklistEmailLog.objects.create(email='anon@example.com')
        s = str(log)
        self.assertIn('anon@example.com', s)
        self.assertNotIn('()', s)

    def test_ordering_is_most_recent_first(self):
        log1 = ChecklistEmailLog.objects.create(email='a@x.com')
        log2 = ChecklistEmailLog.objects.create(email='b@x.com')
        logs = list(ChecklistEmailLog.objects.all())
        self.assertEqual(logs[0], log2)

    def test_converted_defaults_to_false(self):
        log = ChecklistEmailLog.objects.create(email='conv@x.com')
        self.assertFalse(log.converted)


# ═══════════════════════════════════════════════════════════════
#  ERROR HANDLER TESTS
# ═══════════════════════════════════════════════════════════════

class ErrorHandlerTest(TestCase):

    def test_404_handler_returns_404(self):
        from baseapp.views import error_404
        request = RequestFactory().get('/nonexistent/')
        response = error_404(request)
        self.assertEqual(response.status_code, 404)

    def test_500_handler_returns_500(self):
        from baseapp.views import error_500
        request = RequestFactory().get('/')
        response = error_500(request)
        self.assertEqual(response.status_code, 500)

    def test_400_handler_returns_400(self):
        from baseapp.views import error_400
        request = RequestFactory().get('/')
        response = error_400(request)
        self.assertEqual(response.status_code, 400)

    def test_403_handler_returns_403(self):
        from baseapp.views import error_403
        request = RequestFactory().get('/')
        response = error_403(request)
        self.assertEqual(response.status_code, 403)
