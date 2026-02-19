# recovery/views.py
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.views.generic import (
    CreateView,
    UpdateView,
    DetailView,
    ListView,
    View,
)

from dashboard.models import Profile, Contact
from .models import RecoveryRequest
from .forms import (
    ExternalRecoveryRequestForm,
    AuthenticatedRecoveryRequestForm,
    AdminRecoveryReviewForm,
)


# =============================================================================
# MIXINS
# =============================================================================

class StaffRequiredMixin(UserPassesTestMixin):
    """Require staff or superuser access."""

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('dashboard:dashboard_home')


# =============================================================================
# PUBLIC VIEWS
# =============================================================================

class ExternalRecoveryRequestView(CreateView):
    """
    Public view — no login required.
    External users submit recovery requests here.
    """
    model = RecoveryRequest
    form_class = ExternalRecoveryRequestForm
    template_name = 'recovery/external_request.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Account Recovery Request'
        return context

    def form_valid(self, form):
        recovery_request = form.save()
        messages.success(
            self.request,
            f'Your recovery request has been submitted. Please check your email '
            f'({recovery_request.requester_email}) for a verification link.'
        )
        return redirect('recovery:recovery_request_status', pk=recovery_request.pk)


class VerifyRecoveryRequestView(View):
    """Verify email address for external recovery requests."""

    def get(self, request, token):
        recovery_request = get_object_or_404(RecoveryRequest, verification_token=token)

        if recovery_request.is_verified():
            messages.info(request, 'This request has already been verified.')
            return redirect('recovery:recovery_request_status', pk=recovery_request.pk)

        if recovery_request.verification_attempts >= 5:
            messages.error(request, 'Too many verification attempts. Please contact support.')
            return redirect('recovery:recovery_request_status', pk=recovery_request.pk)

        recovery_request.verify()
        recovery_request.verification_attempts += 1
        recovery_request.save()

        _send_admin_notification(recovery_request)

        messages.success(
            request,
            'Your email has been verified! Your request is now being reviewed by our team. '
            'You will receive updates at the email address you provided.'
        )
        return redirect('recovery:recovery_request_status', pk=recovery_request.pk)


class RecoveryRequestStatusView(DetailView):
    """
    View the status of a recovery request.
    Accessible to the requester (via session after verification) or authenticated users.
    """
    model = RecoveryRequest
    template_name = 'recovery/status.html'
    context_object_name = 'recovery_request'

    def dispatch(self, request, *args, **kwargs):
        recovery_request = self.get_object()
        has_access = False

        if request.user.is_authenticated:
            if recovery_request.requested_by_user == request.user:
                has_access = True
            elif request.user.is_staff or request.user.is_superuser:
                has_access = True

        session_key = f'verified_recovery_{recovery_request.pk}'
        if request.session.get(session_key):
            has_access = True

        if request.GET.get('verified') == 'true':
            request.session[session_key] = True
            has_access = True

        if not has_access:
            return HttpResponseForbidden(
                'You do not have permission to view this recovery request.'
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Recovery Request Status'
        return context


class ResendVerificationEmailView(View):
    """Resend verification email for external recovery requests."""

    def get(self, request, pk):
        recovery_request = get_object_or_404(RecoveryRequest, pk=pk)

        if recovery_request.is_verified():
            messages.info(request, 'This request has already been verified.')
            return redirect('recovery:recovery_request_status', pk=pk)

        if not recovery_request.is_external_request():
            messages.error(request, 'This request does not require email verification.')
            return redirect('recovery:recovery_request_status', pk=pk)

        if recovery_request.verification_attempts >= 10:
            messages.error(
                request,
                'Maximum verification attempts reached. Please contact support.'
            )
            return redirect('recovery:recovery_request_status', pk=pk)

        recovery_request.generate_verification_token()
        recovery_request.verification_attempts += 1
        recovery_request.save()

        _send_verification_email(recovery_request)

        messages.success(
            request,
            f'Verification email has been resent to {recovery_request.requester_email}'
        )
        return redirect('recovery:recovery_request_status', pk=pk)


# =============================================================================
# AUTHENTICATED USER VIEWS
# =============================================================================

class AuthenticatedRecoveryRequestView(LoginRequiredMixin, CreateView):
    """
    Authenticated users submit recovery requests for profiles they have access to.
    Must be a digital executor contact, staff, or superuser.
    """
    model = RecoveryRequest
    form_class = AuthenticatedRecoveryRequestForm
    template_name = 'recovery/authenticated_request.html'

    def dispatch(self, request, *args, **kwargs):
        self.profile = get_object_or_404(Profile, pk=self.kwargs['profile_id'])

        is_authorized = (
            request.user.is_staff
            or request.user.is_superuser
            or Contact.objects.filter(
                profile=self.profile,
                email=request.user.email,
                is_digital_executor=True,
            ).exists()
        )

        if not is_authorized:
            return HttpResponseForbidden(
                'You do not have permission to submit recovery requests for this profile.'
            )

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['profile'] = self.profile
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.profile
        context['page_title'] = (
            f'Recovery Request for {self.profile.first_name} {self.profile.last_name}'
        )
        return context

    def form_valid(self, form):
        recovery_request = form.save()
        _send_admin_notification(recovery_request)
        messages.success(
            self.request,
            'Your recovery request has been submitted and will be reviewed shortly.'
        )
        return redirect('recovery:recovery_request_status', pk=recovery_request.pk)


class MyRecoveryRequestsListView(LoginRequiredMixin, ListView):
    """List all recovery requests submitted by the authenticated user."""
    model = RecoveryRequest
    template_name = 'recovery/my_requests.html'
    context_object_name = 'recovery_requests'
    paginate_by = 20

    def get_queryset(self):
        return RecoveryRequest.objects.filter(
            requested_by_user=self.request.user
        ).select_related('profile', 'target_account').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'My Recovery Requests'
        return context


class CancelRecoveryRequestView(LoginRequiredMixin, View):
    """Allow users to cancel their own pending recovery requests."""

    def _get_and_check(self, request, pk):
        """Shared permission check for GET and POST."""
        recovery_request = get_object_or_404(RecoveryRequest, pk=pk)
        if recovery_request.requested_by_user != request.user and not request.user.is_staff:
            return recovery_request, HttpResponseForbidden('You cannot cancel this request.')
        return recovery_request, None

    def get(self, request, pk):
        recovery_request, denied = self._get_and_check(request, pk)
        if denied:
            return denied

        if recovery_request.status not in ['Pending Verification', 'Verified', 'In Progress']:
            messages.error(
                request, f'Cannot cancel a request with status: {recovery_request.status}'
            )
            return redirect('recovery:recovery_request_status', pk=pk)

        return render(request, 'recovery/cancel_confirm.html', {
            'recovery_request': recovery_request,
        })

    def post(self, request, pk):
        recovery_request, denied = self._get_and_check(request, pk)
        if denied:
            return denied

        if recovery_request.status in ['Pending Verification', 'Verified', 'In Progress']:
            recovery_request.status = 'Cancelled'
            recovery_request.save()
            messages.success(request, 'Recovery request has been cancelled.')
            return redirect('recovery:my_recovery_requests')

        messages.error(
            request, f'Cannot cancel a request with status: {recovery_request.status}'
        )
        return redirect('recovery:recovery_request_status', pk=pk)


# =============================================================================
# ADMIN VIEWS
# =============================================================================

class AdminRecoveryDashboardView(StaffRequiredMixin, ListView):
    """Dashboard for admins to view and filter all recovery requests."""
    model = RecoveryRequest
    template_name = 'recovery/admin_dashboard.html'
    context_object_name = 'recovery_requests'
    paginate_by = 20

    def get_queryset(self):
        qs = RecoveryRequest.objects.select_related(
            'profile', 'requested_by_user', 'reviewed_by', 'target_account'
        )
        status_filter   = self.request.GET.get('status', '')
        reason_filter   = self.request.GET.get('reason', '')
        verified_filter = self.request.GET.get('verified', '')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if reason_filter:
            qs = qs.filter(reason=reason_filter)
        if verified_filter == 'yes':
            qs = qs.filter(verified_at__isnull=False)
        elif verified_filter == 'no':
            qs = qs.filter(verified_at__isnull=True)

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'total':             RecoveryRequest.objects.count(),
            'pending':           RecoveryRequest.objects.filter(status='Pending Verification').count(),
            'verified':          RecoveryRequest.objects.filter(status='Verified').count(),
            'in_progress':       RecoveryRequest.objects.filter(status='In Progress').count(),
            'completed':         RecoveryRequest.objects.filter(status='Completed').count(),
            'denied':            RecoveryRequest.objects.filter(status='Denied').count(),
            'external_requests': RecoveryRequest.objects.filter(requested_by_user__isnull=True).count(),
        }
        context['status_filter']   = self.request.GET.get('status', '')
        context['reason_filter']   = self.request.GET.get('reason', '')
        context['verified_filter'] = self.request.GET.get('verified', '')
        context['status_choices']  = RecoveryRequest.STATUS_CHOICES
        context['reason_choices']  = RecoveryRequest.REASON_CHOICES
        context['page_title']      = 'Recovery Request Dashboard'
        return context


class AdminReviewRecoveryRequestView(StaffRequiredMixin, UpdateView):
    """Admin interface to review and update a single recovery request."""
    model = RecoveryRequest
    form_class = AdminRecoveryReviewForm
    template_name = 'recovery/admin_review.html'

    def get_queryset(self):
        return RecoveryRequest.objects.select_related(
            'profile', 'requested_by_user', 'target_account', 'reviewed_by'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contacts'] = Contact.objects.filter(
            profile=self.object.profile
        ).order_by('contact_relation')
        context['page_title'] = f'Review Recovery Request #{self.object.pk}'
        context['recovery_request'] = self.object
        return context

    def form_valid(self, form):
        old_status = self.object.status
        updated_request = form.save(commit=False, reviewer=self.request.user)
        new_status = updated_request.status
        updated_request.save()

        if old_status != new_status:
            _send_status_update_email(updated_request, old_status, new_status)

        messages.success(
            self.request,
            f'Recovery request updated successfully. Status: {new_status}'
        )
        return redirect('recovery:admin_review_recovery_request', pk=self.object.pk)


# =============================================================================
# PRIVATE HELPERS  (module-level, not exposed via URLs)
# =============================================================================

def _send_admin_notification(recovery_request):
    """Email all staff/admin when a new recovery request arrives."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    admin_emails = list(
        User.objects.filter(
            is_staff=True
        ).values_list('email', flat=True)
    )
    if not admin_emails:
        return

    admin_url = (
        f"{settings.SITE_URL}"
        f"{reverse('recovery:admin_review_recovery_request', kwargs={'pk': recovery_request.pk})}"
    )
    requester_type  = 'External' if recovery_request.is_external_request() else 'Authenticated User'
    requester_name  = recovery_request.get_requester_name()
    requester_email = recovery_request.get_requester_email()

    send_mail(
        subject=f'New Recovery Request #{recovery_request.pk}',
        message=(
            f'A new account recovery request has been submitted.\n\n'
            f'ID: #{recovery_request.pk}\n'
            f'Type: {requester_type}\n'
            f'Name: {requester_name}\n'
            f'Email: {requester_email}\n'
            f'Relationship: {recovery_request.requester_relationship or "N/A"}\n\n'
            f'Profile: {recovery_request.profile.first_name} {recovery_request.profile.last_name}\n'
            f'Reason: {recovery_request.get_reason_display()}\n'
            f'Verified: {"Yes" if recovery_request.is_verified() else "No"}\n\n'
            f'Review: {admin_url}'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=admin_emails,
        fail_silently=True,
    )


def _send_verification_email(recovery_request):
    """Send the email verification link to an external requester."""
    verification_url = (
        f"{settings.SITE_URL}"
        f"{reverse('recovery:verify_recovery_request', kwargs={'token': recovery_request.verification_token})}"
    )
    send_mail(
        subject='Verify Your Account Recovery Request',
        message=(
            f'Dear {recovery_request.requester_first_name} {recovery_request.requester_last_name},\n\n'
            f'Please verify your email address by clicking the link below:\n\n'
            f'{verification_url}\n\n'
            f'This link will expire in 48 hours.\n\n'
            f'If you did not make this request, please ignore this email.\n\n'
            f'Best regards,\nDigital Estate Plan Team'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recovery_request.requester_email],
        fail_silently=False,
    )


def _send_status_update_email(recovery_request, old_status, new_status):
    """Notify the requester when their recovery request status changes."""
    requester_email = recovery_request.get_requester_email()
    if not requester_email:
        return

    status_messages = {
        'Verified':    'Your request has been verified and is awaiting review.',
        'In Progress': 'Your request is currently being processed by our team.',
        'Completed':   'Your recovery request has been completed.',
        'Denied':      'Unfortunately, your recovery request has been denied.',
        'Cancelled':   'Your recovery request has been cancelled.',
    }

    body = (
        f'Dear {recovery_request.get_requester_name()},\n\n'
        f'Your recovery request (ID: #{recovery_request.pk}) has been updated.\n\n'
        f'Previous status: {old_status}\n'
        f'New status: {new_status}\n\n'
        f'{status_messages.get(new_status, f"Status updated to {new_status}")}\n'
    )
    if recovery_request.outcome_notes:
        body += f'\nNotes:\n{recovery_request.outcome_notes}\n'

    body += '\nIf you have questions, please contact our support team.\n\nBest regards,\nDigital Estate Plan Team'

    send_mail(
        subject=f'Recovery Request Update — {new_status}',
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[requester_email],
        fail_silently=True,
    )