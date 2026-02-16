from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.db.models import Q
from django.views.generic import (
    TemplateView, 
    CreateView, 
    UpdateView, 
    DetailView, 
    ListView,
    FormView,
    View
)

from dashboard.models import Profile, Contact
from .models import RecoveryRequest
from .forms import (
    ExternalRecoveryRequestForm,
    AuthenticatedRecoveryRequestForm,
    AdminRecoveryReviewForm
)


# ============================================================================
# MIXINS
# ============================================================================

class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin to require staff access"""
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('dashboard:dashboard_home')


# ============================================================================
# PUBLIC VIEWS
# ============================================================================

class HomeView(TemplateView):
    """Base app home view"""
    template_name = "baseapp/base.html"


class ExternalRecoveryRequestView(CreateView):
    """
    Public view for external (non-authenticated) users to submit recovery requests.
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
    """
    Verify email address for external recovery requests.
    """
    def get(self, request, token):
        try:
            recovery_request = get_object_or_404(RecoveryRequest, verification_token=token)
            
            # Check if already verified
            if recovery_request.is_verified():
                messages.info(request, 'This request has already been verified.')
                return redirect('recovery:recovery_request_status', pk=recovery_request.pk)
            
            # Check verification attempts limit
            if recovery_request.verification_attempts >= 5:
                messages.error(
                    request,
                    'Too many verification attempts. Please contact support.'
                )
                return redirect('recovery:recovery_request_status', pk=recovery_request.pk)
            
            # Verify the request
            recovery_request.verify()
            recovery_request.verification_attempts += 1
            recovery_request.save()
            
            # Send notification to admin
            self.send_admin_notification(recovery_request)
            
            messages.success(
                request,
                'Your email has been verified! Your request is now being reviewed by our team. '
                'You will receive updates at the email address you provided.'
            )
            
            return redirect('recovery:recovery_request_status', pk=recovery_request.pk)
            
        except RecoveryRequest.DoesNotExist:
            messages.error(request, 'Invalid or expired verification link.')
            return redirect('recovery:external_recovery_request')
    
    def send_admin_notification(self, recovery_request):
        """Send notification email to admins"""
        from .utils import send_admin_notification
        send_admin_notification(recovery_request)


class RecoveryRequestStatusView(DetailView):
    """
    View the status of a recovery request.
    Accessible to the requester (via email verification) or authenticated users.
    """
    model = RecoveryRequest
    template_name = 'recovery/status.html'
    context_object_name = 'recovery_request'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Recovery Request Status'
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """Check access permissions"""
        recovery_request = self.get_object()
        has_access = False
        
        # If user is authenticated
        if request.user.is_authenticated:
            # User who submitted the request
            if recovery_request.requested_by_user == request.user:
                has_access = True
            # Staff/admin
            elif request.user.is_staff or request.user.is_superuser:
                has_access = True
        
        # External users can view if they have the verification token in session
        session_key = f'verified_recovery_{recovery_request.pk}'
        if request.session.get(session_key):
            has_access = True
        
        # Also allow access if they just verified
        if request.GET.get('verified') == 'true':
            request.session[session_key] = True
            has_access = True
        
        if not has_access:
            return HttpResponseForbidden(
                "You do not have permission to view this recovery request."
            )
        
        return super().dispatch(request, *args, **kwargs)


# ============================================================================
# AUTHENTICATED USER VIEWS
# ============================================================================

class AuthenticatedRecoveryRequestView(LoginRequiredMixin, CreateView):
    """
    Authenticated users can submit recovery requests for profiles they have access to.
    """
    model = RecoveryRequest
    form_class = AuthenticatedRecoveryRequestForm
    template_name = 'recovery/authenticated_request.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user is authorized to submit recovery request for this profile"""
        self.profile = get_object_or_404(Profile, pk=self.kwargs['profile_id'])
        
        is_authorized = False
        
        # Check if user is a contact with digital executor privileges
        try:
            contact = Contact.objects.get(
                profile=self.profile,
                email=request.user.email,
                is_digital_executor=True
            )
            is_authorized = True
        except Contact.DoesNotExist:
            pass
        
        # Or if they're staff/admin
        if request.user.is_staff or request.user.is_superuser:
            is_authorized = True
        
        if not is_authorized:
            return HttpResponseForbidden(
                "You do not have permission to submit recovery requests for this profile."
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
        context['page_title'] = f'Recovery Request for {self.profile.first_name} {self.profile.last_name}'
        return context
    
    def form_valid(self, form):
        recovery_request = form.save()
        
        # Send notification to admin
        from .utils import send_admin_notification
        send_admin_notification(recovery_request)
        
        messages.success(
            self.request,
            'Your recovery request has been submitted and will be reviewed shortly.'
        )
        
        return redirect('recovery:recovery_request_status', pk=recovery_request.pk)


class MyRecoveryRequestsListView(LoginRequiredMixin, ListView):
    """
    List all recovery requests submitted by the authenticated user.
    """
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
    """
    Allow users to cancel their own recovery requests.
    """
    def get(self, request, pk):
        recovery_request = get_object_or_404(RecoveryRequest, pk=pk)
        
        # Check permission
        if recovery_request.requested_by_user != request.user and not request.user.is_staff:
            return HttpResponseForbidden("You cannot cancel this request.")
        
        # Only allow cancellation of pending/verified/in-progress requests
        if recovery_request.status not in ['Pending Verification', 'Verified', 'In Progress']:
            messages.error(
                request,
                f'Cannot cancel a request with status: {recovery_request.status}'
            )
            return redirect('recovery:recovery_request_status', pk=pk)
        
        context = {
            'recovery_request': recovery_request,
        }
        return render(request, 'recovery/cancel_confirm.html', context)
    
    def post(self, request, pk):
        recovery_request = get_object_or_404(RecoveryRequest, pk=pk)
        
        # Check permission
        if recovery_request.requested_by_user != request.user and not request.user.is_staff:
            return HttpResponseForbidden("You cannot cancel this request.")
        
        # Only allow cancellation of pending/verified/in-progress requests
        if recovery_request.status in ['Pending Verification', 'Verified', 'In Progress']:
            recovery_request.status = 'Cancelled'
            recovery_request.save()
            
            messages.success(request, 'Recovery request has been cancelled.')
            return redirect('recovery:my_recovery_requests')
        else:
            messages.error(
                request,
                f'Cannot cancel a request with status: {recovery_request.status}'
            )
            return redirect('recovery:recovery_request_status', pk=pk)


class ResendVerificationEmailView(View):
    """
    Resend verification email for external recovery requests.
    """
    def get(self, request, pk):
        recovery_request = get_object_or_404(RecoveryRequest, pk=pk)
        
        # Only allow for unverified external requests
        if recovery_request.is_verified():
            messages.info(request, 'This request has already been verified.')
            return redirect('recovery:recovery_request_status', pk=pk)
        
        if not recovery_request.is_external_request():
            messages.error(request, 'This request does not require email verification.')
            return redirect('recovery:recovery_request_status', pk=pk)
        
        # Check rate limiting
        if recovery_request.verification_attempts >= 10:
            messages.error(
                request,
                'Maximum verification attempts reached. Please contact support.'
            )
            return redirect('recovery:recovery_request_status', pk=pk)
        
        # Generate new token and send email
        recovery_request.generate_verification_token()
        recovery_request.verification_attempts += 1
        recovery_request.save()
        
        # Send the email
        self.send_verification_email(recovery_request)
        
        messages.success(
            request,
            f'Verification email has been resent to {recovery_request.requester_email}'
        )
        
        return redirect('recovery:recovery_request_status', pk=pk)
    
    def send_verification_email(self, recovery_request):
        """Send verification email"""
        verification_url = f"{settings.SITE_URL}{reverse('recovery:verify_recovery_request', kwargs={'token': recovery_request.verification_token})}"
        
        subject = "Verify Your Account Recovery Request"
        message = f"""
Dear {recovery_request.requester_first_name} {recovery_request.requester_last_name},

Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 48 hours.

If you did not make this request, please ignore this email.

Best regards,
Digital Estate Planning Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recovery_request.requester_email],
            fail_silently=False,
        )


# ============================================================================
# ADMIN VIEWS
# ============================================================================

class AdminRecoveryDashboardView(StaffRequiredMixin, ListView):
    """
    Dashboard for admins to view all recovery requests.
    """
    model = RecoveryRequest
    template_name = 'recovery/admin_dashboard.html'
    context_object_name = 'recovery_requests'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = RecoveryRequest.objects.select_related(
            'profile',
            'requested_by_user',
            'reviewed_by',
            'target_account'
        )
        
        # Apply filters
        status_filter = self.request.GET.get('status', '')
        reason_filter = self.request.GET.get('reason', '')
        verified_filter = self.request.GET.get('verified', '')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if reason_filter:
            queryset = queryset.filter(reason=reason_filter)
        
        if verified_filter == 'yes':
            queryset = queryset.filter(verified_at__isnull=False)
        elif verified_filter == 'no':
            queryset = queryset.filter(verified_at__isnull=True)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get statistics
        context['stats'] = {
            'total': RecoveryRequest.objects.count(),
            'pending': RecoveryRequest.objects.filter(status='Pending Verification').count(),
            'verified': RecoveryRequest.objects.filter(status='Verified').count(),
            'in_progress': RecoveryRequest.objects.filter(status='In Progress').count(),
            'completed': RecoveryRequest.objects.filter(status='Completed').count(),
            'denied': RecoveryRequest.objects.filter(status='Denied').count(),
            'external_requests': RecoveryRequest.objects.filter(requested_by_user__isnull=True).count(),
        }
        
        # Add filter parameters to context
        context['status_filter'] = self.request.GET.get('status', '')
        context['reason_filter'] = self.request.GET.get('reason', '')
        context['verified_filter'] = self.request.GET.get('verified', '')
        context['status_choices'] = RecoveryRequest.STATUS_CHOICES
        context['reason_choices'] = RecoveryRequest.REASON_CHOICES
        context['page_title'] = 'Recovery Request Dashboard'
        
        return context


class AdminReviewRecoveryRequestView(StaffRequiredMixin, UpdateView):
    """
    Admin interface to review and update recovery requests.
    """
    model = RecoveryRequest
    form_class = AdminRecoveryReviewForm
    template_name = 'recovery/admin_review.html'
    
    def get_queryset(self):
        return RecoveryRequest.objects.select_related(
            'profile',
            'requested_by_user',
            'target_account',
            'reviewed_by'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get related contacts for reference
        context['contacts'] = Contact.objects.filter(
            profile=self.object.profile
        ).order_by('contact_relation')
        
        context['page_title'] = f'Review Recovery Request #{self.object.pk}'
        context['recovery_request'] = self.object
        
        return context
    
    def form_valid(self, form):
        # Track status changes
        old_status = self.object.status
        
        # Save with reviewer information
        updated_request = form.save(commit=False, reviewer=self.request.user)
        new_status = updated_request.status
        updated_request.save()
        
        # Send notification email if status changed
        if old_status != new_status:
            from .utils import send_status_update_email
            send_status_update_email(updated_request, old_status, new_status)
        
        messages.success(
            self.request,
            f'Recovery request updated successfully. Status: {new_status}'
        )
        
        return redirect('recovery:admin_review_recovery_request', pk=self.object.pk)