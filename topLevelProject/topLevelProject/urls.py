from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from baseapp import views as base
from django.conf import settings
from django.conf.urls import handler404, handler500
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('baseapp.urls', namespace='home')),
    path('/classes', include('classes.urls', namespace='classes_main')),
    # path('', include('contactus.urls', namespace='contactus_main')),
    # path('', include('enrollment.urls', namespace='enrollment_main')),
    # path('', include('faqs.urls', namespace='faqs_main')),
]

# handler500 = base_views.error_500
# handler404 = base_views.error_404

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL,
#                           document_root=settings.MEDIA_ROOT)