from django.urls import path
from . import views
app_name = "dashboard"

urlpatterns = [
    # Dashboard Home
    path('dashboard/', views.DashboardHomeView.as_view(), name='dashboard_home'),
    
    # Profile URLs --- DONE
    path('profile/', views.ProfileCreateView.as_view(), name='profile_create'),
    path('profile/<int:pk>/', views.ProfileDetailView.as_view(), name='profile_detail'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_update'),
    
    # Account (Digital) URLs --- DONE
    path('accounts/', views.AccountListView.as_view(), name='account_list'),
    path('accounts/<int:pk>/', views.AccountDetailView.as_view(), name='account_detail'),
    path('accounts/create/', views.AccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/edit/', views.AccountUpdateView.as_view(), name='account_update'),
    path('accounts/<int:pk>/delete/', views.AccountDeleteView.as_view(), name='account_delete'),
  
    # Account Relevance Review
    path('reviews/', views.RelevanceReviewListView.as_view(), name='relevancereview_list'),
    path('reviews/new/', views.RelevanceReviewCreateView.as_view(), name='relevancereview_create'),
    path('reviews/<int:pk>/', views.RelevanceReviewDetailView.as_view(), name='relevancereview_detail'),
    path('reviews/<int:pk>/edit/', views.RelevanceReviewUpdateView.as_view(), name='relevancereview_update'),
    path('reviews/<int:pk>/delete/', views.RelevanceReviewDeleteView.as_view(), name='relevancereview_delete'),
    path('reviews/<int:review_pk>/mark-reviewed/', views.MarkItemReviewedView.as_view(), name='mark_item_reviewed'),    
    
    # Contacts URLs
    path('contacts/', views.ContactListView.as_view(), name='contact_list'),
    path('contacts/<int:pk>/', views.ContactDetailView.as_view(), name='contact_detail'),
    path('contacts/create/', views.ContactCreateView.as_view(), name='contact_create'),
    path('contacts/<int:pk>/edit/', views.ContactUpdateView.as_view(), name='contact_update'),
    path('contacts/<int:pk>/delete/', views.ContactDeleteView.as_view(), name='contact_delete'),

    # Digital Estate
    path('estate/', views.EstateListView.as_view(), name='estate_list'),
    path('estate/<int:pk>/', views.EstateDetailView.as_view(), name='estate_detail'),
    path('estate/create/', views.EstateCreateView.as_view(), name='estate_create'),
    path('estate/<int:pk>/edit/', views.EstateUpdateView.as_view(), name='estate_update'),
    path('estate/<int:pk>/delete/', views.EstateDeleteView.as_view(), name='estate_delete'),    
    
    # Device URLs --- DONE
    path('devices/', views.DeviceListView.as_view(), name='device_list'),
    path('devices/<int:pk>/', views.DeviceDetailView.as_view(), name='device_detail'),
    path('devices/create/', views.DeviceCreateView.as_view(), name='device_create'),
    path('devices/<int:pk>/edit/', views.DeviceUpdateView.as_view(), name='device_update'),
    path('devices/<int:pk>/delete/', views.DeviceDeleteView.as_view(), name='device_delete'),
  
  # Family Awareness URLs
    path('familyawareness/', views.FamilyAwarenessListView.as_view(), name='familyawareness_list'),
    path('familyawareness/<int:pk>/', views.FamilyAwarenessDetailView.as_view(), name='familyawareness_detail'),
    path('familyawareness/create/', views.FamilyAwarenessCreateView.as_view(), name='familyawareness_create'),
    path('familyawareness/<int:pk>/edit/', views.FamilyAwarenessUpdateView.as_view(), name='familyawareness_update'),
    path('familyawareness/<int:pk>/delete/', views.FamilyAwarenessDeleteView.as_view(), name='familyawareness_delete'),

  # Funeral Planning URLs
    path('funeralplanning/', views.FuneralPlanIndexView.as_view(), name='funeralplan_list'),
    path('funeralplanning//<int:pk>/', views.FuneralPlanDetailView.as_view(), name='funeralplan_detail'),
    path('funeralplanning/create/', views.FuneralPlanCreateView.as_view(), name='funeralplan_create'),
    path('funeralplanning/<int:pk>/edit/', views.FuneralPlanUpdateView.as_view(), name='funeralplan_update'),
    path('funeralplanning/<int:pk>/delete/', views.FuneralPlanDeleteView.as_view(), name='funeralplan_delete'),

    # Important Document URLs
    path('documents/', views.ImportantDocumentListView.as_view(), name='importantdocument_list'),
    path('documents/<int:pk>/', views.ImportantDocumentDetailView.as_view(), name='importantdocument_detail'),
    path('documents/create/', views.ImportantDocumentCreateView.as_view(), name='importantdocument_create'),
    path('documents/<int:pk>/edit/', views.ImportantDocumentUpdateView.as_view(), name='importantdocument_update'),
    path('documents/<int:pk>/delete/', views.ImportantDocumentDeleteView.as_view(), name='importantdocument_delete'),
    
    # Onboarding URLs 
    path('onboarding/', views.OnboardingWelcomeView.as_view(), name='onboarding_welcome'),
    path('onboarding/contacts/', views.OnboardingContactView.as_view(), name='onboarding_contacts'),
    path('onboarding/accounts/', views.OnboardingAccountView.as_view(), name='onboarding_accounts'),
    path('onboarding/devices/', views.OnboardingDeviceView.as_view(), name='onboarding_devices'),
    path('onboarding/estate/',    views.OnboardingEstateView.as_view(),     name='onboarding_estate'),
    path('onboarding/documents/', views.OnboardingDocumentsView.as_view(), name='onboarding_documents'),
    path('onboarding/family/',    views.OnboardingFamilyView.as_view(),     name='onboarding_family'),
    path('onboarding/complete/', views.OnboardingCompleteView.as_view(), name='onboarding_complete'),
 ]

