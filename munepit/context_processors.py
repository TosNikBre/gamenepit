# munepit/context_processors.py
from django.utils import timezone
from .models import GameSettings

def game_timer(request):
    """Контекстный процессор для таймера игры"""
    try:
        start_time = GameSettings.get_start_time()
        current_time = timezone.now()
        
        # Разница в секундах
        elapsed_seconds = int((current_time - start_time).total_seconds())
        
        # Форматирование
        days = elapsed_seconds // 86400
        hours = (elapsed_seconds % 86400) // 3600
        minutes = (elapsed_seconds % 3600) // 60
        seconds = elapsed_seconds % 60
        
        return {
            'game_start_time': start_time,
            'game_elapsed_seconds': elapsed_seconds,
            'game_elapsed_days': days,
            'game_elapsed_hours': hours,
            'game_elapsed_minutes': minutes,
            'game_elapsed_seconds_only': seconds,
            'game_elapsed_formatted': f"{days:02d}:{hours:02d}:{minutes:02d}:{seconds:02d}",
            'game_elapsed_simple': f"{days}д {hours:02d}ч {minutes:02d}м"
        }
    except:
        return {
            'game_start_time': timezone.now(),
            'game_elapsed_seconds': 0,
            'game_elapsed_formatted': "00:00:00:00",
            'game_elapsed_simple': "0д 00ч 00м"
        }