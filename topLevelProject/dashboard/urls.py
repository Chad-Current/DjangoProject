from django.urls import path
from .views import *
app_name = "dashboard"

urlpatterns = [
    path('', DashboardView.as_view(), name="dashboard")
]
