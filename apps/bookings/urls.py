# apps/bookings/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('create/', views.create_booking, name='create_booking'),
    path('export/', views.export_calendar_ics, name='export_calendar'),
    path('feed/<str:token>.ics', views.calendar_feed, name='calendar_feed'),
    path('api/events/', views.get_events_api, name='api_events'),
    path('api/booking/<int:booking_id>/', views.booking_detail_api, name='booking_detail_api'),
    path('api/booking/<int:booking_id>/update/', views.update_booking_api, name='booking_update_api'),
    path('api/booking/<int:booking_id>/cancel/', views.cancel_booking_api, name='booking_cancel_api'),
]
