# recovery/urls.py
from django.urls import path

from .views import (
    ExternalRecoveryRequestView,
    VerifyRecoveryRequestView,
    AuthenticatedRecoveryRequestView,
    RecoveryRequestStatusView,
    MyRecoveryRequestsListView,
    CancelRecoveryRequestView,
    ResendVerificationEmailView,
    AdminRecoveryDashboardView,
    AdminReviewRecoveryRequestView,
)

app_name = 'recovery'

urlpatterns = [
    # ── public ────────────────────────────────────────────────────────────────
    path('request/', ExternalRecoveryRequestView.as_view(), name='external_recovery_request'),

    path('verify/<str:token>/', VerifyRecoveryRequestView.as_view(), name='verify_recovery_request'),

    path('status/<int:pk>/', RecoveryRequestStatusView.as_view(), name='recovery_request_status'),

    path('<int:pk>/resend-verification/', ResendVerificationEmailView.as_view(), name='resend_verification_email'),

    # ── authenticated user ────────────────────────────────────────────────────
    path('request/<int:profile_id>/authenticated/', AuthenticatedRecoveryRequestView.as_view(), name='authenticated_recovery_request'),

    path('my-requests/', MyRecoveryRequestsListView.as_view(), name='my_recovery_requests'),
    path('<int:pk>/cancel/', CancelRecoveryRequestView.as_view(), name='cancel_recovery_request'),

    # ── admin ─────────────────────────────────────────────────────────────────
    path('admin/', AdminRecoveryDashboardView.as_view(), name='admin_recovery_dashboard'),
    path('admin/<int:pk>/review/', AdminReviewRecoveryRequestView.as_view(), name='admin_review_recovery_request'),
]

# from django.core.mail import send_mail
# from django.conf import settings
# from django.urls import reverse
# from django.db.models import Q


# def send_admin_notification(recovery_request):
#     """
#     Send notification email to admins when a new recovery request is submitted.
#     """
#     subject = f'New Account Recovery Request #{recovery_request.pk}'
    
#     requester_type = "External Requester" if recovery_request.is_external_request() else "Authenticated User"
#     requester_name = recovery_request.get_requester_name()
#     requester_email = recovery_request.get_requester_email()
    
#     admin_url = f"{settings.SITE_URL}{reverse('recovery:admin_review_recovery_request', kwargs={'pk': recovery_request.pk})}"
    
#     message = f"""
# A new account recovery request has been submitted:

# Request ID: #{recovery_request.pk}
# Requester Type: {requester_type}
# Requester Name: {requester_name}
# Requester Email: {requester_email}
# Relationship: {recovery_request.requester_relationship or 'N/A'}

# Profile: {recovery_request.profile.first_name} {recovery_request.profile.last_name}
# Reason: {recovery_request.get_reason_display()}
# Target: {recovery_request.target_description}

# Verification Status: {'Verified' if recovery_request.is_verified() else 'Pending Verification'}

# Review this request here:
# {admin_url}

# ---
# Digital Estate Planning System
#     """
    
#     # Get admin emails
#     from django.contrib.auth import get_user_model
#     User = get_user_model()
#     admin_emails = User.objects.filter(
#         Q(is_staff=True) | Q(is_superuser=True)
#     ).values_list('email', flat=True)
    
#     if admin_emails:
#         send_mail(
#             subject,
#             message,
#             settings.DEFAULT_FROM_EMAIL,
#             list(admin_emails),
#             fail_silently=True,
#         )


# def send_status_update_email(recovery_request, old_status, new_status):
#     """
#     Send email notification when recovery request status changes.
#     """
#     requester_email = recovery_request.get_requester_email()
    
#     if not requester_email:
#         return
    
#     subject = f'Recovery Request Update - {new_status}'
    
#     status_messages = {
#         'Verified': 'Your request has been verified and is awaiting review.',
#         'In Progress': 'Your request is currently being processed by our team.',
#         'Completed': 'Your recovery request has been completed.',
#         'Denied': 'Unfortunately, your recovery request has been denied.',
#         'Cancelled': 'Your recovery request has been cancelled.',
#     }
    
#     status_message = status_messages.get(new_status, f'Status updated to {new_status}')
    
#     message = f"""
# Dear {recovery_request.get_requester_name()},

# Your account recovery request (ID: #{recovery_request.pk}) has been updated.

# Previous Status: {old_status}
# New Status: {new_status}

# {status_message}

# Request Details:
# - Profile: {recovery_request.profile.first_name} {recovery_request.profile.last_name}
# - Target: {recovery_request.target_description}
# - Submitted: {recovery_request.created_at.strftime('%B %d, %Y at %I:%M %p')}
# """
    
#     if recovery_request.outcome_notes:
#         message += f"\nNotes:\n{recovery_request.outcome_notes}\n"
    
#     message += """
# If you have any questions, please contact our support team.

# Best regards,
# Digital Estate Planning Team
#     """
    
#     send_mail(
#         subject,
#         message,
#         settings.DEFAULT_FROM_EMAIL,
#         [requester_email],
#         fail_silently=True,
#     )