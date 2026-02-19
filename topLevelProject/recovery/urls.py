from django.urls import path
from . import views

app_name = 'recovery'

urlpatterns = [
    # Public views
    path('request/', views.ExternalRecoveryRequestView.as_view(), name='external_recovery_request'),
    path('verify/<str:token>/', views.VerifyRecoveryRequestView.as_view(), name='verify_recovery_request'),
    path('status/<int:pk>/', views.RecoveryRequestStatusView.as_view(), name='recovery_request_status'),
 
    # Authenticated user views
    path('submit/<int:profile_id>/', views.AuthenticatedRecoveryRequestView.as_view(), name='authenticated_recovery_request'),
    path('my-requests/', views.MyRecoveryRequestsListView.as_view(), name='my_recovery_requests'),
    path('cancel/<int:pk>/', views.CancelRecoveryRequestView.as_view(), name='cancel_recovery_request'),  
    path('resend-verification/<int:pk>/', views.ResendVerificationEmailView.as_view(), name='resend_verification_email'),
    
    # Admin views
    path('admin/dashboard/', views.AdminRecoveryDashboardView.as_view(), name='admin_recovery_dashboard'),  
    path('admin/review/<int:pk>/', views.AdminReviewRecoveryRequestView.as_view(), name='admin_review_recovery_request'),
]