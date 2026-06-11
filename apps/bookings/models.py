# apps/bookings/models.py
import secrets

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.rooms.models import Room


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждено'),
        ('cancelled', 'Отменено'),
        ('completed', 'Завершено'),
        ('rejected', 'Отклонено'),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='bookings', verbose_name='Переговорная')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings',
                             verbose_name='Пользователь')

    title = models.CharField('Название встречи', max_length=200)
    description = models.TextField('Описание', blank=True)

    start_time = models.DateTimeField('Начало')
    end_time = models.DateTimeField('Конец')

    attendees_count = models.PositiveIntegerField('Количество участников', default=1)

    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='confirmed')

    needs_projector = models.BooleanField('Нужен проектор', default=False)
    needs_video_conf = models.BooleanField('Нужна видеоконференция', default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reminder_sent = models.BooleanField('Напоминание отправлено', default=False)

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.room.name} - {self.start_time.strftime('%d.%m %H:%M')} - {self.user.username}"

    def clean(self):
        """Валидация на уровне модели"""
        if self.start_time is None or self.end_time is None:
            return

        if self.start_time >= self.end_time:
            raise ValidationError('Время начала должно быть раньше времени окончания')

        if self.start_time < timezone.now():
            raise ValidationError('Нельзя бронировать прошедшее время')

        duration = (self.end_time - self.start_time).total_seconds() / 3600
        if duration > 4:
            raise ValidationError('Максимальная длительность бронирования - 4 часа')

        if duration < 0.25:
            raise ValidationError('Минимальная длительность бронирования - 15 минут')

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            self.full_clean()
        super().save(*args, **kwargs)


class CalendarFeedToken(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='calendar_feed_token',
        verbose_name='Пользователь'
    )
    token = models.CharField('Токен', max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'Токен подписки на календарь'
        verbose_name_plural = 'Токены подписки на календарь'

    def __str__(self):
        return f'Calendar feed token for {self.user}'

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    @classmethod
    def get_or_create_for_user(cls, user):
        token_obj, _ = cls.objects.get_or_create(
            user=user,
            defaults={'token': cls.generate_token()}
        )
        return token_obj

    def rotate(self):
        self.token = self.generate_token()
        self.save(update_fields=['token', 'updated_at'])
        return self.token
