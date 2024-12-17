from django.urls import path
from .views import *
app_name = "faqs"

urlpatterns = [
    path('', Home.as_view(), name="faqs")
]