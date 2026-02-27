# baseapp/urls.py
from django.urls import path
from .views import *
from .views import *

app_name = 'baseapp'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('checklist/download/', ChecklistDownloadView.as_view(), name='checklist_download'),
    path('checklist/email/', ChecklistEmailView.as_view(), name='checklist_email'),
    path('checklist/email/sent/', ChecklistEmailSuccessView.as_view(), name='checklist_email_success'),
    path('legal/privacy-policy/', LegalPolicyView.as_view(), name='privacy_policy'),
    path('legal/terms-and-conditions/', TermsAndCondtionsView.as_view(), name='terms_and_conditions'),
    path('legal/cookie-policy/', CookiePolicyView.as_view(), name='cookie_policy'),
    path('legal/data-collection/', DataCollectionView.as_view(), name='data_collection'),
    path('legal/data-retention/', DataRetentionView.as_view(), name='data_retention'),
    path('legal/accessibilty/', AccessibilityView.as_view(), name='accessibility'),
]