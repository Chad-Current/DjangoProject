from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static

app_name = "classes"

urlpatterns = [
    path('', Classes.as_view(), name="classes_app")
]



