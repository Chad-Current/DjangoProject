from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from baseapp import views as base
from django.conf import settings
from django.conf.urls import handler404, handler500
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('baseapp.urls', namespace='home_main')),
    path('classes/', include('classes.urls', namespace='classes_main')),
    # path('classes/puppy', include('classes.urls', namespace='classes_puppy')),
    path('contactus/', include('contactus.urls', namespace='contactus_main')),
    path('course/', include('courses.urls', namespace="mini-courses")),
    path('enrollment/', include('enrollment.urls', namespace='enrollment_main')),
    path('faqs/', include('faqs.urls', namespace='faqs_page')),
]

# handler500 = base_views.error_500
# handler404 = base_views.error_404

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)