from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static

app_name = "enrollment"

urlpatterns = [
    path('', Enroll.as_view(), name="enrollment_"),
]