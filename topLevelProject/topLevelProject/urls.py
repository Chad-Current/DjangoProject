from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from baseapp import views as base
from django.conf import settings
from django.conf.urls import handler404, handler500
from django.conf.urls.static import static
from accounts import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('baseapp.urls', namespace='home_main')),
    path('accounts/', include('accounts.urls')),
    path('', include('dashboard.urls', namespace='account_directory')),
    path('', include('dashboard.urls', namespace='contact_delegation')),
    path('', include('dashboard.urls', namespace='decision_page')),
    path('', include('dashboard.urls', namespace='device_page')),
    path('', include('dashboard.urls', namespace='digital_estate')),
    path('', include('dashboard.urls', namespace='emergency_notes')),
    path('', include('dashboard.urls', namespace='family_awareness')),
    path('', include('dashboard.urls', namespace='profile_page')),
    path('', include('dashboard.urls', namespace='annual_review')),
    path('', include('dashboard.urls', namespace='quarterly_review')),
    path('', include('accounts.urls', namespace='dashboard_page')),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('faqs/', include('faqs.urls', namespace='faqs_page')),
]

# handler500 = base_views.error_500
# handler404 = base_views.error_404

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)