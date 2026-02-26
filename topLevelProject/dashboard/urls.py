# dashboard urls
from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    # ── Dashboard Home ────────────────────────────────────────────────────────
    path('dashboard/', views.DashboardHomeView.as_view(), name='dashboard_home'),

    # ── Profile ───────────────────────────────────────────────────────────────
    path('profile/',            views.ProfileCreateView.as_view(),  name='profile_create'),
    path('profile/view/',       views.ProfileDetailView.as_view(),  name='profile_detail'),
    path('profile/edit/',       views.ProfileUpdateView.as_view(),  name='profile_update'),

    # ── Accounts (Digital) ────────────────────────────────────────────────────
    path('accounts/',                        views.AccountListView.as_view(),   name='account_list'),
    path('accounts/create/',                 views.AccountCreateView.as_view(), name='account_create'),
    path('accounts/<slug:slug>/',            views.AccountDetailView.as_view(), name='account_detail'),
    path('accounts/<slug:slug>/edit/',       views.AccountUpdateView.as_view(), name='account_update'),
    path('accounts/<slug:slug>/delete/',     views.AccountDeleteView.as_view(), name='account_delete'),

    # ── Account Relevance Reviews ─────────────────────────────────────────────
    path('reviews/',                                        views.RelevanceReviewListView.as_view(),   name='relevancereview_list'),
    path('reviews/new/',                                    views.RelevanceReviewCreateView.as_view(), name='relevancereview_create'),
    path('reviews/<slug:slug>/',                            views.RelevanceReviewDetailView.as_view(), name='relevancereview_detail'),
    path('reviews/<slug:slug>/edit/',                       views.RelevanceReviewUpdateView.as_view(), name='relevancereview_update'),
    path('reviews/<slug:slug>/delete/',                     views.RelevanceReviewDeleteView.as_view(), name='relevancereview_delete'),
    path('reviews/<slug:review_slug>/mark-reviewed/',       views.MarkItemReviewedView.as_view(),      name='mark_item_reviewed'),

    # ── Contacts ──────────────────────────────────────────────────────────────
    path('contacts/',                    views.ContactListView.as_view(),   name='contact_list'),
    path('contacts/create/',             views.ContactCreateView.as_view(), name='contact_create'),
    path('contacts/<slug:slug>/',        views.ContactDetailView.as_view(), name='contact_detail'),
    path('contacts/<slug:slug>/edit/',   views.ContactUpdateView.as_view(), name='contact_update'),
    path('contacts/<slug:slug>/delete/', views.ContactDeleteView.as_view(), name='contact_delete'),

    # ── Digital Estate ────────────────────────────────────────────────────────
    path('estate/',                    views.EstateListView.as_view(),   name='estate_list'),
    path('estate/create/',             views.EstateCreateView.as_view(), name='estate_create'),
    path('estate/<slug:slug>/',        views.EstateDetailView.as_view(), name='estate_detail'),
    path('estate/<slug:slug>/edit/',   views.EstateUpdateView.as_view(), name='estate_update'),
    path('estate/<slug:slug>/delete/', views.EstateDeleteView.as_view(), name='estate_delete'),

    # ── Devices ───────────────────────────────────────────────────────────────
    path('devices/',                    views.DeviceListView.as_view(),   name='device_list'),
    path('devices/create/',             views.DeviceCreateView.as_view(), name='device_create'),
    path('devices/<slug:slug>/',        views.DeviceDetailView.as_view(), name='device_detail'),
    path('devices/<slug:slug>/edit/',   views.DeviceUpdateView.as_view(), name='device_update'),
    path('devices/<slug:slug>/delete/', views.DeviceDeleteView.as_view(), name='device_delete'),

    # ── Family Awareness ──────────────────────────────────────────────────────
    path('familyawareness/',                    views.FamilyAwarenessListView.as_view(),   name='familyawareness_list'),
    path('familyawareness/create/',             views.FamilyAwarenessCreateView.as_view(), name='familyawareness_create'),
    path('familyawareness/<slug:slug>/',        views.FamilyAwarenessDetailView.as_view(), name='familyawareness_detail'),
    path('familyawareness/<slug:slug>/edit/',   views.FamilyAwarenessUpdateView.as_view(), name='familyawareness_update'),
    path('familyawareness/<slug:slug>/delete/', views.FamilyAwarenessDeleteView.as_view(), name='familyawareness_delete'),

    # ── Funeral Planning ──────────────────────────────────────────────────────
    path('funeralplan/',          views.FuneralPlanIndexView.as_view(),  name='funeralplan_index'),
    path('funeralplan/summary/',  views.FuneralPlanDetailView.as_view(), name='funeralplan_detail'),
    path('funeralplan/delete/',   views.FuneralPlanDeleteView.as_view(), name='funeralplan_delete'),
    # 8 section steps
    path('funeralplan/step/1/',   views.FuneralPlanStep1View.as_view(),  name='funeralplan_step1'),
    path('funeralplan/step/2/',   views.FuneralPlanStep2View.as_view(),  name='funeralplan_step2'),
    path('funeralplan/step/3/',   views.FuneralPlanStep3View.as_view(),  name='funeralplan_step3'),
    path('funeralplan/step/4/',   views.FuneralPlanStep4View.as_view(),  name='funeralplan_step4'),
    path('funeralplan/step/5/',   views.FuneralPlanStep5View.as_view(),  name='funeralplan_step5'),
    path('funeralplan/step/6/',   views.FuneralPlanStep6View.as_view(),  name='funeralplan_step6'),
    path('funeralplan/step/7/',   views.FuneralPlanStep7View.as_view(),  name='funeralplan_step7'),
    path('funeralplan/step/8/',   views.FuneralPlanStep8View.as_view(),  name='funeralplan_step8'),

    # ── Important Documents ───────────────────────────────────────────────────
    path('documents/',                    views.ImportantDocumentListView.as_view(),   name='importantdocument_list'),
    path('documents/create/',             views.ImportantDocumentCreateView.as_view(), name='importantdocument_create'),
    path('documents/<slug:slug>/',        views.ImportantDocumentDetailView.as_view(), name='importantdocument_detail'),
    path('documents/<slug:slug>/edit/',   views.ImportantDocumentUpdateView.as_view(), name='importantdocument_update'),
    path('documents/<slug:slug>/delete/', views.ImportantDocumentDeleteView.as_view(), name='importantdocument_delete'),

    # ── Onboarding ────────────────────────────────────────────────────────────
    path('onboarding/',           views.OnboardingWelcomeView.as_view(),   name='onboarding_welcome'),
    path('onboarding/contacts/',  views.OnboardingContactView.as_view(),   name='onboarding_contacts'),
    path('onboarding/accounts/',  views.OnboardingAccountView.as_view(),   name='onboarding_accounts'),
    path('onboarding/devices/',   views.OnboardingDeviceView.as_view(),    name='onboarding_devices'),
    path('onboarding/estate/',    views.OnboardingEstateView.as_view(),    name='onboarding_estate'),
    path('onboarding/documents/', views.OnboardingDocumentsView.as_view(), name='onboarding_documents'),
    path('onboarding/family/',    views.OnboardingFamilyView.as_view(),    name='onboarding_family'),
    path('onboarding/complete/',  views.OnboardingCompleteView.as_view(),  name='onboarding_complete'),
]