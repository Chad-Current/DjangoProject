from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static

app_name = "classes_app"

urlpatterns = [
    path('', Classes.as_view(), name="classes"),
    path('puppy', Puppy.as_view(), name='puppy'),
    path('beginner', Beginner.as_view(), name='beginner'),
    path('advanced', Advanced.as_view(), name='advanced'),
    path('conformation', Conformation.as_view(), name='conformation'),
    path('service-dog', Service.as_view(), name='service-dog'),
    path('rally', Rally.as_view(), name='rally'),
    path('scent', Scent.as_view(), name='scent'),
    path('therapy-dog', Therapy.as_view(), name='therapy-dog'),
]



