# apps/rooms/management/commands/create_rooms.py
from django.core.management.base import BaseCommand
from apps.rooms.models import Room


class Command(BaseCommand):
    help = 'Создает тестовые переговорные комнаты'

    def handle(self, *args, **options):
        rooms = [
            {'name': 'Переговорная №1 (Малый зал)', 'capacity': 6, 'floor': 1, 'has_projector': True,
             'has_whiteboard': True},
            {'name': 'Переговорная №2 (Бизнес-зал)', 'capacity': 12, 'floor': 1, 'has_projector': True,
             'has_video_conf': True},
            {'name': 'Переговорная №3 (Совет директоров)', 'capacity': 20, 'floor': 2, 'has_projector': True,
             'has_video_conf': True, 'has_air_conditioning': True},
            {'name': 'Переговорная №4 (Медиа-зал)', 'capacity': 8, 'floor': 2, 'has_projector': True,
             'has_video_conf': True},
            {'name': 'Переговорная №5 (Команда)', 'capacity': 4, 'floor': 3, 'has_whiteboard': True},
        ]

        for room_data in rooms:
            _, created = Room.objects.get_or_create(
                name=room_data['name'],
                defaults=room_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Создана комната: {room_data['name']}'))
            else:
                self.stdout.write(f'• Комната уже существует: {room_data['name']}')

        self.stdout.write(self.style.SUCCESS(f'\n✅ Всего комнат: {Room.objects.count()}'))

