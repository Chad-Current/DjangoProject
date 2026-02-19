# baseapp/urls.py
from django.urls import path
from .views import *
from .views import (
    checklist_download_view,
    checklist_email_view,
    checklist_email_success_view,
    HomeView,
)

app_name = 'baseapp'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('checklist/download/', ChecklistDownloadView.as_view(), name='checklist_download'),
    path('checklist/email/', ChecklistEmailView.as_view(), name='checklist_email'),
    path('checklist/email/sent/', ChecklistEmailSuccessView.as_view(), name='checklist_email_success'),
]