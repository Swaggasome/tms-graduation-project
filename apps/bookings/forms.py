# apps/bookings/forms.py
from django import forms
from django.utils import timezone
from .models import Booking
from apps.rooms.models import Room


class BookingForm(forms.ModelForm):
    date = forms.DateField(
        label='Дата',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    start_time = forms.TimeField(
        label='Время начала',
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time',
            'step': '900'
        })
    )

    end_time = forms.TimeField(
        label='Время окончания',
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time',
            'step': '900'
        })
    )

    class Meta:
        model = Booking
        fields = ['room', 'title', 'description', 'attendees_count',
                  'needs_projector', 'needs_video_conf']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Планёрка по проекту'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Опишите цель встречи...'
            }),
            'attendees_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 2
            }),
            'room': forms.Select(attrs={'class': 'form-control'}),
            'needs_projector': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'needs_video_conf': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.exclude_booking_id = kwargs.pop('exclude_booking_id', None)
        super().__init__(*args, **kwargs)

        self.fields['room'].queryset = Room.objects.filter(is_active=True)
        self.fields['room'].empty_label = 'Выберите переговорную'

        today = timezone.now().date()
        self.fields['date'].widget.attrs['min'] = today.strftime('%Y-%m-%d')
        self.fields['start_time'].widget.attrs['min'] = '09:00'
        self.fields['start_time'].widget.attrs['max'] = '20:00'
        self.fields['end_time'].widget.attrs['min'] = '09:15'
        self.fields['end_time'].widget.attrs['max'] = '21:00'

        if self.initial.get('start_time'):
            start_datetime = self.initial['start_time']
            if start_datetime:
                self.fields['date'].initial = start_datetime.date()
                self.fields['start_time'].initial = start_datetime.time()
                from datetime import timedelta
                end_datetime = start_datetime + timedelta(hours=1)
                self.fields['end_time'].initial = end_datetime.time()

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        room = cleaned_data.get('room')
        attendees_count = cleaned_data.get('attendees_count')

        if room and attendees_count and attendees_count > room.capacity:
            raise forms.ValidationError(
                f'Количество участников ({attendees_count}) превышает вместимость переговорной "{room.name}" ({room.capacity} чел.).'
            )

        if date and start_time and end_time:
            from django.utils.timezone import make_aware
            from datetime import datetime

            start_datetime = make_aware(datetime.combine(date, start_time))
            end_datetime = make_aware(datetime.combine(date, end_time))
            cleaned_data['start_datetime'] = start_datetime
            cleaned_data['end_datetime'] = end_datetime

            if start_datetime >= end_datetime:
                raise forms.ValidationError('Время начала должно быть раньше времени окончания')

            if start_datetime < timezone.now():
                raise forms.ValidationError('Нельзя бронировать прошедшее время')

            duration = (end_datetime - start_datetime).total_seconds() / 3600
            if duration > 4:
                raise forms.ValidationError('Максимальная длительность бронирования - 4 часа')

            if duration < 0.25:
                raise forms.ValidationError('Минимальная длительность бронирования - 15 минут')

            if start_time.hour < 9 or start_time.hour > 20:
                raise forms.ValidationError('Бронирование возможно только с 9:00 до 21:00')

            if room and start_datetime and end_datetime:
                overlapping = Booking.objects.filter(
                    room=room,
                    status__in=['confirmed', 'pending'],
                    start_time__lt=end_datetime,
                    end_time__gt=start_datetime,
                )
                if self.exclude_booking_id:
                    overlapping = overlapping.exclude(pk=self.exclude_booking_id)
                if overlapping.exists():
                    raise forms.ValidationError('Эта переговорная уже занята в выбранное время')

        return cleaned_data
