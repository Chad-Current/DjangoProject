from django.urls import path
from . import views
app_name = "dashboard"

urlpatterns = [
    # Dashboard Home
    path('dashboard/', views.DashboardHomeView.as_view(), name='dashboard_home'),
    
    # Profile URLs --- DONE
    path('profile/', views.ProfileDetailView.as_view(), name='profile_detail'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_update'),
    
    # Account (Digital) URLs --- DONE
    path('accounts/', views.AccountListView.as_view(), name='account_list'),
    path('accounts/<int:pk>/', views.AccountDetailView.as_view(), name='account_detail'),
    path('accounts/create/', views.AccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/edit/', views.AccountUpdateView.as_view(), name='account_update'),
    path('accounts/<int:pk>/delete/', views.AccountDeleteView.as_view(), name='account_delete'),
    
    # Account Relevance Review
    path('account-reviews/', views.AccountRelevanceReviewListView.as_view(), name='accountrelevancereview_list'),
    path('account-reviews/new/', views.AccountRelevanceReviewCreateView.as_view(), name='accountrelevancereview_create'),
    path('account-reviews/<int:pk>/', views.AccountRelevanceReviewDetailView.as_view(), name='accountrelevancereview_detail'),
    path('account-reviews/<int:pk>/edit/', views.AccountRelevanceReviewUpdateView.as_view(), name='accountrelevancereview_update'),
    path('account-reviews/<int:pk>/delete/', views.AccountRelevanceReviewDeleteView.as_view(), name='accountrelevancereview_delete'),

    # Contact URLs
    path('contacts/', views.ContactListView.as_view(), name='contact_list'),
    path('contacts/<int:pk>/', views.ContactDetailView.as_view(), name='contact_detail'),
    path('contacts/create/', views.ContactCreateView.as_view(), name='contact_create'),
    path('contacts/<int:pk>/edit/', views.ContactUpdateView.as_view(), name='contact_update'),
    path('contacts/<int:pk>/delete/', views.ContactDeleteView.as_view(), name='contact_delete'),    
    
    # Device URLs --- DONE
    path('devices/', views.DeviceListView.as_view(), name='device_list'),
    path('devices/<int:pk>/', views.DeviceDetailView.as_view(), name='device_detail'),
    path('devices/create/', views.DeviceCreateView.as_view(), name='device_create'),
    path('devices/<int:pk>/edit/', views.DeviceUpdateView.as_view(), name='device_update'),
    path('devices/<int:pk>/delete/', views.DeviceDeleteView.as_view(), name='device_delete'),
    
    # Important Document URLs
    path('documents/', views.ImportantDocumentListView.as_view(), name='importantdocument_list'),
    path('documents/<int:pk>/', views.ImportantDocumentDetailView.as_view(), name='importantdocument_detail'),
    path('documents/create/', views.ImportantDocumentCreateView.as_view(), name='importantdocument_create'),
    path('documents/<int:pk>/edit/', views.ImportantDocumentUpdateView.as_view(), name='importantdocument_update'),
    path('documents/<int:pk>/delete/', views.ImportantDocumentDeleteView.as_view(), name='importantdocument_delete'),
    
    # Delegation Grant URLs
    path('delegations/', views.DelegationGrantListView.as_view(), name='delegationgrant_list'),
    path('delegations/create/', views.DelegationGrantCreateView.as_view(), name='delegationgrant_create'),
    path('delegations/<int:pk>/edit/', views.DelegationGrantUpdateView.as_view(), name='delegationgrant_update'),
    path('delegations/<int:pk>/delete/', views.DelegationGrantDeleteView.as_view(), name='delegationgrant_delete'),
    
    # Emergency Note URLs
    path('emergency-contacts/', views.EmergencyContactListView.as_view(), name='emergencycontact_list'),
    path('emergency-contacts<int:pk>/', views.EmergencyContactListView.as_view(), name='emergencycontact_detail'),
    path('emergency-contacts/create/', views.EmergencyContactCreateView.as_view(), name='emergencycontact_create'),
    path('emergency-contacts/<int:pk>/edit/', views.EmergencyContactUpdateView.as_view(), name='emergencycontact_update'),
    path('emergency-contacts/<int:pk>/delete/', views.EmergencyContactDeleteView.as_view(), name='emergencycontact_delete'),
    
    # Checkup URLs
    path('checkups/', views.CheckupListView.as_view(), name='checkup_list'),
    path('checkups/create/', views.CheckupCreateView.as_view(), name='checkup_create'),
    path('checkups/<int:pk>/edit/', views.CheckupUpdateView.as_view(), name='checkup_update'),
    path('checkups/<int:pk>/delete/', views.CheckupDeleteView.as_view(), name='checkup_delete'),
    
    # Recovery Request URLs
    path('recovery-requests/', views.RecoveryRequestListView.as_view(), name='recoveryrequest_list'),
    path('recovery-requests/create/', views.RecoveryRequestCreateView.as_view(), name='recoveryrequest_create'),
    path('recovery-requests/<int:pk>/edit/', views.RecoveryRequestUpdateView.as_view(), name='recoveryrequest_update'),
    path('recovery-requests/<int:pk>/delete/', views.RecoveryRequestDeleteView.as_view(), name='recoveryrequest_delete'),

    # Main Template URL
    path('main-template/', views.MainTemplateView.as_view(), name="main_template")
]

