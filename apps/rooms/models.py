# apps/rooms/models.py
from django.db import models


class Room(models.Model):
    name = models.CharField('Название', max_length=255, unique=True)
    capacity = models.PositiveIntegerField('Вместимость')
    floor = models.PositiveSmallIntegerField('Этаж')

    # Удобства
    has_projector = models.BooleanField('Проектор', default=False)
    has_whiteboard = models.BooleanField('Магнитно-маркерная доска', default=False)
    has_video_conf = models.BooleanField('Видеоконференция', default=False)
    has_air_conditioning = models.BooleanField('Кондиционер', default=False)

    photo = models.ImageField('Фото', upload_to='rooms/', blank=True, null=True)
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Активна', default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Переговорная'
        verbose_name_plural = 'Переговорные'
        ordering = ['floor', 'name']

    def __str__(self):
        return f"{self.name} ({self.capacity} чел., {self.floor} этаж)"
