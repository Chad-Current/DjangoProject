from django.urls import path
from .views import *
app_name = "services"

urlpatterns = [
    path('', Services.as_view(), name="services")
]
