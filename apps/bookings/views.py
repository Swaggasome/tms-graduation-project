# apps/bookings/views.py

import hashlib
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .forms import BookingForm
from .models import Booking, CalendarFeedToken
from .utils import build_bookings_ics
from apps.notifications.tasks import send_booking_reminder
from apps.rooms.models import Room


USER_COLORS = ['#2563eb', '#16a34a', '#9333ea', '#ea580c', '#dc2626', '#0891b2', '#4f46e5', '#0f766e']


def _user_color(user_id):
    return USER_COLORS[user_id % len(USER_COLORS)]


@login_required
def _user_bookings_queryset(request):
    return Booking.objects.filter(user=request.user).select_related('room').order_by('start_time')


def _all_bookings_queryset():
    return Booking.objects.select_related('room', 'user').order_by('start_time')


def _can_edit_booking(user, booking):
    return user.is_staff or booking.user_id == user.id


def _booking_payload(booking, current_user):
    room = booking.room
    owner_name = booking.user.get_full_name() or booking.user.username
    can_edit = _can_edit_booking(current_user, booking)
    color = _user_color(booking.user_id)
    return {
        'id': booking.id,
        'title': booking.title,
        'description': booking.description,
        'room_id': room.id,
        'room': room.name,
        'floor': room.floor,
        'capacity': room.capacity,
        'user': owner_name,
        'user_id': booking.user_id,
        'date': timezone.localtime(booking.start_time).date().isoformat(),
        'start_time': timezone.localtime(booking.start_time).strftime('%H:%M'),
        'end_time': timezone.localtime(booking.end_time).strftime('%H:%M'),
        'start': booking.start_time.isoformat(),
        'end': booking.end_time.isoformat(),
        'attendees_count': booking.attendees_count,
        'status': booking.status,
        'status_display': booking.get_status_display(),
        'needs_projector': booking.needs_projector,
        'needs_video_conf': booking.needs_video_conf,
        'can_edit': can_edit,
        'color': color,
    }


def _ics_response(ics_content, filename='smartmeeting-calendar.ics'):
    response = HttpResponse(ics_content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


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
    feed_token = CalendarFeedToken.get_or_create_for_user(request.user)

    context = {
        'rooms': rooms,
        'my_bookings': my_bookings,
        'statuses': Booking.STATUS_CHOICES,
        'calendar_feed_url': request.build_absolute_uri(
            f'/calendar/feed/{feed_token.token}.ics'
        ),
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
                    return render(request, 'bookings/booking_form.html', {'form': form, 'title': 'Создание бронирования'})

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
                messages.success(request, f'✅ Переговорная "{booking.room.name}" успешно забронирована на {start_datetime.strftime("%d.%m.%Y %H:%M")}!')
                reminder_time = start_datetime - timedelta(hours=1)
                if reminder_time > timezone.now():
                    send_booking_reminder.apply_async(args=[booking.id], eta=reminder_time)
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
    """API для получения событий общего календаря."""
    start = request.GET.get('start')
    end = request.GET.get('end')
    room_id = request.GET.get('room')
    status = request.GET.get('status')
    mine = request.GET.get('mine')

    bookings = _all_bookings_queryset()

    if mine == '1':
        bookings = bookings.filter(user=request.user)
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
        payload = _booking_payload(booking, request.user)
        events.append({
            'id': booking.id,
            'title': f'{booking.title} — {booking.room.name}',
            'start': booking.start_time.isoformat(),
            'end': booking.end_time.isoformat(),
            'color': payload['color'],
            'textColor': '#ffffff',
            'extendedProps': payload,
        })

    return JsonResponse(events, safe=False)


@login_required
def booking_detail_api(request, booking_id):
    booking = get_object_or_404(_all_bookings_queryset(), pk=booking_id)
    return JsonResponse(_booking_payload(booking, request.user))


@login_required
@require_http_methods(['POST'])
def update_booking_api(request, booking_id):
    booking = get_object_or_404(_all_bookings_queryset(), pk=booking_id)
    if not _can_edit_booking(request.user, booking):
        return JsonResponse({'success': False, 'error': 'Можно редактировать только свои бронирования.'}, status=403)
    if booking.status == 'cancelled':
        return JsonResponse({'success': False, 'error': 'Отменённое бронирование нельзя редактировать.'}, status=400)

    form = BookingForm(request.POST, exclude_booking_id=booking.id)
    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    booking.room = form.cleaned_data['room']
    booking.title = form.cleaned_data['title']
    booking.description = form.cleaned_data.get('description', '')
    booking.start_time = form.cleaned_data['start_datetime']
    booking.end_time = form.cleaned_data['end_datetime']
    booking.attendees_count = form.cleaned_data['attendees_count']
    booking.needs_projector = form.cleaned_data['needs_projector']
    booking.needs_video_conf = form.cleaned_data['needs_video_conf']
    booking.save()

    return JsonResponse({'success': True, 'booking': _booking_payload(booking, request.user)})


@login_required
@require_POST
def cancel_booking_api(request, booking_id):
    booking = get_object_or_404(_all_bookings_queryset(), pk=booking_id)
    if not _can_edit_booking(request.user, booking):
        return JsonResponse({'success': False, 'error': 'Можно отменять только свои бронирования.'}, status=403)
    if booking.status == 'cancelled':
        return JsonResponse({'success': True})

    booking.status = 'cancelled'
    booking.save(update_fields=['status', 'updated_at'])
    return JsonResponse({'success': True})


@login_required
def export_calendar_ics(request):
    """Экспорт пользовательских бронирований в iCalendar (.ics)."""
    bookings = _user_bookings_queryset(request).filter(status__in=['confirmed', 'pending'])
    ics_content = build_bookings_ics(
        bookings,
        calendar_name=f'SmartMeeting — {request.user.get_full_name() or request.user.username}'
    )
    return _ics_response(ics_content)


def calendar_feed(request, token):
    """Публичная read-only подписка на календарь по приватному токену."""
    try:
        feed_token = CalendarFeedToken.objects.select_related('user').get(token=token)
    except CalendarFeedToken.DoesNotExist:
        raise Http404('Calendar feed not found')

    bookings = Booking.objects.filter(
        user=feed_token.user,
        status__in=['confirmed', 'pending']
    ).select_related('room').order_by('start_time')

    ics_content = build_bookings_ics(
        bookings,
        calendar_name=f'SmartMeeting — {feed_token.user.get_full_name() or feed_token.user.username}'
    )
    return _ics_response(ics_content, filename='smartmeeting-feed.ics')
