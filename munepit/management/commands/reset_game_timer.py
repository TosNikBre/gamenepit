# munepit/management/commands/reset_game_timer.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from munepit.models import GameSettings

class Command(BaseCommand):
    help = 'Сброс таймера игры на текущее время'

    def handle(self, *args, **options):
        settings = GameSettings.objects.first()
        if settings:
            old_time = settings.game_start_time
            settings.game_start_time = timezone.now()
            settings.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Таймер сброшен. Было: {old_time.strftime("%d.%m.%Y %H:%M:%S")}, '
                    f'стало: {settings.game_start_time.strftime("%d.%m.%Y %H:%M:%S")}'
                )
            )
        else:
            GameSettings.objects.create()
            self.stdout.write(self.style.SUCCESS('✅ Созданы настройки игры с текущим временем'))