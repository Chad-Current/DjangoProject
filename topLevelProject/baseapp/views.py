# baseapp/views.py  ── checklist views
import os
import logging

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from .forms import ChecklistEmailForm
from .models import ChecklistEmailLog

logger = logging.getLogger(__name__)

class HomeView(TemplateView):
    template_name = 'baseapp/index.html'

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_client_ip(request):
    """Return the real client IP, respecting X-Forwarded-For."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


_CHECKLIST_PDF = ('static', 'baseapp', 'downloads', 'digital-estate-checklist.pdf')


def _checklist_pdf_path():
    return os.path.join(settings.BASE_DIR, *_CHECKLIST_PDF)


# ── Rate limiting ─────────────────────────────────────────────────────────────
# Limits: 3 sends per email per hour  |  10 sends per IP per hour

_RATE_EMAIL_LIMIT = 3
_RATE_IP_LIMIT    = 10
_RATE_WINDOW      = 60 * 60  # 1 hour in seconds


def _rate_limit_exceeded(email, ip):
    """
    Returns True and emits a logger warning if either the email address or the
    IP address has exceeded its hourly send limit.
    Uses Django's cache backend (key expiry enforces the sliding window).
    """
    email_key = f'checklist_rl_email:{email}'
    ip_key    = f'checklist_rl_ip:{ip}'

    email_count = cache.get(email_key, 0)
    ip_count    = cache.get(ip_key, 0)

    if email_count >= _RATE_EMAIL_LIMIT:
        logger.warning('Checklist rate limit hit — email: %s (%d sends/hr)', email, email_count)
        return True

    if ip_count >= _RATE_IP_LIMIT:
        logger.warning('Checklist rate limit hit — ip: %s (%d sends/hr)', ip, ip_count)
        return True

    return False


def _rate_limit_increment(email, ip):
    """Increment counters after a successful send."""
    email_key = f'checklist_rl_email:{email}'
    ip_key    = f'checklist_rl_ip:{ip}'

    # add() sets the key only if absent; incr() raises if absent — so we
    # use add+incr together to handle both first-hit and subsequent hits.
    cache.add(email_key, 0, _RATE_WINDOW)
    cache.add(ip_key,    0, _RATE_WINDOW)
    cache.incr(email_key)
    cache.incr(ip_key)


# ── Views ─────────────────────────────────────────────────────────────────────

class ChecklistDownloadView(View):
    """
    Serves the Digital Estate Readiness Checklist PDF as a direct download.

    Place the file at:
        <BASE_DIR>/static/baseapp/downloads/digital-estate-checklist.pdf
    """

    def get(self, request):
        path = _checklist_pdf_path()

        if not os.path.exists(path):
            logger.error('Checklist PDF not found at %s', path)
            raise Http404('Checklist not found.')

        logger.info(
            'Checklist PDF downloaded — user: %s  ip: %s',
            request.user.email if request.user.is_authenticated else 'anonymous',
            _get_client_ip(request),
        )
        with open(path, 'rb') as f:
            content = f.read()

        response = HttpResponse(content, content_type='application/pdf')
        response['Content-Disposition'] = (
            'attachment; filename="digital-estate-checklist.pdf"'
        )
        return response


class ChecklistEmailView(View):
    """
    Public view — no login required.

    Renders a short form (email + optional first name), then emails the
    Digital Estate Readiness Checklist PDF to the address provided.
    Writes a ChecklistEmailLog record for admin tracking.
    Rate-limited to 3 sends per email and 10 sends per IP per hour.
    """

    template_name = 'baseapp/checklist_email.html'

    def get(self, request):
        return render(request, self.template_name, {'form': ChecklistEmailForm()})

    def post(self, request):
        form = ChecklistEmailForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        email      = form.cleaned_data['email']
        first_name = form.cleaned_data.get('first_name') or 'there'
        ip         = _get_client_ip(request)

        # ── Rate limit check ─────────────────────────────────────────────────
        if _rate_limit_exceeded(email, ip):
            messages.error(
                request,
                "You've requested the checklist too many times recently. "
                "Please wait an hour and try again, or contact us directly."
            )
            return render(request, self.template_name, {'form': form})

        # ── PDF existence check ──────────────────────────────────────────────
        pdf_path = _checklist_pdf_path()
        if not os.path.exists(pdf_path):
            logger.error('Checklist PDF missing at %s — requested by %s', pdf_path, email)
            messages.error(
                request,
                'The checklist is temporarily unavailable. Please try again later.'
            )
            return render(request, self.template_name, {'form': form})

        # ── Send ─────────────────────────────────────────────────────────────
        try:
            self._send_checklist(email=email, first_name=first_name, pdf_path=pdf_path)
        except Exception as exc:
            logger.exception('Failed to email checklist to %s: %s', email, exc)
            messages.error(
                request,
                'Something went wrong sending the email. Please try again or contact us.'
            )
            return render(request, self.template_name, {'form': form})

        # ── Post-send bookkeeping ────────────────────────────────────────────
        _rate_limit_increment(email, ip)

        ChecklistEmailLog.objects.create(
            email=email,
            first_name=form.cleaned_data.get('first_name', ''),
            ip_address=ip,
        )
        logger.info('Checklist emailed to %s from ip %s', email, ip)

        messages.success(
            request,
            f'Your checklist is on its way to {email}. '
            'Check your inbox (and spam folder just in case).'
        )
        return redirect('baseapp:checklist_email_success')

    # ── private ───────────────────────────────────────────────────────────────

    def _send_checklist(self, *, email, first_name, pdf_path):
        subject    = 'Your Digital Estate Readiness Checklist'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'hello@digitalestateplan.com')
        context    = {'first_name': first_name}

        text_body = render_to_string('baseapp/emails/checklist_email.txt', context)
        html_body = render_to_string('baseapp/emails/checklist_email.html', context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=[email],
        )
        msg.attach_alternative(html_body, 'text/html')

        with open(pdf_path, 'rb') as f:
            msg.attach(
                filename='digital-estate-checklist.pdf',
                content=f.read(),
                mimetype='application/pdf',
            )

        msg.send(fail_silently=False)


class ChecklistEmailSuccessView(View):
    """Confirmation page shown after a successful checklist email send."""
    template_name = 'baseapp/checklist_email_success.html'

    def get(self, request):
        return render(request, self.template_name)


class LegalPolicyView(View):
    """ Legal Policy Page """
    template_name = 'baseapp/legal/privacy_policy.html'

    def get(self, request):
        return render(request, self.template_name)

class TermsAndCondtionsView(View):
    """ Terms and Conditions Page """
    template_name = 'baseapp/legal/terms_and_condtions.html'

    def get(self, request):
        return render(request, self.template_name)

class CookiePolicyView(View):
    """ Cookie Policy Page """
    template_name = 'baseapp/legal/cookie_policy.html'

    def get(self, request):
        return render(request, self.template_name)

class DataCollectionView(View):
    """ Data Collection Page """
    template_name = 'baseapp/legal/data_collection.html'

    def get(self, request):
        return render(request, self.template_name)  

class DataRetentionView(View):
    """ Data Retention Page """
    template_name = 'baseapp/legal/data_retention.html'

    def get(self, request):
        return render(request, self.template_name)  
    
class AccessibilityView(View):
    """ Accessibility Page """
    template_name = 'baseapp/legal/accessibility.html'

    def get(self, request):
        return render(request, self.template_name)
# ── URL aliases ───────────────────────────────────────────────────────────────

checklist_download_view     = ChecklistDownloadView.as_view()
checklist_email_view        = ChecklistEmailView.as_view()
checklist_email_success_view = ChecklistEmailSuccessView.as_view()