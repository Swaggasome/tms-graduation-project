# apps/bookings/views.py

from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import BookingForm
from .models import Booking
from .utils import build_bookings_ics
from apps.notifications.tasks import send_booking_reminder
from apps.rooms.models import Room


STATUS_COLORS = {
    'confirmed': '#198754',
    'pending': '#ffc107',
    'cancelled': '#dc3545',
    'completed': '#6c757d',
    'rejected': '#dc3545',
}


@login_required
def _user_bookings_queryset(request):
    return Booking.objects.filter(user=request.user).select_related('room').order_by('start_time')


def home_view(request):
    """Главная страница"""
    context = {
        'title': 'SmartMeeting - Система бронирования переговорных',
    }

    if request.user.is_authenticated:
        upcoming_bookings = Booking.objects.filter(
            user=request.user,
            start_time__gte=timezone.now(),
            status__in=['confirmed', 'pending']
        ).select_related('room').order_by('start_time')[:5]

        context['upcoming_bookings'] = upcoming_bookings
        context['rooms_count'] = Room.objects.filter(is_active=True).count()
        context['my_bookings_count'] = Booking.objects.filter(user=request.user).count()

    return render(request, 'home.html', context)


@login_required
def calendar_view(request):
    """Календарь бронирований"""
    rooms = Room.objects.filter(is_active=True).order_by('floor', 'name')
    my_bookings = Booking.objects.filter(
        user=request.user,
        start_time__gte=timezone.now(),
        status__in=['confirmed', 'pending']
    ).select_related('room').order_by('start_time')[:10]

    context = {
        'rooms': rooms,
        'my_bookings': my_bookings,
        'statuses': Booking.STATUS_CHOICES,
    }
    return render(request, 'bookings/calendar.html', context)


@login_required
def create_booking(request):
    """Создание нового бронирования"""
    start_param = request.GET.get('start')
    initial_data = {}

    if start_param:
        try:
            if 'T' in start_param:
                start_datetime = datetime.fromisoformat(start_param.replace('Z', '+00:00'))
                start_datetime = start_datetime.replace(tzinfo=None)
                initial_data['start_time'] = start_datetime
        except ValueError:
            pass

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            try:
                start_datetime = form.cleaned_data.get('start_datetime')
                end_datetime = form.cleaned_data.get('end_datetime')

                if not start_datetime or not end_datetime:
                    messages.error(request, '❌ Ошибка: не указано время начала или окончания')
                    return render(request, 'bookings/booking_form.html',
                                  {'form': form, 'title': 'Создание бронирования'})

                booking = Booking(
                    user=request.user,
                    room=form.cleaned_data['room'],
                    title=form.cleaned_data['title'],
                    description=form.cleaned_data.get('description', ''),
                    start_time=start_datetime,
                    end_time=end_datetime,
                    attendees_count=form.cleaned_data['attendees_count'],
                    needs_projector=form.cleaned_data['needs_projector'],
                    needs_video_conf=form.cleaned_data['needs_video_conf'],
                    status='confirmed'
                )

                booking.save()
                messages.success(
                    request,
                    f'✅ Переговорная "{booking.room.name}" успешно забронирована на {start_datetime.strftime("%d.%m.%Y %H:%M")}!'
                )
                reminder_time = start_datetime - timedelta(hours=1)
                if reminder_time > timezone.now():
                    send_booking_reminder.apply_async(
                        args=[booking.id],
                        eta=reminder_time
                    )
                    messages.info(request, '🔔 Напоминание будет отправлено за час до встречи')
                return redirect('calendar')
            except Exception as e:
                messages.error(request, f'❌ Ошибка при создании бронирования: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'❌ {field}: {error}')
    else:
        form = BookingForm(initial=initial_data)

    return render(request, 'bookings/booking_form.html', {
        'form': form,
        'title': 'Создание бронирования'
    })


@login_required
def get_events_api(request):
    """API для получения событий календаря"""
    start = request.GET.get('start')
    end = request.GET.get('end')
    room_id = request.GET.get('room')
    status = request.GET.get('status')

    bookings = _user_bookings_queryset(request)

    if start:
        bookings = bookings.filter(start_time__gte=start)
    if end:
        bookings = bookings.filter(end_time__lte=end)
    if room_id:
        bookings = bookings.filter(room_id=room_id)
    if status:
        bookings = bookings.filter(status=status)
    else:
        bookings = bookings.filter(status__in=['confirmed', 'pending'])

    events = []
    for booking in bookings:
        room = booking.room
        events.append({
            'id': booking.id,
            'title': f'{booking.title} — {room.name}',
            'start': booking.start_time.isoformat(),
            'end': booking.end_time.isoformat(),
            'color': STATUS_COLORS.get(booking.status, '#0d6efd'),
            'textColor': '#ffffff' if booking.status != 'pending' else '#000000',
            'extendedProps': {
                'description': booking.description,
                'room': room.name,
                'floor': room.floor,
                'capacity': room.capacity,
                'attendees_count': booking.attendees_count,
                'status': booking.status,
                'status_display': booking.get_status_display(),
                'needs_projector': booking.needs_projector,
                'needs_video_conf': booking.needs_video_conf,
            }
        })

    return JsonResponse(events, safe=False)


@login_required
def export_calendar_ics(request):
    """Экспорт пользовательских бронирований в iCalendar (.ics)."""
    bookings = _user_bookings_queryset(request).filter(status__in=['confirmed', 'pending'])
    ics_content = build_bookings_ics(
        bookings,
        calendar_name=f'SmartMeeting — {request.user.get_full_name() or request.user.username}'
    )

    response = HttpResponse(ics_content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="smartmeeting-calendar.ics"'
    return response
