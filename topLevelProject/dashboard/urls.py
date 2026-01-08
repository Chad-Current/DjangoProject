from django.urls import path
from .views import *
app_name = "dashboard"

urlpatterns = [
    path('accountdirectory/', AccountDirectoryView.as_view(), name='accountdirectory'),
    path('contactdelegation/', ContactDelegationView.as_view(), name='contactdelegation'),
    path('decision/', DecisionView.as_view(), name='decision'),
    path('devices/', DevicesView.as_view(), name='devices'),
    path('digitalestate/', DigitalEstateView.as_view(), name='digitalestate'),
    path('emergencynotes/', EmergencyNotesView.as_view(), name='emergencynotes'),
    path('familyawareness/', FamilyAwarenessView.as_view(), name='familyawareness'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('annualreview/', AnnualReviewView.as_view(), name='annualreview'),
    path('quarterlyreview/', QuarterlyReviewView.as_view(), name='quarterlyreview'),

]