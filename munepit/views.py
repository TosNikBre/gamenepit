# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from decimal import Decimal
from datetime import timedelta
import json


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
        return 'factory', 0

    if any(keyword in text for keyword in ('дом', 'особняк', 'жиль')):
        return 'residential', 0

    return 'other', 0


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
    """Суд (п. 2.9)"""
    if request.method == 'POST':
        form = CourtForm(request.POST)
        if form.is_valid():
            convict = form.save(commit=False)
            convict.sentenced_by = request.current_user
            convict.save()
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='court',
                player_id=convict.player_id,
                details={
                    'crime': convict.crime_description,
                    'fine': float(convict.fine_amount),
                    'confiscation': convict.confiscation,
                    'sentence': convict.sentence_years
                }
            )
            
            # Сохраняем для подтверждения
            request.session['pending_convict'] = {
                'id': convict.id,
                'player_id': convict.player_id,
                'player_name': convict.player_name,
                'crime': convict.crime_description,
                'fine': float(convict.fine_amount),
                'confiscation': convict.confiscation,
                'sentence': convict.sentence_years
            }
            return redirect('island_court_confirm')
    else:
        form = CourtForm()
    
    return render(request, 'island/court.html', {'form': form})


@session_required
def island_court_confirm(request):
    """Подтверждение приговора"""
    convict_data = request.session.get('pending_convict')
    if not convict_data:
        return redirect('island_court')
    
    if request.method == 'POST':
        messages.success(request, 'Приговор вынесен')
        del request.session['pending_convict']
        return redirect('island_dashboard')
    
    return render(request, 'island/court_confirm.html', {'convict': convict_data})


@session_required
def island_release(request):
    """Выход с каторги (п. 2.10)"""
    if request.method == 'POST':
        form = ConvictReleaseForm(request.POST)
        if form.is_valid():
            convict = form.cleaned_data['player']
            early = form.cleaned_data['early_release'] == 'True'
            
            # Расчет времени на каторге
            time_served = timezone.now() - convict.sentenced_at
            seconds_served = int(time_served.total_seconds())
            
            # Удаление из таблицы каторжников
            player_id = convict.player_id
            convict.delete()
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='release',
                player_id=player_id,
                details={
                    'early_release': early,
                    'time_served_seconds': seconds_served,
                    'time_served_formatted': str(time_served).split('.')[0]
                }
            )
            
            messages.success(request, f'Игрок {player_id} освобожден с каторги')
            return redirect('island_dashboard')
    else:
        form = ConvictReleaseForm()
        # Автоматически заполняем время для предпросмотра
        if 'player' in request.GET:
            try:
                convict = Convict.objects.get(id=request.GET['player'])
                time_served = timezone.now() - convict.sentenced_at
                form.fields['time_served'].initial = str(time_served).split('.')[0]
            except Convict.DoesNotExist:
                pass
    
    return render(request, 'island/release.html', {'form': form})


@session_required
def island_purchase_resource(request):
    """Покупка ресурса (п. 3.1)"""
    if request.method == 'POST':
        form = ResourcePurchaseForm(request.POST)
        if form.is_valid():
            # Получаем цену из прайс-листа
            try:
                price_item = PriceList.objects.get(
                    name__icontains=form.cleaned_data['resource'],
                    category='resource'
                )
                price = price_item.base_price
            except PriceList.DoesNotExist:
                price = 10  # Значение по умолчанию
            
            total = form.cleaned_data['quantity'] * float(price)
            
            # Сохраняем в сессию для подтверждения
            request.session['pending_purchase'] = {
                'resource': form.cleaned_data['resource'],
                'player_id': form.cleaned_data['player_id'],
                'quantity': form.cleaned_data['quantity'],
                'price_per_unit': float(price),
                'total': total
            }
            return redirect('island_purchase_confirm')
    else:
        form = ResourcePurchaseForm()
    
    return render(request, 'island/purchase_resource.html', {'form': form})


@session_required
def island_purchase_confirm(request):
    """Подтверждение покупки с расчетом сдачи"""
    purchase_data = request.session.get('pending_purchase')
    if not purchase_data:
        return redirect('island_purchase_resource')
    
    change = None
    if request.method == 'POST':
        money_input = Decimal(request.POST.get('money_input', 0))
        total = Decimal(str(purchase_data['total']))
        
        if money_input >= total:
            change = float(money_input - total)
            
            # Запись в БД
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='purchase',
                player_id=purchase_data['player_id'],
                details={
                    'resource': purchase_data['resource'],
                    'quantity': purchase_data['quantity'],
                    'price_per_unit': purchase_data['price_per_unit'],
                    'total': purchase_data['total'],
                    'money_input': float(money_input),
                    'change': change
                }
            )
            
            messages.success(request, f'Покупка завершена. Сдача: {change:.2f}')
            del request.session['pending_purchase']
            return redirect('island_dashboard')
        else:
            messages.error(request, 'Недостаточно средств')
    
    return render(request, 'island/purchase_confirm.html', {
        'purchase': purchase_data,
        'change': change
    })


@session_required
def island_build(request):
    """Постройка здания (п. 3.2)"""
    if request.method == 'POST':
        form = BuildingForm(request.POST)
        if form.is_valid():
            building = form.cleaned_data['building']
            player_id = form.cleaned_data['player_id']
            
            building_type, income_per_minute = _infer_building_type_and_income(
                building.name,
                building.description,
            )

            # Создаем запись о построенном здании
            constructed = ConstructedBuilding.objects.create(
                building_name=building.name,
                building_type=building_type,
                owner_id=player_id,
                built_by=request.current_user,
                cost=building.base_price,
                income_per_minute=income_per_minute
            )
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='building',
                player_id=player_id,
                details={
                    'building': building.name,
                    'cost': float(building.base_price)
                }
            )
            
            request.session['pending_building'] = {
                'building': building.name,
                'player_id': player_id,
                'cost': float(building.base_price)
            }
            return redirect('island_build_confirm')
    else:
        form = BuildingForm()
    
    recent_buildings = ConstructedBuilding.objects.order_by('-built_at')[:20]
    
    return render(request, 'island/build.html', {
        'form': form,
        'recent_buildings': recent_buildings,
    })


@session_required
def island_build_confirm(request):
    """Подтверждение постройки"""
    build_data = request.session.get('pending_building')
    if not build_data:
        return redirect('island_build')
    
    if request.method == 'POST':
        messages.success(request, 'Здание построено')
        del request.session['pending_building']
        return redirect('island_dashboard')
    
    return render(request, 'island/build_confirm.html', {'build': build_data})


@session_required
def island_process_resource(request):
    """Обработка ресурса на фабрике (п. 3.3)"""
    if request.method == 'POST':
        form = ResourceProcessingForm(request.POST)
        if form.is_valid():
            factory = form.cleaned_data['factory']
            quantity = form.cleaned_data['quantity']
            
            # Получаем стоимость обработки
            try:
                price_item = PriceList.objects.get(category='processing', name__icontains='обработка')
                processing_cost = price_item.base_price
            except PriceList.DoesNotExist:
                processing_cost = 5  # По умолчанию
            
            total = quantity * float(processing_cost)
            
            request.session['pending_processing'] = {
                'factory_id': factory.id,
                'factory_name': factory.building_name,
                'owner_id': factory.owner_id,
                'quantity': quantity,
                'cost_per_unit': float(processing_cost),
                'total': total
            }
            return redirect('island_process_confirm')
    else:
        form = ResourceProcessingForm()
    
    return render(request, 'island/process_resource.html', {'form': form})


@session_required
def island_process_confirm(request):
    """Подтверждение обработки"""
    process_data = request.session.get('pending_processing')
    if not process_data:
        return redirect('island_process_resource')
    
    change = None
    if request.method == 'POST':
        money_input = Decimal(request.POST.get('money_input', 0))
        total = Decimal(str(process_data['total']))
        
        if money_input >= total:
            change = float(money_input - total)
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='processing',
                player_id=process_data['owner_id'],
                details={
                    'factory': process_data['factory_name'],
                    'quantity': process_data['quantity'],
                    'total': process_data['total'],
                    'money_input': float(money_input),
                    'change': change
                }
            )
            
            messages.success(request, f'Обработка завершена. Сдача: {change:.2f}')
            del request.session['pending_processing']
            return redirect('island_dashboard')
        else:
            messages.error(request, 'Недостаточно средств')
    
    return render(request, 'island/process_confirm.html', {
        'process': process_data,
        'change': change
    })


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
            if inferred_type == 'business' and building.income_per_minute <= 0:
                building.income_per_minute = inferred_income or 5
                building.save(update_fields=['building_type', 'income_per_minute'])
            else:
                building.save(update_fields=['building_type'])
            normalized += 1

    if normalized:
        print(f"Нормализовано построек по типам: {normalized}")

    # Получаем все бизнесы (здания типа business)
    businesses = ConstructedBuilding.objects.filter(building_type='business').order_by('-last_profit_collected')
    
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
                        'profit': profit,
                        'income_per_minute': float(business.income_per_minute),
                    }
                )
                
                messages.success(
                    request, 
                    f'Прибыль {profit:.2f} ₽ получена от бизнеса "{business.building_name}" для игрока #{business.owner_id}'
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

    total_demolitions = demolitions_qs.count()
    demolitions_today = demolitions_qs.filter(timestamp__date=timezone.now().date()).count()
    total_business_demolitions = demolitions_qs.filter(details__building_type='business').count()
    total_compensation = sum(float(entry.details.get('accumulated_profit', 0) or 0) for entry in demolitions_qs)

    recent_demolitions = demolitions_qs[:20]
    
    return render(request, 'island/demolish.html', {
        'form': form,
        'buildings': buildings,
        'recent_demolitions': recent_demolitions,
        'total_demolitions': total_demolitions,
        'demolitions_today': demolitions_today,
        'total_business_demolitions': total_business_demolitions,
        'total_compensation': round(total_compensation, 2),
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
    """Покупка ресурса"""
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')
    
    # Получаем все ресурсы из прайс-листа
    resources = PriceList.objects.filter(category='resource')
    
    # Последние покупки из логов
    recent_purchases = LogEntry.objects.filter(
        action_type='purchase',
        table='island'
    ).order_by('-timestamp')[:10]
    
    # Статистика за сегодня
    today = timezone.now().date()
    today_sales = LogEntry.objects.filter(
        action_type='purchase',
        table='island',
        timestamp__date=today
    ).count()
    
    total_revenue = sum(
        float(p.details.get('total', 0)) 
        for p in LogEntry.objects.filter(
            action_type='purchase',
            table='island',
            timestamp__date=today
        )
    )
    
    if request.method == 'POST':
        form = ResourcePurchaseForm(request.POST)
        if form.is_valid():
            resource = form.cleaned_data['resource']
            player_id = form.cleaned_data['player_id']
            quantity = form.cleaned_data['quantity']
            
            # Цены ресурсов
            prices = {
                'coffee': 10,
                'cocoa': 12,
                'tobacco': 15,
                'sugar_cane': 8
            }
            
            price_per_unit = prices.get(resource, 10)
            total = quantity * price_per_unit
            
            # Получаем название ресурса для отображения
            resource_names = {
                'coffee': 'Кофейные зерна',
                'cocoa': 'Какао бобы',
                'tobacco': 'Табак',
                'sugar_cane': 'Тростник'
            }
            
            # Сохраняем в сессию для подтверждения
            request.session['pending_purchase'] = {
                'resource': resource_names.get(resource, resource),
                'resource_key': resource,
                'player_id': player_id,
                'quantity': quantity,
                'price_per_unit': price_per_unit,
                'total': total,
            }
            
            return redirect('island_purchase_confirm')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = ResourcePurchaseForm()
    
    context = {
        'form': form,
        'resources': resources,
        'recent_purchases': recent_purchases,
        'resources_count': resources.count(),
        'today_sales': today_sales,
        'total_revenue': total_revenue,
        'session': request.session,
    }
    
    return render(request, 'island/purchase_resource.html', context)

# ================ СТОЛ "ВЕЛИКОБРИТАНИЯ" ================

@session_required
def britain_dashboard(request):
    """Главная страница стола Великобритания"""
    # Данные для таблицы кредитов
    credits = Credit.objects.all()
    for credit in credits:
        credit.overdue = credit.is_overdue()
    
    # Данные для таблицы каперов
    privateers = Privateer.objects.filter(is_active=True)
    for p in privateers:
        p.tenure_display = str(p.tenure()).split('.')[0]
    
    context = {
        'session': request.current_session,
        'credits': credits,
        'privateers': privateers,
        'price_list': PriceList.objects.filter(category='goods'),
    }
    return render(request, 'britain/dashboard.html', context)


@session_required
def britain_sale(request):
    """Продажа товара (п. 2.1)"""
    if request.method == 'POST':
        form = GoodsSaleForm(request.POST)
        if form.is_valid():
            good = form.cleaned_data['good']
            player_id = form.cleaned_data['player_id']
            quantity = form.cleaned_data['quantity']
            money_input = form.cleaned_data['money_input']
            
            # Получаем динамическую цену
            try:
                dynamic_price, created = DynamicPrice.objects.get_or_create(
                    good_name=good,
                    defaults={
                        'current_price': 100,
                        'pmax': 100,
                        'n_for_drop': 10,
                        't_recovery': 300
                    }
                )
                
                # Проверяем восстановление цены
                dynamic_price.check_recovery()
                
                price_per_unit = dynamic_price.current_price
                total = quantity * float(price_per_unit)
                
                if money_input >= total:
                    # Фиксируем продажу (цена упадет)
                    dynamic_price.record_sale(quantity)
                    
                    change = float(money_input - total)
                    
                    # Запись в лог
                    LogEntry.objects.create(
                        author=request.current_user,
                        table=request.current_table,
                        action_type='sale',
                        player_id=player_id,
                        details={
                            'good': good,
                            'quantity': quantity,
                            'price_per_unit': float(price_per_unit),
                            'total': total,
                            'money_input': float(money_input),
                            'change': change
                        }
                    )
                    
                    messages.success(request, f'Продажа завершена. Сдача: {change:.2f}')
                    return redirect('britain_dashboard')
                else:
                    messages.error(request, f'Недостаточно средств. Требуется: {total:.2f}')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')
    else:
        form = GoodsSaleForm()
    
    return render(request, 'britain/sale.html', {'form': form})


@session_required
def britain_ship_deal(request):
    """Сделка с кораблем (п. 2.2)"""
    if request.method == 'POST':
        form = ShipDealForm(request.POST)
        if form.is_valid():
            ship = form.cleaned_data['ship']
            deal_type = form.cleaned_data['deal_type']
            player_id = form.cleaned_data['player_id']
            money_input = form.cleaned_data.get('money_input', 0)
            
            # Получаем цену корабля
            try:
                price_item = PriceList.objects.get(name__icontains=ship, category='ship')
                price = price_item.base_price
            except PriceList.DoesNotExist:
                price = 1000  # По умолчанию
            
            if deal_type == 'buy':
                total = float(price)
                if money_input >= total:
                    change = float(money_input - total)
                    
                    LogEntry.objects.create(
                        author=request.current_user,
                        table=request.current_table,
                        action_type='ship_deal',
                        player_id=player_id,
                        details={
                            'ship': ship,
                            'deal_type': 'покупка',
                            'price': total,
                            'money_input': float(money_input),
                            'change': change
                        }
                    )
                    
                    messages.success(request, f'Корабль куплен. Сдача: {change:.2f}')
                else:
                    messages.error(request, f'Недостаточно средств. Требуется: {total:.2f}')
            else:  # Продажа
                total = float(price) * 0.5  # Продажа за полцены
                
                LogEntry.objects.create(
                    author=request.current_user,
                    table=request.current_table,
                    action_type='ship_deal',
                    player_id=player_id,
                    details={
                        'ship': ship,
                        'deal_type': 'продажа',
                        'price': total
                    }
                )
                
                messages.success(request, f'Корабль продан за {total:.2f}')
            
            return redirect('britain_dashboard')
    else:
        form = ShipDealForm()
    
    return render(request, 'britain/ship_deal.html', {'form': form})


@session_required
def britain_factory_work(request):
    """Работа на заводе (п. 2.3)"""
    if request.method == 'POST':
        form = FactoryWorkForm(request.POST)
        if form.is_valid():
            player_id = form.cleaned_data['player_id']
            quantity = form.cleaned_data['quantity']
            money_input = form.cleaned_data['money_input']
            
            # Стоимость шестерни
            try:
                price_item = PriceList.objects.get(category='gear')
                gear_price = price_item.base_price
            except PriceList.DoesNotExist:
                gear_price = 2  # По умолчанию
            
            total = quantity * float(gear_price)
            
            if money_input >= total:
                change = float(money_input - total)
                
                LogEntry.objects.create(
                    author=request.current_user,
                    table=request.current_table,
                    action_type='factory_work',
                    player_id=player_id,
                    details={
                        'quantity': quantity,
                        'price_per_unit': float(gear_price),
                        'total': total,
                        'money_input': float(money_input),
                        'change': change
                    }
                )
                
                messages.success(request, f'Работа оплачена. Сдача: {change:.2f}')
                return redirect('britain_dashboard')
            else:
                messages.error(request, f'Недостаточно средств. Требуется: {total:.2f}')
    else:
        form = FactoryWorkForm()
    
    return render(request, 'britain/factory_work.html', {'form': form})


@session_required
def britain_credits(request):
    """Таблица кредитов (п. 2.4)"""
    credits = Credit.objects.all()
    for credit in credits:
        credit.time_since = credit.time_since_last_payment()
        credit.overdue = credit.is_overdue()
    
    return render(request, 'britain/credits.html', {'credits': credits})


@session_required
def britain_credit_issue(request):
    """Выдача кредита (п. 2.4.1)"""
    if request.method == 'POST':
        form = CreditIssueForm(request.POST)
        if form.is_valid():
            player_id = form.cleaned_data['player_id']
            amount = form.cleaned_data['credit_amount']
            term = int(form.cleaned_data['term'])
            
            monthly = (amount / term) * Decimal('1.5')
            
            # Создаем кредит
            credit = Credit.objects.create(
                player_id=player_id,
                credit_amount=amount,
                term_months=term,
                monthly_payment=monthly,
                remaining_payments=term,
                issued_by=request.current_user
            )
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
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
            return redirect('britain_credit_confirm')
    else:
        form = CreditIssueForm()
    
    return render(request, 'britain/credit_issue.html', {'form': form})


@session_required
def britain_credit_confirm(request):
    """Подтверждение выдачи кредита"""
    credit_data = request.session.get('pending_credit')
    if not credit_data:
        return redirect('britain_credit_issue')
    
    if request.method == 'POST':
        messages.success(request, 'Кредит выдан')
        del request.session['pending_credit']
        return redirect('britain_credits')
    
    return render(request, 'britain/credit_confirm.html', {'credit': credit_data})


@session_required
def britain_credit_payment(request):
    """Внесение платежа по кредиту (п. 2.4.2)"""
    if request.method == 'POST':
        form = CreditPaymentForm(request.POST)
        if form.is_valid():
            credit = form.cleaned_data['debtor']
            amount = form.cleaned_data['payment_amount']
            
            # Вносим платеж
            closed = credit.make_payment(amount)
            
            if closed:
                credit.delete()
                messages.success(request, f'Кредит полностью погашен!')
            else:
                credit.save()
                messages.success(request, f'Платеж принят. Осталось платежей: {credit.remaining_payments}')
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='credit_payment',
                player_id=credit.player_id,
                details={
                    'amount': float(amount),
                    'remaining': credit.remaining_payments if not closed else 0,
                    'closed': closed
                }
            )
            
            return redirect('britain_credits')
    else:
        form = CreditPaymentForm()
    
    return render(request, 'britain/credit_payment.html', {'form': form})


@session_required
def britain_coal(request):
    """Покупка угля (п. 2.5)"""
    if request.method == 'POST':
        form = CoalPurchaseForm(request.POST)
        if form.is_valid():
            player_id = form.cleaned_data['player_id']
            amount = form.cleaned_data['amount']
            money_input = form.cleaned_data['money_input']
            
            if money_input >= amount:
                change = float(money_input - amount)
                
                LogEntry.objects.create(
                    author=request.current_user,
                    table=request.current_table,
                    action_type='coal_purchase',
                    player_id=player_id,
                    details={
                        'amount': float(amount),
                        'money_input': float(money_input),
                        'change': change
                    }
                )
                
                messages.success(request, f'Уголь куплен. Сдача: {change:.2f}')
                return redirect('britain_dashboard')
            else:
                messages.error(request, f'Недостаточно средств. Требуется: {amount:.2f}')
    else:
        form = CoalPurchaseForm()
    
    return render(request, 'britain/coal.html', {'form': form})


@session_required
def britain_privateers(request):
    """Таблица каперов (п. 2.6)"""
    privateers = Privateer.objects.filter(is_active=True)
    return render(request, 'britain/privateers.html', {'privateers': privateers})


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
    """Принятие задания (п. 2.7)"""
    if request.method == 'POST':
        form = QuestAcceptForm(request.POST)
        if form.is_valid():
            privateer = form.cleaned_data['privateer']
            reward = form.cleaned_data['reward']
            description = form.cleaned_data['description']
            
            # Запись в лог
            LogEntry.objects.create(
                author=request.current_user,
                table=request.current_table,
                action_type='quest_accept',
                player_id=privateer.player_id,
                details={
                    'reward': float(reward),
                    'description': description
                }
            )
            
            messages.success(request, f'Задание принято')
            return redirect('britain_dashboard')
    else:
        form = QuestAcceptForm()
    
    return render(request, 'britain/quest.html', {'form': form})


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