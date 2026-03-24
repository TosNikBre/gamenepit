# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import *
from decimal import Decimal
from datetime import timedelta
import json
from .forms import *
from .models import (
    UserSession, LogEntry, PriceList, Convict, 
    ConstructedBuilding, Credit, Privateer, DynamicPrice,
    Quest, GameSettings, BrickExchange  # Добавьте BrickExchange сюда
)

def _infer_building_type_and_income(building_name, description=''):
    """Определяет тип постройки и доход по названию/описанию прайса."""
    text = f"{building_name or ''} {description or ''}".lower()

    income_map = {
        'маленький магазин': 2,
        'ресторан': 5,
        'таверна': 4,
        'гостиница': 8,
        'рынок': 10,
    }

    for key, value in income_map.items():
        if key in text:
            return 'business', value

    if any(keyword in text for keyword in ('магазин', 'ресторан', 'таверн', 'гостиниц', 'рынок', 'бизнес')):
        return 'business', 5

    if any(keyword in text for keyword in ('фабрик', 'ферм', 'плантац', 'завод')):
        return 'factory', 50

    if any(keyword in text for keyword in ('дом', 'особняк', 'жиль')):
        return 'residential', 0

    return 'other', 0




def _get_player_resource_balance(player_id, resource_key):
    """Подсчет остатка ресурса у игрока по журналу операций."""
    logs = LogEntry.objects.filter(
        table='island',
        player_id=player_id,
        details__resource_key=resource_key,
    )

    balance = 0
    for entry in logs:
        details = entry.details or {}
        quantity = int(details.get('quantity', 0) or 0)

        # Новый формат с явным дельта-изменением склада
        if 'stock_delta' in details:
            balance += int(details.get('stock_delta', 0) or 0)
            continue

        # Старый формат: считаем purchase как приход ресурса игроку
        if entry.action_type == 'purchase':
            balance += quantity

    return max(0, balance)

def player_search(request):
    """Поиск игрока по номеру"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    query = request.GET.get('q', '')
    results = []
    
    if query:
        # Поиск в логах
        transactions = LogEntry.objects.filter(
            Q(player_id__icontains=query)
        ).order_by('-timestamp')[:100]
        
        # Информация по игроку
        player_info = {
            'id': query,
            'transactions_count': LogEntry.objects.filter(player_id=query).count(),
            'total_amount': 0,
            'as_convict': Convict.objects.filter(player_id=query).first(),
            'as_builder': ConstructedBuilding.objects.filter(owner_id=query).count(),
            'as_debtor': Credit.objects.filter(player_id=query).first(),
            'as_privateer': Privateer.objects.filter(player_id=query, is_active=True).first(),
        }
        
        # Подсчет общей суммы
        for t in LogEntry.objects.filter(player_id=query):
            if 'total' in t.details:
                player_info['total_amount'] += float(t.details['total'])
            elif 'amount' in t.details:
                player_info['total_amount'] += float(t.details['amount'])
            elif 'fine' in t.details:
                player_info['total_amount'] += float(t.details['fine'])
        
        results = transactions
    else:
        player_info = None
    
    context = {
        'query': query,
        'results': results,
        'player_info': player_info,
    }
    
    return render(request, 'munepit/player_search.html', context)


def player_detail(request, player_id):
    """Детальная информация об игроке"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Все транзакции игрока
    transactions = LogEntry.objects.filter(
        player_id=player_id
    ).order_by('-timestamp')
    
    # Пагинация
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Статистика по типам
    action_stats = transactions.values('action_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Суммы по месяцам
    monthly_sums = {}
    for t in transactions:
        month = t.timestamp.strftime('%Y-%m')
        amount = 0
        if 'total' in t.details:
            amount = float(t.details['total'])
        elif 'amount' in t.details:
            amount = float(t.details['amount'])
        elif 'fine' in t.details:
            amount = float(t.details['fine'])
        
        if month in monthly_sums:
            monthly_sums[month] += amount
        else:
            monthly_sums[month] = amount
    
    # Информация об игроке
    convict = Convict.objects.filter(player_id=player_id).first()
    buildings = ConstructedBuilding.objects.filter(owner_id=player_id)
    credit = Credit.objects.filter(player_id=player_id).first()
    privateer = Privateer.objects.filter(player_id=player_id, is_active=True).first()
    
    context = {
        'player_id': player_id,
        'page_obj': page_obj,
        'action_stats': action_stats,
        'monthly_sums': monthly_sums,
        'convict': convict,
        'buildings': buildings,
        'credit': credit,
        'privateer': privateer,
        'total_transactions': transactions.count(),
    }
    
    return render(request, 'munepit/player_detail.html', context)
def statistics(request, table=None):
    """Страница статистики"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Период по умолчанию - последние 30 дней
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Базовый запрос
    logs = LogEntry.objects.filter(timestamp__gte=start_date)
    
    # Фильтр по столу
    if table:
        logs = logs.filter(table=table)
        current_table = table
    else:
        current_table = 'all'
    
    # Общая статистика
    total_count = logs.count()
    
    # Статистика по типам действий
    actions_stats = logs.values('action_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Статистика по дням
    daily_stats = logs.extra(
        select={'day': "date(timestamp)"}
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    # Статистика по игрокам
    players_stats = logs.exclude(
        player_id__isnull=True
    ).values('player_id').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Суммы по дням
    daily_sums = []
    for log in logs:
        amount = 0
        if 'total' in log.details:
            amount = float(log.details['total'])
        elif 'amount' in log.details:
            amount = float(log.details['amount'])
        elif 'fine' in log.details:
            amount = float(log.details['fine'])
        
        if amount > 0:
            daily_sums.append({
                'date': log.timestamp.date(),
                'amount': amount
            })
    
    # Группировка сумм по дням
    from collections import defaultdict
    sums_by_day = defaultdict(float)
    for item in daily_sums:
        sums_by_day[item['date']] += item['amount']
    
    # Статистика по столам
    island_stats = {
        'buildings': ConstructedBuilding.objects.count(),
        'convicts': Convict.objects.count(),
    }
    
    britain_stats = {
        'credits': Credit.objects.count(),
        'privateers': Privateer.objects.filter(is_active=True).count(),
    }
    
    # Подготовка данных для графиков
    dates = [item['day'] for item in daily_stats]
    counts = [item['count'] for item in daily_stats]
    
    sum_dates = list(sums_by_day.keys())
    sum_values = list(sums_by_day.values())
    
    context = {
        'total_count': total_count,
        'days': days,
        'current_table': current_table,
        'actions_stats': actions_stats,
        'players_stats': players_stats,
        'island_stats': island_stats,
        'britain_stats': britain_stats,
        'dates': json.dumps([str(d) for d in dates]),
        'counts': json.dumps(counts),
        'sum_dates': json.dumps([str(d) for d in sum_dates]),
        'sum_values': json.dumps(sum_values),
        'table_choices': LogEntry.TABLE_CHOICES,
        'action_types': LogEntry.ACTION_TYPES,
    }
    
    return render(request, 'munepit/statistics.html', context)
from .models import (
    UserSession, LogEntry, PriceList, Convict, ConstructedBuilding,
    Credit, Privateer, DynamicPrice
)
from .forms import *

# munepit/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import LogEntry

def transaction_list(request):
    """Список всех транзакций"""
    # Получаем параметры фильтрации
    table = request.GET.get('table', '')
    action_type = request.GET.get('action_type', '')
    player_id = request.GET.get('player_id', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Базовый запрос
    transactions = LogEntry.objects.all().order_by('-timestamp')
    
    # Применяем фильтры
    if table:
        transactions = transactions.filter(table=table)
    if action_type:
        transactions = transactions.filter(action_type=action_type)
    if player_id:
        transactions = transactions.filter(player_id__icontains=player_id)
    if date_from:
        transactions = transactions.filter(timestamp__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(timestamp__date__lte=date_to)
    
    # Пагинация
    paginator = Paginator(transactions, 20)  # 20 транзакций на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'table': table,
        'action_type': action_type,
        'player_id': player_id,
        'date_from': date_from,
        'date_to': date_to,
        'action_types': LogEntry.ACTION_TYPES,
        'table_choices': LogEntry.TABLE_CHOICES,
    }
    
    return render(request, 'munepit/transaction_list.html', context)


def transaction_detail(request, pk):
    """Детальная информация о транзакции"""
    transaction = get_object_or_404(LogEntry, pk=pk)
    return render(request, 'munepit/transaction_detail.html', {'transaction': transaction})

# Декоратор для проверки авторизации
def session_required(view_func):
    def wrapper(request, *args, **kwargs):
        session_id = request.session.get('session_id')
        if not session_id:
            return redirect('login')
        
        try:
            session = UserSession.objects.get(session_id=session_id, is_active=True)
            request.current_session = session
            request.current_table = session.table
            request.current_user = session.username
        except UserSession.DoesNotExist:
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


# Авторизация
def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            # Создаем сессию
            session = UserSession.objects.create(
                username=form.cleaned_data['username'],
                table=form.cleaned_data['table']
            )
            request.session['session_id'] = str(session.session_id)
            request.session['username'] = session.username
            request.session['table'] = session.table
            
            # Перенаправляем на соответствующий стол
            if session.table == 'island':
                return redirect('island_dashboard')
            else:
                return redirect('britain_dashboard')
    else:
        form = UserLoginForm()
    
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    session_id = request.session.get('session_id')
    if session_id:
        UserSession.objects.filter(session_id=session_id).update(is_active=False)
        request.session.flush()
    
    return redirect('login')


# ================ СТОЛ "ОСТРОВ" ================

@session_required
def island_dashboard(request):
    """Главная страница стола Остров"""
    context = {
        'session': request.current_session,
        'convicts_count': Convict.objects.count(),
        'buildings_count': ConstructedBuilding.objects.count(),
    }
    return render(request, 'island/dashboard.html', context)


@session_required
def island_deal(request):
    """Сделка между игроками (п. 2.8)"""
    if request.method == 'POST':
        form = DealForm(request.POST)
        if form.is_valid():
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='deal',
                details=form.cleaned_data
            )
            
            # Переходим на экран подтверждения
            request.session['pending_deal'] = form.cleaned_data
            return redirect('island_deal_confirm')
    else:
        form = DealForm()
    
    return render(request, 'island/deal.html', {'form': form})


@session_required
def island_deal_confirm(request):
    """Подтверждение сделки"""
    deal_data = request.session.get('pending_deal')
    if not deal_data:
        return redirect('island_deal')
    
    if request.method == 'POST':
        # Действие уже записано в лог на предыдущем шаге
        # Здесь можно добавить дополнительную логику
        messages.success(request, 'Сделка успешно зарегистрирована')
        del request.session['pending_deal']
        return redirect('island_dashboard')
    
    return render(request, 'island/deal_confirm.html', {'deal': deal_data})


@session_required
def island_court(request):
    """Суд - вынесение приговора"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    if request.method == 'POST':
        form = CourtForm(request.POST)
        if form.is_valid():
            convict = form.save(commit=False)
            convict.sentenced_by = request.session.get('username', 'Unknown')
            
            # Сохраняем только если есть срок > 0, иначе не создаем запись
            if convict.sentence_years > 0:
                convict.save()
                
                # Если игрок был капером - деактивируем
                Privateer.objects.filter(player_id=convict.player_id, is_active=True).update(is_active=False)
                
                # Если конфискация - удаляем кредиты
                if convict.confiscation:
                    Credit.objects.filter(player_id=convict.player_id).delete()
            else:
                # Если срок 0, не сохраняем в таблицу каторжников
                print(f"Срок 0 лет - игрок #{convict.player_id} не отправляется на каторгу")
            
            # Запись в лог (всегда, даже при сроке 0)
            LogEntry.objects.create(
                author=request.session.get('username', 'Unknown'),
                table=request.session.get('table', 'island'),
                action_type='court',
                player_id=convict.player_id,
                details={
                    'crime': convict.crime_description,
                    'fine': float(convict.fine_amount),
                    'confiscation': convict.confiscation,
                    'sentence': convict.sentence_years
                }
            )
            
            # Сохраняем в сессию для подтверждения
            request.session['pending_convict'] = {
                'player_id': convict.player_id,
                'player_name': convict.player_name,
                'crime': convict.crime_description,
                'fine': float(convict.fine_amount),
                'confiscation': convict.confiscation,
                'sentence': convict.sentence_years,
                'saved_to_db': convict.sentence_years > 0  # Флаг, был ли сохранен в БД
            }
            
            messages.success(request, 'Приговор вынесен. Подтвердите действие.')
            return redirect('island_court_confirm')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = CourtForm()
    
    context = {
        'form': form,
        'session': request.session,
    }
    
    return render(request, 'island/court.html', context)




@session_required
def island_court_confirm(request):
    """Подтверждение приговора"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    convict_data = request.session.get('pending_convict')
    if not convict_data:
        messages.warning(request, 'Нет данных для подтверждения')
        return redirect('island_court')
    
    if request.method == 'POST':
        # Сообщение в зависимости от наличия срока
        if convict_data['sentence'] > 0:
            messages.success(
                request, 
                f'✅ Приговор вынесен игроку #{convict_data["player_id"]}. Отправлен на каторгу на {convict_data["sentence"]} лет.'
            )
        else:
            messages.success(
                request, 
                f'✅ Приговор вынесен игроку #{convict_data["player_id"]}. Каторга не назначена.'
            )
        
        # Добавляем информацию о конфискации
        if convict_data['confiscation']:
            messages.info(request, '💰 Имущество конфисковано')
        
        # Добавляем информацию о штрафе
        if convict_data['fine'] > 0:
            messages.info(request, f'💰 Назначен штраф: {convict_data["fine"]} ₽')
        
        del request.session['pending_convict']
        
        # ПЕРЕНАПРАВЛЯЕМ НА СТРАНИЦУ ВЕЛИКОБРИТАНИИ
        return redirect('britain_dashboard')
    
    context = {
        'convict': convict_data,
        'session': request.session,
    }
    
    return render(request, 'island/court_confirm.html', context)

@session_required
def island_release(request):
    """Выход с каторги (освобождение)"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    if request.method == 'POST':
        form = ConvictReleaseForm(request.POST)
        if form.is_valid():
            convict = form.cleaned_data['player']
            early_release = form.cleaned_data['early_release']
            
            # Расчет времени на каторге
            time_served = timezone.now() - convict.sentenced_at
            seconds_served = int(time_served.total_seconds())
            days_served = seconds_served // 86400
            hours_served = (seconds_served % 86400) // 3600
            minutes_served = (seconds_served % 3600) // 60
            
            time_served_formatted = f"{days_served}д {hours_served}ч {minutes_served}м"
            
            # Сохраняем данные перед удалением
            player_id = convict.player_id
            player_name = convict.player_name
            sentence = convict.sentence_years
            
            # Удаляем из таблицы каторжников
            convict.delete()
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.session.get('username', 'Unknown'),
                table='island',
                action_type='release',
                player_id=player_id,
                details={
                    'early_release': early_release,
                    'time_served_seconds': seconds_served,
                    'time_served_formatted': time_served_formatted,
                    'sentence_years': sentence
                }
            )
            
            if early_release:
                messages.success(
                    request, 
                    f'✅ Игрок #{player_id} досрочно освобожден с каторги. Провел на каторге: {time_served_formatted}'
                )
            else:
                messages.success(
                    request, 
                    f'✅ Игрок #{player_id} освобожден с каторги по окончании срока. Провел на каторге: {time_served_formatted}'
                )
            
            return redirect('island_release')
        else:
            messages.error(request, '❌ Пожалуйста, исправьте ошибки в форме')
    else:
        form = ConvictReleaseForm()
    
    # Список каторжников для отображения
    convicts = Convict.objects.all().order_by('-sentenced_at')
    
    context = {
        'form': form,
        'convicts': convicts,
        'convicts_count': convicts.count(),
        'session': request.session,
    }
    
    return render(request, 'island/release.html', context)




@session_required
def island_process_resource(request):
    """Обработка ресурса с индивидуальными ценами"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    factories = ConstructedBuilding.objects.filter(
        Q(building_type='factory') |
        Q(building_type='фабрика') |
        Q(building_name__icontains='фабрика')
    ).order_by('building_name')
    
    # Индивидуальные цены обработки для каждого типа ресурса
    processing_prices = {
        # Сырье (базовая обработка)
        'wheat': 2,
        'sugar_cane': 2,
        'coffee': 3,
        'cocoa': 3,
        'tobacco': 4,
        'cotton': 2,
        
        # Полуфабрикаты (средняя обработка)
        'bread': 5,
        'sugar': 4,
        'ground_coffee': 6,
        'cocoa_powder': 6,
        'processed_tobacco': 8,
        'fabric': 5,
        'packaging': 3,
        
        # Готовая продукция (сложная обработка)
        'biscuit': 10,
        'rum': 12,
        'chocolate': 15,
        'cigars': 15,
        
        # Элитная продукция (дорогая обработка)
        'imperial_dessert': 25,
        'coffee_liqueur': 20,
    }
    
    # Названия ресурсов для отображения
    resource_names = {
        'wheat': 'Пшеница',
        'sugar_cane': 'Тростник',
        'coffee': 'Кофейные зерна',
        'cocoa': 'Какао-бобы',
        'tobacco': 'Табачные листья',
        'cotton': 'Хлопок',
        'bread': 'Хлеб',
        'sugar': 'Сахар',
        'ground_coffee': 'Молотый кофе',
        'cocoa_powder': 'Какао-порошок',
        'processed_tobacco': 'Табак',
        'fabric': 'Ткань',
        'packaging': 'Упаковочный товар',
        'biscuit': 'Бисквит',
        'rum': 'Ром',
        'chocolate': 'Шоколад',
        'cigars': 'Сигары',
        'imperial_dessert': 'Имперский десерт',
        'coffee_liqueur': 'Кофейный ликёр',
    }
    
    if request.method == 'POST':
        form = ResourceProcessingForm(request.POST)
        money_input = Decimal(request.POST.get('money_input', 0))
        resource_type = request.POST.get('resource_type', '')
        
        print(f"POST data: {request.POST}")
        print(f"form valid: {form.is_valid()}")
        
        if form.is_valid():
            factory = form.cleaned_data['factory']
            quantity = form.cleaned_data['quantity']
            
            if not resource_type:
                messages.error(request, '❌ Выберите тип ресурса')
                return redirect('island_process_resource')
            
            # Получаем цену обработки для конкретного ресурса
            processing_cost = processing_prices.get(resource_type, 5)  # 5 по умолчанию
            total_cost = quantity * processing_cost
            
            # Проверка средств
            if money_input < total_cost:
                messages.error(
                    request, 
                    f'❌ Недостаточно средств. Требуется: {total_cost:.2f} ₽, внесено: {money_input:.2f} ₽'
                )
                return redirect('island_process_resource')
            
            # Запись в лог
            change = money_input - total_cost
            
            resource_display = resource_names.get(resource_type, resource_type)
            
            LogEntry.objects.create(
                author=request.session.get('username', 'Unknown'),
                table='island',
                action_type='processing',
                player_id=factory.owner_id,
                details={
                    'factory': factory.building_name,
                    'factory_id': factory.id,
                    'quantity': quantity,
                    'resource_type': resource_type,
                    'resource_name': resource_display,
                    'cost_per_unit': processing_cost,
                    'total_cost': float(total_cost),
                    'money_input': float(money_input),
                    'change': float(change),
                }
            )
            
            messages.success(
                request, 
                f'✅ Обработано {quantity} ед. "{resource_display}". Стоимость обработки: {processing_cost}₽/ед. Сдача: {change:.2f} ₽'
            )
            
            return redirect('island_process_resource')
        else:
            messages.error(request, '❌ Пожалуйста, исправьте ошибки в форме')
            print(f"Form errors: {form.errors}")
    else:
        form = ResourceProcessingForm()
    
    # Статистика по владельцам
    owners_count = factories.values('owner_id').distinct().count()
    
    # Последние обработки
    recent_processes = LogEntry.objects.filter(
        action_type='processing',
        table='island'
    ).order_by('-timestamp')[:10]
    
    recent_processes_list = []
    for log in recent_processes:
        recent_processes_list.append({
            'player_id': log.player_id,
            'quantity': log.details.get('quantity', 0),
            'resource_type': log.details.get('resource_name', log.details.get('resource_type', 'unknown')),
            'cost_per_unit': log.details.get('cost_per_unit', 5),
            'timestamp': log.timestamp
        })
    
    context = {
        'form': form,
        'factories': factories,
        'factories_count': factories.count(),
        'owners_count': owners_count,
        'processing_prices': processing_prices,
        'resource_names': resource_names,
        'recent_processes': recent_processes_list,
        'session': request.session,
    }
    
    return render(request, 'island/process_resource.html', context)


@session_required
def island_build(request):
    """Постройка здания"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Получаем все здания из прайс-листа
    buildings_available = PriceList.objects.filter(
        Q(category='building') | 
        Q(category='factory') | 
        Q(category='business')
    ).order_by('base_price')
    
    # Уже построенные здания
    buildings = ConstructedBuilding.objects.all().order_by('-built_at')
    
    if request.method == 'POST':
        form = BuildingForm(request.POST)
        
        # Получаем money_input из POST
        money_input = Decimal(request.POST.get('money_input', 0))
        
        print(f"POST data: {request.POST}")  # Отладка
        print(f"money_input: {money_input}")
        
        if form.is_valid():
            building = form.cleaned_data['building']
            player_id = form.cleaned_data['player_id']
            
            total = building.base_price  # Decimal
            
            print(f"total: {total}, money_input: {money_input}")
            
            # Проверяем достаточно ли денег
            if money_input < total:
                messages.error(
                    request, 
                    f'❌ Недостаточно средств. Требуется: {total:.2f} ₽, внесено: {money_input:.2f} ₽'
                )
                # Возвращаем форму с сохраненными данными
                form = BuildingForm(initial={
                    'building': building.id,
                    'player_id': player_id,
                })
                context = {
                    'form': form,
                    'buildings_available': buildings_available,
                    'buildings': buildings,
                    'session': request.session,
                    'money_input': float(money_input),  # Передаем обратно в шаблон
                }
                return render(request, 'island/build.html', context)
            
            # Создаем здание
            constructed = ConstructedBuilding.objects.create(
                building_name=building.name,
                building_type=building.category,
                owner_id=player_id,
                built_by=request.session.get('username', 'Unknown'),
                cost=total,
                income_per_minute=5 if building.category == 'business' else 0
            )
            
            # Расчет сдачи
            change = money_input - total
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.session.get('username', 'Unknown'),
                table='island',
                action_type='building',
                player_id=player_id,
                details={
                    'building': building.name,
                    'building_id': building.id,
                    'cost': float(total),
                    'money_input': float(money_input),
                    'change': float(change),
                }
            )
            
            messages.success(
                request, 
                f'✅ Здание "{building.name}" построено для игрока #{player_id}. Сдача: {change:.2f} ₽'
            )
            
            return redirect('island_build')
        else:
            messages.error(request, '❌ Пожалуйста, исправьте ошибки в форме')
            print(f"Ошибки формы: {form.errors}")
    else:
        form = BuildingForm()
    
    # Количество уникальных владельцев
    owners_count = buildings.values('owner_id').distinct().count()
    
    context = {
        'form': form,
        'buildings_available': buildings_available,
        'buildings': buildings,
        'owners_count': owners_count,
        'session': request.session,
    }
    
    return render(request, 'island/build.html', context)




@session_required
def island_build_confirm(request):
    """Подтверждение постройки здания с выдачей сдачи"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    build_data = request.session.get('pending_building')
    
    if not build_data:
        messages.warning(request, 'Нет данных для подтверждения')
        return redirect('island_build')
    
    if request.method == 'POST':
        money_input = Decimal(request.POST.get('money_input', 0))
        cost = Decimal(str(build_data['cost']))
        
        if money_input >= cost:
            change = money_input - cost
            
            # Создаем запись о построенном здании
            constructed = ConstructedBuilding.objects.create(
                building_name=build_data['building_name'],
                building_type='other',  # По умолчанию
                owner_id=build_data['player_id'],
                built_by=request.session.get('username', 'Unknown'),
                cost=cost,
                income_per_minute=5  # Значение по умолчанию
            )
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.session.get('username', 'Unknown'),
                table='island',
                action_type='building',
                player_id=build_data['player_id'],
                details={
                    'building': build_data['building_name'],
                    'building_id': build_data['building_id'],
                    'cost': float(cost),
                    'money_input': float(money_input),
                    'change': float(change),
                }
            )
            
            messages.success(
                request, 
                f'Здание "{build_data["building_name"]}" построено для игрока #{build_data["player_id"]}. '
                f'Сдача: {change:.2f} ₽'
            )
            
            del request.session['pending_building']
            return redirect('island_dashboard')
        else:
            messages.error(request, f'Недостаточно средств. Требуется: {cost:.2f} ₽')
    
    context = {
        'build': build_data,
        'session': request.session,
    }
    
    return render(request, 'island/build_confirm.html', context)
@session_required
def island_process_resource(request):
    """Обработка ресурса на фабрике"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Получаем все фабрики
    factories = ConstructedBuilding.objects.filter(building_type='factory').order_by('building_name')
    
    # Получаем стоимость обработки
    try:
        processing_cost_obj = PriceList.objects.filter(name='Обработка ресурса').first()
        processing_cost = float(processing_cost_obj.base_price) if processing_cost_obj else 5.0
    except:
        processing_cost = 5.0
    
    # Статистика по владельцам фабрик
    factories_by_owner = {}
    for factory in factories:
        owner = factory.owner_id
        if owner not in factories_by_owner:
            factories_by_owner[owner] = {
                'owner_id': owner,
                'factory_count': 0,
                'factories': []
            }
        factories_by_owner[owner]['factory_count'] += 1
        factories_by_owner[owner]['factories'].append({
            'id': factory.id,
            'name': factory.building_name
        })
    
    owners_with_factories = list(factories_by_owner.values())
    owners_count = len(owners_with_factories)
    factories_count = factories.count()
    
    # Последние обработки из логов
    recent_processes = LogEntry.objects.filter(
        action_type='processing',
        table='island'
    ).order_by('-timestamp')[:10]
    
    # Подготовка данных для отображения
    recent_processes_list = []
    for log in recent_processes:
        recent_processes_list.append({
            'player_id': log.player_id,
            'quantity': log.details.get('quantity', 0),
            'timestamp': log.timestamp
        })
    
    if request.method == 'POST':
        form = ResourceProcessingForm(request.POST)
        if form.is_valid():
            factory = form.cleaned_data['factory']
            quantity = form.cleaned_data['quantity']
            resource_type = request.POST.get('resource_type', 'unknown')
            
            total = quantity * processing_cost
            
            # Сохраняем в сессию
            request.session['pending_processing'] = {
                'factory_id': factory.id,
                'factory_name': factory.building_name,
                'owner_id': factory.owner_id,
                'quantity': quantity,
                'cost_per_unit': processing_cost,
                'total': total,
                'resource_type': resource_type,
            }
            
            messages.success(request, 'Данные приняты. Перейдите к подтверждению.')
            return redirect('island_process_confirm')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = ResourceProcessingForm()
    
    context = {
        'form': form,
        'factories': factories,
        'factories_count': factories_count,
        'processing_cost': processing_cost,
        'recent_processes': recent_processes_list,
        'owners_with_factories': owners_with_factories,
        'owners_count': owners_count,
        'session': request.session,
    }
    
    return render(request, 'island/process_resource.html', context)

@session_required
def island_process_confirm(request):
    """Подтверждение обработки ресурса - максимально просто"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Получаем данные из сессии
    process_data = request.session.get('pending_processing')
    
    # Если нет данных - возвращаем назад
    if not process_data:
        messages.warning(request, 'Нет данных для подтверждения')
        return redirect('island_process_resource')
    
    # Если нажали кнопку подтвердить
    if request.method == 'POST':
        # Записываем в лог
        LogEntry.objects.create(
            author=request.session.get('username', 'Unknown'),
            table='island',
            action_type='processing',
            player_id=process_data['owner_id'],
            details={
                'factory': process_data['factory_name'],
                'factory_id': process_data['factory_id'],
                'quantity': process_data['quantity'],
                'cost_per_unit': process_data['cost_per_unit'],
                'total': process_data['total'],
                'resource_type': process_data.get('resource_type', 'unknown'),
            }
        )
        
        messages.success(request, '✅ Обработка подтверждена')
        
        # Очищаем сессию
        del request.session['pending_processing']
        
        return redirect('island_process_resource')
    
    # Показываем страницу подтверждения
    return render(request, 'island/process_confirm.html', {'process': process_data})

@session_required
def island_profit(request):

    """Получение прибыли от бизнеса"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Автонормализация старых построек: раньше все создавались как 'other'
    normalized = 0
    for building in ConstructedBuilding.objects.filter(building_type='other'):
        inferred_type, inferred_income = _infer_building_type_and_income(building.building_name)
        if inferred_type != 'other':
            building.building_type = inferred_type
            if inferred_type in ('business', 'factory') and building.income_per_minute <= 0:
                default_income = 5 if inferred_type == 'business' else 50
                building.income_per_minute = inferred_income or default_income
                building.save(update_fields=['building_type', 'income_per_minute'])
            else:
                building.save(update_fields=['building_type'])
            normalized += 1

    if normalized:
        print(f"Нормализовано построек по типам: {normalized}")

    # Получаем объекты для начисления прибыли (бизнесы и фабрики)
    businesses = ConstructedBuilding.objects.filter(
        building_type__in=['business', 'factory']
    ).order_by('-last_profit_collected')
    
    # Для отладки - выводим в консоль
    print(f"Найдено бизнесов: {businesses.count()}")
    for b in businesses:
        print(f"  - {b.building_name} (ID: {b.id}, владелец: {b.owner_id}, доход: {b.income_per_minute} ₽/мин)")
    
    # Статистика
    total_businesses = businesses.count()
    active_businesses = businesses.filter(
        last_profit_collected__gte=timezone.now() - timedelta(days=1)
    ).count()
    
    # Топ бизнесов по доходу
    top_businesses = businesses.order_by('-income_per_minute')[:5]
    
    # Последние получения прибыли из логов
    recent_profits = LogEntry.objects.filter(
        action_type='profit',
        table='island'
    ).order_by('-timestamp')[:10]
    
    # Общая прибыль за сегодня
    today = timezone.now().date()
    today_profits = LogEntry.objects.filter(
        action_type='profit',
        table='island',
        timestamp__date=today
    )
    total_profit_today = sum(float(p.details.get('profit', 0)) for p in today_profits)
    
    if request.method == 'POST':
        form = BusinessProfitForm(request.POST)
        if form.is_valid():
            business = form.cleaned_data['business']
            
            # Расчет прибыли
            if business.building_type == 'factory':
                minutes = (timezone.now() - business.last_profit_collected).total_seconds() / 60
                factory_income = float(business.income_per_minute or 50)
                profit = max(0, round(minutes * factory_income, 2))
            else:
                profit = business.calculate_accumulated_profit()
            
            if profit > 0:
                # Сброс таймера
                business.reset_profit_timer()
                
                # Запись в лог
                LogEntry.objects.create(
                    author=request.session.get('username', 'Unknown'),
                    table='island',
                    action_type='profit',
                    player_id=business.owner_id,
                    details={
                        'business': business.building_name,
                        'business_id': business.id,
                        'building_type': business.building_type,
                        'profit': profit,
                        'income_per_minute': float(business.income_per_minute),
                    }
                )
                
                source_label = 'фабрики' if business.building_type == 'factory' else 'бизнеса'
                messages.success(
                    request, 
                    f'Прибыль {profit:.2f} ₽ получена от {source_label} "{business.building_name}" для игрока #{business.owner_id}'
                )
            else:
                messages.warning(request, 'Прибыль еще не накоплена')
            
            return redirect('island_profit')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
            print(f"Ошибки формы: {form.errors}")
    else:
        form = BusinessProfitForm()
    
    context = {
        'form': form,
        'businesses': businesses,  # Передаем все бизнесы в шаблон
        'total_businesses': total_businesses,
        'active_businesses': active_businesses,
        'top_businesses': top_businesses,
        'recent_profits': recent_profits,
        'total_profit_today': total_profit_today,
        'session': request.session,
    }
    
    return render(request, 'island/profit.html', context)

@session_required
def island_demolish(request):
    """Снос здания (п. 3.5)"""
    if request.method == 'POST':
        form = BuildingDemolitionForm(request.POST)
        if form.is_valid():
            building = form.cleaned_data['building']
            demolisher = form.cleaned_data['demolisher_id']
            
            accumulated = 0
            if building.building_type == 'business':
                accumulated = building.calculate_accumulated_profit()
            
            # Сохраняем данные перед удалением
            building_data = {
                'id': building.id,
                'name': building.building_name,
                'type': building.building_type,
                'owner': building.owner_id,
                'accumulated': accumulated
            }
            
            # Удаляем здание
            building.delete()
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='demolition',
                player_id=demolisher,
                details={
                    'building': building_data['name'],
                    'building_type': building_data['type'],
                    'owner': building_data['owner'],
                    'demolisher': demolisher,
                    'accumulated_profit': accumulated
                }
            )
            
            request.session['pending_demolition'] = building_data
            return redirect('island_demolish_confirm')
    else:
        form = BuildingDemolitionForm()
    
    buildings = ConstructedBuilding.objects.order_by('-built_at')

    demolitions_qs = LogEntry.objects.filter(
        action_type='demolition',
        table='island'
    ).order_by('-timestamp')
    recent_demolitions = []
    for entry in demolitions_qs[:20]:
        details = entry.details or {}
        recent_demolitions.append({
            'building_name': details.get('building', '—'),
            'owner': details.get('owner', '—'),
            'accumulated_profit': float(details.get('accumulated_profit', 0) or 0),
            'timestamp': entry.timestamp,
        })

    return render(request, 'island/demolish.html', {
        'form': form,
        'buildings': buildings,
        'recent_demolitions': recent_demolitions,
    })


@session_required
def island_demolish_confirm(request):
    """Подтверждение сноса"""
    demolish_data = request.session.get('pending_demolition')
    if not demolish_data:
        return redirect('island_demolish')
    
    if request.method == 'POST':
        messages.success(request, 'Здание снесено')
        del request.session['pending_demolition']
        return redirect('island_dashboard')
    
    return render(request, 'island/demolish_confirm.html', {'demolish': demolish_data})



def island_purchase_resource(request):
    """Покупка ресурса (без подтверждения)"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    resources = PriceList.objects.filter(category='resource')
    
    # Последние покупки для отображения
    recent_purchases = LogEntry.objects.filter(
        action_type='purchase',
        table='island'
    ).order_by('-timestamp')[:10]
    
    recent_purchases_list = []
    for p in recent_purchases:
        recent_purchases_list.append({
            'player_id': p.player_id,
            'resource': p.details.get('resource', 'Неизвестно'),
            'quantity': p.details.get('quantity', 0),
            'total': p.details.get('total', 0),
            'timestamp': p.timestamp
        })
    
    if request.method == 'POST':
        form = ResourcePurchaseForm(request.POST)
        money_input = Decimal(request.POST.get('money_input', 0))  # Это Decimal
        
        if form.is_valid():
            resource = form.cleaned_data['resource']
            player_id = form.cleaned_data['player_id']
            quantity = form.cleaned_data['quantity']
            
            # Получаем цену как Decimal из модели
            price_per_unit = resource.base_price  # Это Decimal
            
            # Все вычисления делаем в Decimal
            total = price_per_unit * quantity  # Decimal * int = Decimal
            
            # Проверяем достаточно ли денег (оба Decimal)
            if money_input < total:
                messages.error(
                    request, 
                    f'❌ Недостаточно средств. Требуется: {total:.2f} ₽, внесено: {money_input:.2f} ₽'
                )
                return redirect('island_purchase_resource')
            
            # СРАЗУ ЗАПИСЫВАЕМ В ЛОГ (конвертируем в float для JSON)
            change = money_input - total  # Decimal - Decimal = Decimal
            
            LogEntry.objects.create(
                author=request.session.get('username', 'Unknown'),
                table='island',
                action_type='purchase',
                player_id=player_id,
                details={
                    'resource': resource.name,
                    'resource_id': resource.id,
                    'quantity': quantity,
                    'price_per_unit': float(price_per_unit),  # Decimal -> float
                    'total': float(total),  # Decimal -> float
                    'money_input': float(money_input),  # Decimal -> float
                    'change': float(change),  # Decimal -> float
                }
            )
            
            # Сообщение об успехе (конвертируем в float для форматирования)
            if change > 0:
                messages.success(
                    request, 
                    f'✅ Покупка завершена! Сдача: {float(change):.2f} ₽'
                )
            else:
                messages.success(
                    request, 
                    '✅ Покупка завершена!'
                )
            
            return redirect('island_purchase_resource')
        else:
            messages.error(request, '❌ Пожалуйста, исправьте ошибки в форме')
    else:
        form = ResourcePurchaseForm()
    
    context = {
        'form': form,
        'resources': resources,
        'recent_purchases': recent_purchases_list,
        'session': request.session,
    }
    
    return render(request, 'island/purchase_resource.html', context)


# ================ СТОЛ "ВЕЛИКОБРИТАНИЯ" ================

@session_required
def britain_dashboard(request):
    """Дашборд Великобритании"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Получаем текущую дату для фильтрации
    today = timezone.now().date()
    
    # Статистика по кредитам
    credits = Credit.objects.all()
    credits_count = credits.count()
    
    # Просроченные кредиты (более 10 минут)
    overdue_credits = 0
    for credit in credits:
        if credit.is_overdue():
            overdue_credits += 1
    
    # Статистика по каперам
    active_privateers = Privateer.objects.filter(is_active=True)
    privateers_count = active_privateers.count()
    
    # Каперы с жалобами
    privateers_with_complaints = active_privateers.filter(complaints__gt=0).count()
    
    # Сделки за сегодня
    today_deals = LogEntry.objects.filter(
        table='britain',
        timestamp__date=today
    ).count()
    
    # Сделки между игроками за сегодня
    today_player_deals = LogEntry.objects.filter(
        action_type='deal',
        timestamp__date=today
    ).count()
    
    # Последние сделки между игроками
    recent_player_deals = LogEntry.objects.filter(
        action_type='deal'
    ).order_by('-timestamp')[:10]
    
    # Данные о каторжниках (для блока судов)
    convicts_count = Convict.objects.count()
    convicts = Convict.objects.all().order_by('-sentenced_at')[:5]
    
    # Для отладки - выводим информацию в консоль
    
    
    context = {
        'session': request.session,
        'credits_count': credits_count,
        'privateers_count': privateers_count,
        'today_deals': today_deals,
        'overdue_credits': overdue_credits,
        'privateers_with_complaints': privateers_with_complaints,
        'today_player_deals': today_player_deals,
        'recent_player_deals': recent_player_deals,
        'convicts_count': convicts_count,
        'convicts': convicts,
        'active_privateers': active_privateers,  # Передаем для отображения в таблице
    }
    
    return render(request, 'britain/dashboard.html', context)

@session_required
def britain_sale(request):
    """Продажа товара с динамической ценой"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Получаем все товары (goods) и ресурсы (resource) из базы
    all_goods = PriceList.objects.filter(
        Q(category='goods') | Q(category='resource')
    ).order_by('category', 'name')
    
    # Для отладки
    print(f"Найдено товаров: {all_goods.count()}")
    for g in all_goods:
        print(f"  - {g.name} ({g.category}): {g.base_price}₽")
    
    # Создаем или обновляем динамические цены для всех товаров
    for good in all_goods:
        price, created = DynamicPrice.objects.get_or_create(
            good_name=good.name,
            defaults={
                'current_price': good.base_price,
                'pmax': good.pmax or good.base_price,
                'pmin': good.pmin or 1,
                'n_for_drop': good.n_for_drop or 5,
                't_recovery': good.t_recovery or 300,
            }
        )
        # Проверяем восстановление цены
        price.check_recovery()
    
    # Последние продажи
    recent_sales = LogEntry.objects.filter(
        action_type='sale',
        table='britain'
    ).order_by('-timestamp')[:10]
    
    recent_sales_list = []
    for sale in recent_sales:
        recent_sales_list.append({
            'good': sale.details.get('good_name', 'Неизвестно'),
            'quantity': sale.details.get('quantity', 0),
            'total': sale.details.get('total_price', 0),
            'player_id': sale.player_id,
            'timestamp': sale.timestamp,
        })
    
    if request.method == 'POST':
        form = GoodsSaleForm(request.POST)
        if form.is_valid():
            good = form.cleaned_data['good']
            player_id = form.cleaned_data['player_id']
            quantity = form.cleaned_data['quantity']
            
            # Получаем динамическую цену
            try:
                price_obj = DynamicPrice.objects.get(good_name=good.name)
            except DynamicPrice.DoesNotExist:
                price_obj = DynamicPrice.objects.create(
                    good_name=good.name,
                    current_price=good.base_price,
                    pmax=good.pmax or good.base_price,
                    pmin=good.pmin or 1,
                    n_for_drop=good.n_for_drop or 5,
                    t_recovery=good.t_recovery or 300,
                )
            
            # Получаем цену для данного количества
            total_price = price_obj.get_price_for_quantity(quantity)
            
            # Фиксируем продажу
            new_price = price_obj.record_sale(quantity)
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.session.get('username', 'Unknown'),
                table='britain',
                action_type='sale',
                player_id=player_id,
                details={
                    'good': good.name,
                    'good_id': good.id,
                    'category': good.category,
                    'quantity': quantity,
                    'total_price': float(total_price),
                    'new_price': new_price,
                }
            )
            
            messages.success(
                request, 
                f'✅ Продажа оформлена. Выплатить игроку #{player_id}: {total_price:.2f} ₽'
            )
            return redirect('britain_sale')
        else:
            messages.error(request, '❌ Пожалуйста, исправьте ошибки в форме')
    else:
        form = GoodsSaleForm()
    
    # Разделяем товары по категориям для отображения
    resources = all_goods.filter(category='resource')
    goods = all_goods.filter(category='goods')
    
    # Текущие цены для отображения
    current_prices = {}
    for good in all_goods:
        try:
            price_obj = DynamicPrice.objects.get(good_name=good.name)
            current_prices[good.id] = {
                'name': good.name,
                'category': good.category,
                'current': float(price_obj.current_price),
                'pmax': float(price_obj.pmax),
                'pmin': float(price_obj.pmin),
                'n': price_obj.n_for_drop,
                't': price_obj.t_recovery,
                'sales': price_obj.sales_count,
            }
        except DynamicPrice.DoesNotExist:
            current_prices[good.id] = {
                'name': good.name,
                'category': good.category,
                'current': float(good.base_price),
                'pmax': float(good.pmax or good.base_price),
                'pmin': float(good.pmin or 1),
                'n': good.n_for_drop or 5,
                't': good.t_recovery or 300,
                'sales': 0,
            }
    
    context = {
        'form': form,
        'all_goods': all_goods,
        'resources': resources,
        'goods': goods,
        'current_prices': current_prices,
        'recent_sales': recent_sales_list,
        'session': request.session,
    }
    
    return render(request, 'britain/sale.html', context)


@session_required
def britain_sale_confirm(request):
    """Подтверждение продажи ресурса игроком в Великобритании"""
    sale_data = request.session.get('pending_britain_sale')
    if not sale_data:
        return redirect('britain_sale')

    if request.method == 'POST':
        required_quantity = int(sale_data.get('quantity', 0) or 0)

        dynamic_price, _ = DynamicPrice.objects.get_or_create(
            good_name=sale_data['good'],
            defaults={
                'current_price': sale_data['price_per_unit'],
                'pmax': sale_data['price_per_unit'],
                'n_for_drop': 10,
                't_recovery': 300
            }
        )
        dynamic_price.check_recovery()
        dynamic_price.record_sale(required_quantity)

        LogEntry.objects.create(
            author=request.current_user,
            table=request.current_table,
            action_type='sale',
            player_id=sale_data['player_id'],
            details={
                'good': sale_data['good'],
                'resource_key': sale_data['good'],
                'quantity': required_quantity,
                'price_per_unit': sale_data['price_per_unit'],
                'total': sale_data['total'],
                'payout_to_player': sale_data['total'],
                'operation': 'resource_buyback',
                'stock_delta': -required_quantity,
            }
        )

        del request.session['pending_britain_sale']
        messages.success(request, f"Операция подтверждена. Выплатить игроку: {sale_data['total']:.2f}")
        return redirect('britain_dashboard')

    return render(request, 'britain/sale_confirm.html', {'sale': sale_data})


@session_required
def britain_ship_deal(request):
    """Сделка с кораблем"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Получаем все корабли
    ships = PriceList.objects.filter(category='ship').order_by('base_price')
    
    # Для отладки
    print(f"Найдено кораблей: {ships.count()}")
    for ship in ships:
        print(f"  - {ship.name}: {ship.base_price} ₽")
    
    # Последние сделки
    recent_deals = LogEntry.objects.filter(
        action_type='ship_deal',
        table='britain'
    ).order_by('-timestamp')[:10]
    
    recent_deals_list = []
    for deal in recent_deals:
        recent_deals_list.append({
            'ship': deal.details.get('ship', 'Неизвестно'),
            'type': 'покупка' if deal.details.get('deal_type') == 'buy' else 'продажа',
            'amount': deal.details.get('total', 0),
            'player_id': deal.player_id,
            'timestamp': deal.timestamp
        })
    
    if request.method == 'POST':
        form = ShipDealForm(request.POST)
        
        # Отладка
        print("POST data:", request.POST)
        print("Form valid:", form.is_valid())
        
        if form.is_valid():
            ship = form.cleaned_data['ship']
            deal_type = form.cleaned_data['deal_type']
            player_id = form.cleaned_data['player_id']
            money_input = form.cleaned_data.get('money_input', Decimal('0'))
            
            base_price = ship.base_price
            
            if deal_type == 'buy':
                # ПОКУПКА - игрок платит, модератор получает деньги
                total = base_price
                
                if money_input < total:
                    messages.error(
                        request, 
                        f'❌ Недостаточно средств для покупки. Требуется: {total:.2f} ₽, внесено: {money_input:.2f} ₽'
                    )
                    return redirect('britain_ship_deal')
                
                change = money_input - total
                
                LogEntry.objects.create(
                    author=request.session.get('username', 'Unknown'),
                    table='britain',
                    action_type='ship_deal',
                    player_id=player_id,
                    details={
                        'ship': ship.name,
                        'ship_id': ship.id,
                        'deal_type': 'buy',
                        'action': 'покупка',
                        'base_price': float(base_price),
                        'total': float(total),
                        'money_input': float(money_input),
                        'change': float(change)
                    }
                )
                
                messages.success(
                    request, 
                    f'✅ Корабль "{ship.name}" куплен игроком #{player_id}. Сдача: {change:.2f} ₽'
                )
                
            else:  # sell - ПРОДАЖА
                # Продажа - модератор платит игроку 50% от стоимости
                total = base_price * Decimal('0.5')
                
                LogEntry.objects.create(
                    author=request.session.get('username', 'Unknown'),
                    table='britain',
                    action_type='ship_deal',
                    player_id=player_id,
                    details={
                        'ship': ship.name,
                        'ship_id': ship.id,
                        'deal_type': 'sell',
                        'action': 'продажа',
                        'base_price': float(base_price),
                        'total': float(total)
                    }
                )
                
                messages.success(
                    request, 
                    f'✅ Корабль "{ship.name}" продан игроком #{player_id}. Выплачено: {total:.2f} ₽'
                )
            
            return redirect('britain_ship_deal')
        else:
            print("Form errors:", form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ShipDealForm()
    
    # Преобразуем для шаблона
    ships_data = []
    for ship in ships:
        ships_data.append({
            'id': ship.id,
            'name': ship.name,
            'price': float(ship.base_price),
            'description': ship.description
        })
    
    context = {
        'form': form,
        'ships': ships_data,
        'recent_deals': recent_deals_list,
        'session': request.session,
    }
    
    return render(request, 'britain/ship_deal.html', context)





@session_required
def britain_brick_exchange(request):
    """Обмен кирпичей на стартовый корабль"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Получаем доступные стартовые корабли из прайс-листа
    starter_ships = PriceList.objects.filter(category='starter_ship')
    
    # Последние обмены
    recent_exchanges = BrickExchange.objects.all().order_by('-exchanged_at')[:10]
    
    if request.method == 'POST':
        player_id = request.POST.get('player_id')
        ship_type = request.POST.get('ship_type')
        bricks_count = int(request.POST.get('bricks_count', 10))
        
        if not player_id or not ship_type:
            messages.error(request, '❌ Заполните все поля')
            return redirect('britain_brick_exchange')
        
        # Название корабля для отображения
        ship_names = {
            'basic': 'Люггер (базовый)',
            'armed': 'Люггер (с орудиями)',
        }
        ship_name = ship_names.get(ship_type, 'Неизвестный корабль')
        
        # Записываем обмен
        exchange = BrickExchange.objects.create(
            player_id=player_id,
            ship_type=ship_type,
            bricks_count=bricks_count,
            exchanged_by=request.session.get('username', 'Unknown')
        )
        
        # Запись в лог
        LogEntry.objects.create(
            author=request.session.get('username', 'Unknown'),
            table='britain',
            action_type='brick_exchange',
            player_id=player_id,
            details={
                'ship': ship_name,
                'ship_type': ship_type,
                'bricks': bricks_count,
                'exchange_id': exchange.id
            }
        )
        
        messages.success(
            request, 
            f'✅ Игрок #{player_id} получил {ship_name} за {bricks_count} кирпичей'
        )
        
        return redirect('britain_brick_exchange')
    
    context = {
        'starter_ships': starter_ships,
        'recent_exchanges': recent_exchanges,
        'session': request.session,
    }
    
    return render(request, 'britain/brick_exchange.html', context)
@session_required
def britain_factory_work(request):
    """Работа на заводе - модератор платит игроку"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Получаем цену шестерни
    try:
        gear_item = PriceList.objects.filter(name='Шестерня').first()
        gear_price = float(gear_item.base_price) if gear_item else 2
    except:
        gear_price = 2
    
    if request.method == 'POST':
        form = FactoryWorkForm(request.POST)
        if form.is_valid():
            player_id = form.cleaned_data['player_id']
            quantity = form.cleaned_data['quantity']
            
            # Расчет суммы к выплате (модератор платит игроку)
            total_payment = quantity * gear_price
            
            # Сохраняем в сессию для подтверждения
            request.session['pending_factory_work'] = {
                'player_id': player_id,
                'quantity': quantity,
                'price_per_unit': gear_price,
                'total_payment': total_payment,
            }
            
            return redirect('britain_factory_work_confirm')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = FactoryWorkForm()
    
    context = {
        'form': form,
        'gear_price': gear_price,
        'session': request.session,
    }
    
    return render(request, 'britain/factory_work.html', context)

def britain_factory_work_confirm(request):
    """Подтверждение выплаты за работу на заводе"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    work_data = request.session.get('pending_factory_work')
    
    if not work_data:
        messages.warning(request, 'Нет данных для подтверждения')
        return redirect('britain_factory_work')
    
    if request.method == 'POST':
        # Запись в лог
        LogEntry.objects.create(
            author=request.session.get('username', 'Unknown'),
            table='britain',
            action_type='factory_work',
            player_id=work_data['player_id'],
            details={
                'quantity': work_data['quantity'],
                'price_per_unit': work_data['price_per_unit'],
                'total_payment': work_data['total_payment'],
                'payment_type': 'moderator_pays_player'
            }
        )
        
        messages.success(
            request, 
            f'Выплачено {work_data["total_payment"]:.2f} ₽ игроку #{work_data["player_id"]} за {work_data["quantity"]} шестерен'
        )
        
        del request.session['pending_factory_work']
        return redirect('britain_factory_work')
    
    return render(request, 'britain/factory_work_confirm.html', {'work': work_data})


@session_required
def britain_credits(request):
    """Таблица кредитов (п. 2.4)"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    credits = list(Credit.objects.all())
    now = timezone.now()
    
    for credit in credits:
        # Время с последнего платежа в секундах
        diff_seconds = max(0, int((now - credit.last_payment_at).total_seconds()))
        credit.time_since_seconds = diff_seconds
        credit.time_since_minutes = diff_seconds // 60
        credit.overdue = diff_seconds > 600  # 10 минут
        credit.is_critical = diff_seconds > 900  # 15 минут
        
        # Прогресс погашения
        paid_payments = max(0, credit.term_months - credit.remaining_payments)
        credit.progress_percent = round((paid_payments / credit.term_months) * 100, 2) if credit.term_months else 0
        
        # Для отладки
        print(f"Кредит {credit.id}: последний платеж {credit.last_payment_at}, прошло {diff_seconds} сек")

    context = {
        'credits': credits,
        'active_credits_count': len(credits),
        'overdue_credits_count': sum(1 for c in credits if c.overdue),
        'total_credit_amount': round(sum(float(c.credit_amount) for c in credits), 2),
        'total_paid': round(sum(float(c.total_paid) for c in credits), 2),
        'session': request.session,
    }
    return render(request, 'britain/credits.html', context)


@session_required
def britain_credit_issue(request):
    """Выдача кредита (п. 2.4.1)"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    if request.method == 'POST':
        form = CreditIssueForm(request.POST)
        if form.is_valid():
            player_id = form.cleaned_data['player_id']
            amount = form.cleaned_data['credit_amount']
            term = int(form.cleaned_data['term'])
            
            # Проверяем, есть ли уже активный кредит у игрока
            existing_credit = Credit.objects.filter(player_id=player_id).first()
            if existing_credit:
                messages.error(
                    request, 
                    f'У игрока #{player_id} уже есть активный кредит. Сначала закройте старый.'
                )
                return redirect('britain_credit_issue')
            
            # Расчет ежемесячного платежа (аннуитет)
            monthly = (amount / term) * Decimal('1.5')
            
            # Создаем кредит
            credit = Credit.objects.create(
                player_id=player_id,
                credit_amount=amount,
                term_months=term,
                monthly_payment=monthly,
                remaining_payments=term,
                issued_by=request.session.get('username', 'Unknown'),
                issued_at=timezone.now(),
                last_payment_at=timezone.now()
            )
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.session.get('username', 'Unknown'),
                table=request.session.get('table', 'britain'),
                action_type='credit_issue',
                player_id=player_id,
                details={
                    'amount': float(amount),
                    'term': term,
                    'monthly': float(monthly)
                }
            )
            
            request.session['pending_credit'] = {
                'player_id': player_id,
                'amount': float(amount),
                'term': term,
                'monthly': float(monthly)
            }
            
            messages.success(request, f'Кредит успешно выдан игроку #{player_id}')
            return redirect('britain_credit_confirm')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = CreditIssueForm()
    
    context = {
        'form': form,
        'session': request.session,
    }
    return render(request, 'britain/credit_issue.html', context)


@session_required
def britain_credit_confirm(request):
    """Подтверждение выдачи кредита"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    credit_data = request.session.get('pending_credit')
    if not credit_data:
        messages.warning(request, 'Нет данных для подтверждения')
        return redirect('britain_credit_issue')
    
    if request.method == 'POST':
        messages.success(request, f'✅ Кредит выдан игроку #{credit_data["player_id"]}')
        del request.session['pending_credit']
        return redirect('britain_credits')
    
    context = {
        'credit': credit_data,
        'session': request.session,
    }
    return render(request, 'britain/credit_confirm.html', context)


@session_required
def britain_credit_payment(request):
    """Внесение платежа по кредиту с выдачей сдачи"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Последние платежи
    recent_payments = LogEntry.objects.filter(
        action_type='credit_payment',
        table='britain'
    ).order_by('-timestamp')[:10]
    
    recent_payments_list = []
    for p in recent_payments:
        recent_payments_list.append({
            'player_id': p.player_id,
            'amount': p.details.get('amount', 0),
            'timestamp': p.timestamp
        })
    
    if request.method == 'POST':
        form = CreditPaymentForm(request.POST)
        money_input = Decimal(request.POST.get('money_input', 0))
        
        if form.is_valid():
            credit = form.cleaned_data['debtor']
            payment_amount = form.cleaned_data['payment_amount']
            
            # УБИРАЕМ ПРОВЕРКУ - доверяем JavaScript на клиенте
            # if money_input < payment_amount:
            #     messages.error(request, f'❌ Внесено недостаточно средств. Требуется: {payment_amount:.2f} ₽')
            #     return redirect('britain_credit_payment')
            
            # Вносим платеж
            change = money_input - payment_amount
            closed = credit.make_payment(payment_amount)
            
            # Запись в лог
            log_details = {
                'amount': float(payment_amount),
                'money_input': float(money_input),
                'change': float(change),
                'remaining': credit.remaining_payments if not closed else 0,
                'closed': closed
            }
            
            LogEntry.objects.create(
                author=request.session.get('username', 'Unknown'),
                table='britain',
                action_type='credit_payment',
                player_id=credit.player_id,
                details=log_details
            )
            
            if closed:
                credit.delete()
                messages.success(
                    request, 
                    f'✅ Кредит полностью погашен! Сдача: {change:.2f} ₽'
                )
            else:
                credit.save()
                messages.success(
                    request, 
                    f'✅ Платеж принят. Сдача: {change:.2f} ₽. Осталось платежей: {credit.remaining_payments}'
                )
            
            return redirect('britain_credits')
        else:
            messages.error(request, '❌ Пожалуйста, исправьте ошибки в форме')
    else:
        form = CreditPaymentForm()
    
    context = {
        'form': form,
        'recent_payments': recent_payments_list,
        'session': request.session,
    }
    
    return render(request, 'britain/credit_payment.html', context)



@session_required
def britain_coal(request):
    """Покупка угля с выдачей сдачи"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    if request.method == 'POST':
        form = CoalPurchaseForm(request.POST)
        price_per_unit = Decimal(request.POST.get('price_per_unit', 0))
        money_input = Decimal(request.POST.get('money_input', 0))
        
        if form.is_valid() and price_per_unit > 0:
            player_id = form.cleaned_data['player_id']
            quantity = form.cleaned_data['quantity']
            
            total = price_per_unit * quantity
            
            # Проверяем достаточно ли денег
            if money_input < total:
                messages.error(
                    request, 
                    f'❌ Недостаточно средств. Требуется: {total:.2f} ₽, внесено: {money_input:.2f} ₽'
                )
                return redirect('britain_coal')
            
            # Рассчитываем сдачу
            change = money_input - total
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.session.get('username', 'Unknown'),
                table='britain',
                action_type='coal_purchase',
                player_id=player_id,
                details={
                    'quantity': float(quantity),
                    'price_per_unit': float(price_per_unit),
                    'total': float(total),
                    'money_input': float(money_input),
                    'change': float(change),
                }
            )
            
            if change > 0:
                messages.success(
                    request, 
                    f'✅ Покупка угля оформлена. Сдача: {change:.2f} ₽'
                )
            else:
                messages.success(
                    request, 
                    f'✅ Покупка угля оформлена. Сдача не требуется.'
                )
            
            return redirect('britain_coal')
        else:
            messages.error(request, '❌ Пожалуйста, заполните все поля корректно')
    else:
        form = CoalPurchaseForm()
    
    context = {
        'form': form,
        'price_per_unit': 50,  # Значение по умолчанию
        'session': request.session,
    }
    
    return render(request, 'britain/coal.html', context)



@session_required
def britain_privateers(request):
    """Список каперов"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    privateers = Privateer.objects.all().order_by('-is_active', '-last_payment_at')
    
    # Статистика
    total_privateers = privateers.count()
    active_privateers_count = privateers.filter(is_active=True).count()
    privateers_with_complaints = privateers.filter(complaints__gt=0).count()
    
    # Средняя выслуга в минутах
    avg_tenure = 0
    if active_privateers_count > 0:
        total_minutes = sum(p.tenure_minutes() for p in privateers.filter(is_active=True))
        avg_tenure = total_minutes // active_privateers_count
    
    context = {
        'privateers': privateers,
        'total_privateers': total_privateers,
        'active_privateers_count': active_privateers_count,
        'privateers_with_complaints': privateers_with_complaints,
        'avg_tenure_minutes': avg_tenure,
        'session': request.session,
    }
    
    return render(request, 'britain/privateers.html', context)

@session_required
def britain_privateer_license(request):
    """Выдача/разжалование капера (п. 2.6.1)"""
    if request.method == 'POST':
        form = PrivateerLicenseForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            player_id = form.cleaned_data['player_id']
            ship_type = form.cleaned_data.get('ship_type')
            
            if action == 'issue':
                # Выдача лицензии
                privateer, created = Privateer.objects.get_or_create(
                    player_id=player_id,
                    defaults={
                        'ship_type': ship_type,
                        'licensed_by': request.current_user,
                        'is_active': True
                    }
                )
                if not created:
                    privateer.is_active = True
                    privateer.save()
                
                messages.success(request, f'Лицензия выдана игроку {player_id}')
            else:
                # Разжалование
                Privateer.objects.filter(player_id=player_id, is_active=True).update(is_active=False)
                messages.success(request, f'Игрок {player_id} разжалован')
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='privateer_license',
                player_id=player_id,
                details={
                    'action': action,
                    'ship_type': ship_type if action == 'issue' else None
                }
            )
            
            return redirect('britain_privateers')
    else:
        form = PrivateerLicenseForm()
    
    return render(request, 'britain/privateer_license.html', {'form': form})


@session_required
def britain_privateer_change_ship(request):
    """Смена корабля капера (п. 2.6.2)"""
    if request.method == 'POST':
        form = PrivateerChangeShipForm(request.POST)
        if form.is_valid():
            privateer = form.cleaned_data['privateer']
            new_ship = form.cleaned_data['new_ship']
            
            old_ship = privateer.ship_type
            privateer.ship_type = new_ship
            privateer.save()
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='privateer_ship',
                player_id=privateer.player_id,
                details={
                    'old_ship': old_ship,
                    'new_ship': new_ship
                }
            )
            
            messages.success(request, f'Корабль изменен')
            return redirect('britain_privateers')
    else:
        form = PrivateerChangeShipForm()
    
    return render(request, 'britain/privateer_change_ship.html', {'form': form})


@session_required
def britain_privateer_complaint(request):
    """Подача жалобы на капера (п. 2.6.3)"""
    if request.method == 'POST':
        form = PrivateerComplaintForm(request.POST)
        if form.is_valid():
            privateer = form.cleaned_data['privateer']
            value = form.cleaned_data['complaint_value']
            
            privateer.add_complaint(value)
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='privateer_complaint',
                player_id=privateer.player_id,
                details={
                    'value': value,
                    'new_total': privateer.complaints
                }
            )
            
            messages.success(request, f'Жалоба зарегистрирована')
            return redirect('britain_privateers')
    else:
        form = PrivateerComplaintForm()
    
    return render(request, 'britain/privateer_complaint.html', {'form': form})


@session_required
def britain_privateer_payment(request):
    """Внесение платежа капером (п. 2.6.4)"""
    if request.method == 'POST':
        form = PrivateerPaymentForm(request.POST)
        if form.is_valid():
            privateer = form.cleaned_data['privateer']
            
            # Фиксированная сумма платежа
            try:
                price_item = PriceList.objects.get(name='Каперский платеж')
                payment_amount = price_item.base_price
            except PriceList.DoesNotExist:
                payment_amount = 50  # По умолчанию
            
            privateer.make_payment()
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='privateer_payment',
                player_id=privateer.player_id,
                details={
                    'amount': float(payment_amount)
                }
            )
            
            messages.success(request, f'Платеж принят')
            return redirect('britain_privateers')
    else:
        form = PrivateerPaymentForm()
    
    return render(request, 'britain/privateer_payment.html', {'form': form})


@session_required
def britain_quest(request):
    """Управление заданиями для каперов"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Активные задания
    active_quests = Quest.objects.filter(is_active=True).order_by('-issued_at')
    
    # Публичные задания (для всех)
    public_quests = active_quests.filter(is_public=True)
    
    # Персональные задания (для конкретных каперов)
    personal_quests = active_quests.filter(is_public=False)
    
    # Активные каперы
    active_privateers = Privateer.objects.filter(is_active=True)
    
    if request.method == 'POST':
        form = QuestForm(request.POST)
        
        # Выводим ошибки в консоль для отладки
        if not form.is_valid():
            print("Ошибки формы:", form.errors)
            print("Данные POST:", request.POST)
        
        if form.is_valid():
            mode = form.cleaned_data['mode']
            
            if mode == 'issue':
                # Выдать публичное задание (всем)
                quest = Quest.objects.create(
                    player_id='ALL',  # Специальное значение для всех
                    description=form.cleaned_data['description'],
                    reward=form.cleaned_data['reward'],
                    issued_by=request.session.get('username', 'Unknown'),
                    is_public=True,
                    is_active=True
                )
                
                LogEntry.objects.create(
                    author=request.session.get('username', 'Unknown'),
                    table='britain',
                    action_type='quest_issue',
                    player_id='ALL',
                    details={
                        'quest_id': quest.id,
                        'description': quest.description,
                        'reward': float(quest.reward),
                        'is_public': True
                    }
                )
                
                messages.success(
                    request, 
                    f'✅ Публичное задание создано для всех каперов. Награда: {quest.reward} ₽'
                )
                
            elif mode == 'assign':
                # Назначить задание конкретному каперу
                privateer = form.cleaned_data['privateer']
                
                quest = Quest.objects.create(
                    player_id=privateer.player_id,
                    description=form.cleaned_data['description'],
                    reward=form.cleaned_data['reward'],
                    issued_by=request.session.get('username', 'Unknown'),
                    is_public=False,
                    is_active=True
                )
                
                LogEntry.objects.create(
                    author=request.session.get('username', 'Unknown'),
                    table='britain',
                    action_type='quest_assign',
                    player_id=privateer.player_id,
                    details={
                        'quest_id': quest.id,
                        'description': quest.description,
                        'reward': float(quest.reward),
                        'privateer': privateer.player_id
                    }
                )
                
                messages.success(
                    request, 
                    f'✅ Задание назначено каперу #{privateer.player_id}. Награда: {quest.reward} ₽'
                )
                
            elif mode == 'complete':
                # Отметить выполнение задания
                quest = form.cleaned_data['quest']
                completer = form.cleaned_data['completer']
                
                if not quest.is_active:
                    messages.error(request, '❌ Это задание уже выполнено')
                    return redirect('britain_quest')
                
                # Отмечаем выполнение
                quest.complete(completer.player_id)
                
                LogEntry.objects.create(
                    author=request.session.get('username', 'Unknown'),
                    table='britain',
                    action_type='quest_complete',
                    player_id=completer.player_id,
                    details={
                        'quest_id': quest.id,
                        'description': quest.description,
                        'reward': float(quest.reward),
                        'completed_by': completer.player_id
                    }
                )
                
                messages.success(
                    request, 
                    f'✅ Задание выполнено! Капер #{completer.player_id} получил {quest.reward} ₽'
                )
            
            return redirect('britain_quest')
        else:
            # Показываем все ошибки пользователю
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = QuestForm()
    
    context = {
        'form': form,
        'active_quests': active_quests,
        'public_quests': public_quests,
        'personal_quests': personal_quests,
        'active_privateers': active_privateers,
        'session': request.session,
    }
    
    return render(request, 'britain/quest.html', context)





# API для получения данных (AJAX)
@session_required
def api_get_building_profit(request):
    """API для получения накопленной прибыли здания"""
    building_id = request.GET.get('building_id')
    try:
        building = ConstructedBuilding.objects.get(id=building_id)
        profit = building.calculate_accumulated_profit()
        return JsonResponse({
            'success': True,
            'profit': profit,
            'owner': building.owner_id,
            'building': building.building_name
        })
    except ConstructedBuilding.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Здание не найдено'})


@session_required
def api_get_convict_time(request):
    """API для получения времени на каторге"""
    convict_id = request.GET.get('convict_id')
    try:
        convict = Convict.objects.get(id=convict_id)
        time_served = timezone.now() - convict.sentenced_at
        seconds = int(time_served.total_seconds())
        return JsonResponse({
            'success': True,
            'time_served': str(time_served).split('.')[0],
            'seconds': seconds
        })
    except Convict.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Каторжник не найден'})


@session_required
def api_get_dynamic_price(request):
    """API для получения динамической цены товара"""
    good = request.GET.get('good')
    try:
        price, created = DynamicPrice.objects.get_or_create(
            good_name=good,
            defaults={
                'current_price': 100,
                'pmax': 100,
                'n_for_drop': 10,
                't_recovery': 300
            }
        )
        price.check_recovery()
        return JsonResponse({
            'success': True,
            'price': float(price.current_price),
            'pmax': float(price.pmax),
            'sales': price.sales_count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
