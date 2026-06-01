# smartmeeting/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.bookings.views import home_view, calendar_view, get_events_api
from apps.accounts.views import register
from smartmeeting.views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),

    # Главная страница
    path('', home_view, name='home'),

    # Календарь и API
    path('calendar/', include('apps.bookings.urls')),
    path('api/events/', get_events_api, name='api_events'),
    path('register/', register, name='register'),

    # Health check for Kubernetes liveness/readiness probes
    path('health/', health_check, name='health_check'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
