# apps/bookings/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('create/', views.create_booking, name='create_booking'),
    path('export/', views.export_calendar_ics, name='export_calendar'),
    path('feed/<str:token>.ics', views.calendar_feed, name='calendar_feed'),
    path('api/events/', views.get_events_api, name='api_events'),
]
