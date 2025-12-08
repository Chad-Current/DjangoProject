from django.urls import path
from .views import *
app_name = "aboutus"

urlpatterns = [
    path('', AboutUs.as_view(), name="aboutus")
]