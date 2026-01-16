from django.urls import path
from . import views
app_name = "dashboard"

urlpatterns = [
    # Dashboard Home
    path('', views.DashboardHomeView.as_view(), name='dashboard_home'),
    
    # Profile URLs
    path('profile/', views.ProfileDetailView.as_view(), name='profile_detail'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_update'),
    
    # Account Category URLs
    path('categories/', views.AccountCategoryListView.as_view(), name='accountcategory_list'),
    path('categories/create/', views.AccountCategoryCreateView.as_view(), name='accountcategory_create'),
    path('categories/<int:pk>/edit/', views.AccountCategoryUpdateView.as_view(), name='accountcategory_update'),
    path('categories/<int:pk>/delete/', views.AccountCategoryDeleteView.as_view(), name='accountcategory_delete'),
    
    # Digital Account URLs
    path('accounts/', views.DigitalAccountListView.as_view(), name='digitalaccount_list'),
    path('accounts/<int:pk>/', views.DigitalAccountDetailView.as_view(), name='digitalaccount_detail'),
    path('accounts/create/', views.DigitalAccountCreateView.as_view(), name='digitalaccount_create'),
    path('accounts/<int:pk>/edit/', views.DigitalAccountUpdateView.as_view(), name='digitalaccount_update'),
    path('accounts/<int:pk>/delete/', views.DigitalAccountDeleteView.as_view(), name='digitalaccount_delete'),
    
    # Contact URLs
    path('contacts/', views.ContactListView.as_view(), name='contact_list'),
    path('contacts/<int:pk>/', views.ContactDetailView.as_view(), name='contact_detail'),
    path('contacts/create/', views.ContactCreateView.as_view(), name='contact_create'),
    path('contacts/<int:pk>/edit/', views.ContactUpdateView.as_view(), name='contact_update'),
    path('contacts/<int:pk>/delete/', views.ContactDeleteView.as_view(), name='contact_delete'),
    
    # Device URLs
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
    path('emergency-notes/', views.EmergencyNoteListView.as_view(), name='emergencynote_list'),
    path('emergency-notes/create/', views.EmergencyNoteCreateView.as_view(), name='emergencynote_create'),
    path('emergency-notes/<int:pk>/edit/', views.EmergencyNoteUpdateView.as_view(), name='emergencynote_update'),
    path('emergency-notes/<int:pk>/delete/', views.EmergencyNoteDeleteView.as_view(), name='emergencynote_delete'),
    
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

