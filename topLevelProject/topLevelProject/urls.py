from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('baseapp.urls', namespace='baseapp_main')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('', include('dashboard.urls', namespace="dashboard_homepage")),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('faqs/', include('faqs.urls', namespace='faqs_page')),
    path('recovery/', include('recovery.urls', namespace="recovery")),
]

# handler500 = base_views.error_500
# handler404 = base_views.error_404

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)