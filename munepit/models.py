# models.py
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.utils import timezone
from decimal import Decimal
# Create your models here.

class UserSession(models.Model):
    """Модель для сессий пользователей (авторизация за столом)"""
    TABLE_CHOICES = [
        ('island', 'Остров'),
        ('britain', 'Великобритания'),
    ]
    
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField(max_length=100, verbose_name="Имя пользователя")
    table = models.CharField(max_length=20, choices=TABLE_CHOICES, verbose_name="Стол")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время входа")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    
    class Meta:
        verbose_name = "Сессия пользователя"
        verbose_name_plural = "Сессии пользователей"
    
    def __str__(self):
        return f"{self.username} @ {self.get_table_display()}"


class LogEntry(models.Model):
    """Общая таблица логов всех действий"""
    ACTION_TYPES = [
        ('deal', 'Сделка'),
        ('court', 'Суд'),
        ('release', 'Выход с каторги'),
        ('purchase', 'Покупка ресурса'),
        ('building', 'Постройка здания'),
        ('processing', 'Обработка ресурса'),
        ('profit', 'Получение прибыли'),
        ('demolition', 'Снос здания'),
        ('sale', 'Продажа товара'),
        ('ship_deal', 'Сделка с кораблем'),
        ('factory_work', 'Работа на заводе'),
        ('credit_issue', 'Выдача кредита'),
        ('credit_payment', 'Внесение платежа'),
        ('coal_purchase', 'Покупка угля'),
        ('privateer_license', 'Каперская лицензия'),
        ('privateer_ship', 'Смена корабля'),
        ('privateer_complaint', 'Жалоба'),
        ('privateer_payment', 'Платеж капера'),
        ('quest_accept', 'Принятие задания'),
    ]
    
    TABLE_CHOICES = [
        ('island', 'Остров'),
        ('britain', 'Великобритания'),
    ]
    
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Время", db_index=True)
    author = models.CharField(max_length=100, verbose_name="Автор (модератор)")
    table = models.CharField(max_length=20, choices=TABLE_CHOICES, verbose_name="Стол", db_index=True)
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES, verbose_name="Тип действия", db_index=True)
    player_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Номер игрока", db_index=True)
    
    # JSON поле для хранения всех деталей операции
    details = models.JSONField(default=dict, verbose_name="Детали операции")
    
    class Meta:
        verbose_name = "Запись лога"
        verbose_name_plural = "Логи действий"
        indexes = [
            models.Index(fields=['timestamp', 'action_type']),
            models.Index(fields=['player_id', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M')} | {self.author} | {self.get_action_type_display()} | Игрок {self.player_id}"

class Quest(models.Model):
    """Модель для заданий каперам"""
    
    # Кому выдано
    player_id = models.CharField(
        max_length=50, 
        verbose_name="Номер игрока (капер)",
        db_index=True
    )
    
    # Описание задания
    description = models.TextField(
        verbose_name="Описание задания",
        help_text="Что нужно сделать"
    )
    
    # Награда
    reward = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Сумма награды",
        help_text="Сколько получит капер за выполнение"
    )
    
    # Кто выдал
    issued_by = models.CharField(
        max_length=100, 
        verbose_name="Выдал (модератор)"
    )
    
    issued_at = models.DateTimeField(
        default=timezone.now, 
        verbose_name="Дата выдачи",
        db_index=True
    )
    
    # Статус задания
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Активно",
        help_text="Задание еще не выполнено"
    )
    
    completed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Дата выполнения"
    )
    
    completed_by = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Принял (капер)"
    )
    
    # Для всех ли каперов
    is_public = models.BooleanField(
        default=False,
        verbose_name="Публичное задание",
        help_text="Если True - задание видят все каперы"
    )
    
    class Meta:
        verbose_name = "Задание"
        verbose_name_plural = "Задания"
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['is_active', 'player_id']),
            models.Index(fields=['is_active', 'is_public']),
        ]
    
    def __str__(self):
        return f"Задание #{self.id} - {self.reward} ₽ ({'активно' if self.is_active else 'выполнено'})"
    
    def complete(self, completed_by):
        """Отметить задание как выполненное"""
        self.is_active = False
        self.completed_at = timezone.now()
        self.completed_by = completed_by
        self.save()
    
    def time_since_issued(self):
        """Время с момента выдачи"""
        return timezone.now() - self.issued_at
    
    def time_since_issued_minutes(self):
        """Минуты с момента выдачи"""
        return int(self.time_since_issued().total_seconds() / 60)

class BrickExchange(models.Model):
    """Модель для обмена кирпичей на стартовый корабль"""
    
    SHIP_CHOICES = [
        ('basic', 'Люггер базовый'),
        ('armed', 'Люггер с орудиями'),
    ]
    
    player_id = models.CharField(max_length=50, verbose_name="Номер игрока", db_index=True)
    ship_type = models.CharField(max_length=20, choices=SHIP_CHOICES, verbose_name="Тип корабля")
    bricks_count = models.IntegerField(verbose_name="Количество кирпичей", default=10)
    
    exchanged_by = models.CharField(max_length=100, verbose_name="Выдал (модератор)")
    exchanged_at = models.DateTimeField(default=timezone.now, verbose_name="Дата обмена")
    
    class Meta:
        verbose_name = "Обмен кирпичей"
        verbose_name_plural = "Обмены кирпичей"
        ordering = ['-exchanged_at']
    
    def __str__(self):
        ship_display = dict(self.SHIP_CHOICES).get(self.ship_type, self.ship_type)
        return f"Игрок #{self.player_id} - {ship_display}"


class PriceList(models.Model):
    """Таблица цен (для всех ресурсов, товаров, зданий, кораблей)"""
    CATEGORY_CHOICES = [
        ('resource', 'Ресурс (Остров)'),
        ('building', 'Здание'),
        ('factory', 'Фабрика'),  # Добавлено
        ('business', 'Бизнес'),   # Добавлено
        ('processing', 'Обработка'),
        ('goods', 'Товар (Великобритания)'),
        ('ship', 'Корабль'),
        ('brick', 'Кирпичи'),
        ('starter_ship', 'Стартовый корабль'),
        ('fine', 'Штраф'),
        ('other', 'Прочее'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Наименование", unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Категория", db_index=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Базовая цена", default=0)
    
    # Для товаров с динамической ценой
    pmax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Pmax (максимальная цена)")
    pmin = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Pmin (минимальная цена)")  # Добавлено
    n_for_drop = models.IntegerField(null=True, blank=True, verbose_name="N (кол-во для падения цены на 1)")
    t_recovery = models.IntegerField(null=True, blank=True, verbose_name="T (секунд для восстановления)")
    
    description = models.TextField(blank=True, verbose_name="Описание")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")
    
    class Meta:
        verbose_name = "Прайс-лист"
        verbose_name_plural = "Прайс-листы"
    
    def __str__(self):
        price_display = f"{self.base_price} ₽" if self.base_price > 0 else "Бесплатно"
        return f"{self.name} - {price_display}"


class Convict(models.Model):
    """Таблица каторжников (п. 2.9)"""
    player_id = models.CharField(max_length=50, unique=True, verbose_name="Номер игрока", db_index=True)
    player_name = models.CharField(max_length=200, blank=True, verbose_name="ФИО игрока")
    crime_description = models.TextField(verbose_name="Описание преступления")
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма штрафа")
    confiscation = models.BooleanField(default=False, verbose_name="Конфискация имущества")
    sentence_years = models.IntegerField(verbose_name="Срок каторги (лет)", validators=[MinValueValidator(0), MaxValueValidator(5)])
    
    sentenced_by = models.CharField(max_length=100, verbose_name="Приговорил")
    sentenced_at = models.DateTimeField(default=timezone.now, verbose_name="Дата приговора", db_index=True)
    
    notes = models.TextField(blank=True, verbose_name="Примечания")
    
    class Meta:
        verbose_name = "Каторжник"
        verbose_name_plural = "Каторжники"
    
    def __str__(self):
        return f"Игрок {self.player_id} - {self.sentence_years} лет (с {self.sentenced_at.date()})"
    
    def time_served(self):
        """Время, проведенное на каторге"""
        return timezone.now() - self.sentenced_at
    
    def time_served_seconds(self):
        return int(self.time_served().total_seconds())


class GameSettings(models.Model):
    """Настройки игры - время начала"""
    
    game_start_time = models.DateTimeField(
        default=timezone.now,
        verbose_name="Время начала игры"
    )
    
    class Meta:
        verbose_name = "Настройки игры"
        verbose_name_plural = "Настройки игры"
    
    def __str__(self):
        return f"Игра начата: {self.game_start_time.strftime('%d.%m.%Y %H:%M:%S')}"
    
    @classmethod
    def get_start_time(cls):
        """Получить время начала игры"""
        settings = cls.objects.first()
        if not settings:
            settings = cls.objects.create()
        return settings.game_start_time
    
    @classmethod
    def reset_game_time(cls):
        """Сбросить время начала игры на текущее"""
        settings = cls.objects.first()
        if settings:
            settings.game_start_time = timezone.now()
            settings.save()
        else:
            cls.objects.create()



class ConstructedBuilding(models.Model):
    """Таблица построенных зданий (Остров)"""
    BUILDING_TYPES = [
        ('factory', 'Фабрика'),
        ('business', 'Бизнес'),
        ('residential', 'Жилое'),
        ('other', 'Другое'),
    ]
    
    building_name = models.CharField(max_length=100, verbose_name="Название здания")
    building_type = models.CharField(max_length=20, choices=BUILDING_TYPES, verbose_name="Тип здания", db_index=True)
    
    owner_id = models.CharField(max_length=50, verbose_name="Номер игрока-владельца", db_index=True)
    
    built_by = models.CharField(max_length=100, verbose_name="Построил (модератор)")
    built_at = models.DateTimeField(default=timezone.now, verbose_name="Дата постройки")
    
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Стоимость постройки")
    
    # Для бизнесов - время последнего получения прибыли
    last_profit_collected = models.DateTimeField(default=timezone.now, verbose_name="Последнее получение прибыли")
    
    # Доход в минуту (берется из PriceList или отдельного поля)
    income_per_minute = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Доход в минуту")
    
    class Meta:
        verbose_name = "Построенное здание"
        verbose_name_plural = "Построенные здания"
    
    def __str__(self):
        return f"{self.building_name} (игрок {self.owner_id})"
    
    
    def calculate_accumulated_profit(self):
        """
        Расчет накопленной прибыли для бизнеса
        """
        # Отладка - выводим информацию
        print(f"=== calculate_accumulated_profit для бизнеса {self.id} ===")
        print(f"  building_type: {self.building_type}")
        print(f"  income_per_minute: {self.income_per_minute}")
        print(f"  last_profit_collected: {self.last_profit_collected}")
        print(f"  current time: {timezone.now()}")
        
        
        # Текущее время
        now = timezone.now()
        
        # Разница во времени
        time_diff = now - self.last_profit_collected
        seconds = time_diff.total_seconds()
        minutes = seconds / 60.0
        
        print(f"  секунд прошло: {seconds}")
        print(f"  минут прошло: {minutes}")
        
        # Доход в минуту
        income = float(self.income_per_minute)
        print(f"  доход в минуту: {income}")
        
        # Расчет прибыли
        profit = income * minutes
        print(f"  прибыль: {profit}")
        
        # Округляем
        result = round(profit, 2)
        print(f"  результат: {result}")
        
        return result
        
    
    
    
    def reset_profit_timer(self):
        """Сброс таймера прибыли"""
        self.last_profit_collected = timezone.now()
        self.save(update_fields=['last_profit_collected'])


class Credit(models.Model):
    """Таблица кредитов (Великобритания)"""
    player_id = models.CharField(max_length=50, unique=True, verbose_name="Игрок-должник", db_index=True)
    
    credit_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма кредита")
    term_months = models.IntegerField(verbose_name="Срок (кол-во платежей)", validators=[MinValueValidator(2), MaxValueValidator(6)])
    monthly_payment = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ежемесячный платеж")
    
    remaining_payments = models.IntegerField(verbose_name="Осталось платежей")
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Всего выплачено")
    
    issued_by = models.CharField(max_length=100, verbose_name="Выдал")
    issued_at = models.DateTimeField(default=timezone.now, verbose_name="Дата выдачи")
    
    last_payment_at = models.DateTimeField(default=timezone.now, verbose_name="Последний платеж", db_index=True)
    
    class Meta:
        verbose_name = "Кредит"
        verbose_name_plural = "Кредиты"
    
    def __str__(self):
        return f"Игрок {self.player_id}: {self.remaining_payments}/{self.term_months} платежей"
    
    def time_since_last_payment(self):
        """Время с последнего платежа"""
        return timezone.now() - self.last_payment_at
    
    def is_overdue(self):
        """Просрочка более 10 минут"""
        return self.time_since_last_payment().total_seconds() > 600  # 10 минут
    
    def make_payment(self, amount):
        """Внесение платежа"""
        from decimal import Decimal
        
        monthly = self.monthly_payment
        
        # Обязательный платеж
        if amount >= monthly:
            payments_covered = 1
            
            # Дополнительные платежи (каждые 0.66 * monthly)
            extra = amount - monthly
            if extra > 0:
                extra_payments = int(extra / (monthly * Decimal('0.66')))
                payments_covered += extra_payments
            
            self.remaining_payments = max(0, self.remaining_payments - payments_covered)
            self.total_paid += amount
            self.last_payment_at = timezone.now()
            
            if self.remaining_payments <= 0:
                return True  # Кредит закрыт
        
        return False  # Кредит не закрыт


class Privateer(models.Model):
    """Таблица каперов (лицензий) - Великобритания"""
    SHIP_CHOICES = [
        ('frigate', 'Фрегат'),
        ('battleship', 'Линкор'),
        ('steam_frigate', 'Паровой фрегат'),
    ]
    
    player_id = models.CharField(max_length=50, unique=True, verbose_name="Номер игрока", db_index=True)
    ship_type = models.CharField(max_length=20, choices=SHIP_CHOICES, verbose_name="Корабль")
    
    # Выслуга (таймер с последнего платежа)
    last_payment_at = models.DateTimeField(default=timezone.now, verbose_name="Последний платеж")
    
    complaints = models.IntegerField(default=0, verbose_name="Количество жалоб")
    
    licensed_by = models.CharField(max_length=100, verbose_name="Лицензию выдал")
    licensed_at = models.DateTimeField(default=timezone.now, verbose_name="Дата выдачи")
    
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    class Meta:
        verbose_name = "Капер"
        verbose_name_plural = "Каперы"
    
    def __str__(self):
        return f"Игрок {self.player_id} - {self.get_ship_type_display()}"
    
    def tenure_minutes(self):
        """Выслуга в минутах с последнего платежа"""
        if not self.last_payment_at:
            return 0
        delta = timezone.now() - self.last_payment_at
        return int(delta.total_seconds() / 60)
    
    def tenure_hours(self):
        """Выслуга в часах"""
        return self.tenure_minutes() // 60
    
    def tenure_days(self):
        """Выслуга в днях"""
        return self.tenure_hours() // 24
    
    def is_overdue(self):
        """Просрочка платежа (более 24 часов)"""
        return self.tenure_minutes() > 1440  # 24 часа = 1440 минут
    
    def make_payment(self):
        """Внесение платежа"""
        self.last_payment_at = timezone.now()
        self.save(update_fields=['last_payment_at'])
    
    def add_complaint(self, value):
        """Добавление жалобы (может быть отрицательной)"""
        self.complaints += value
        self.save(update_fields=['complaints'])

class DynamicPrice(models.Model):
    """Для динамических цен товаров (Великобритания)"""
    good_name = models.CharField(max_length=100, verbose_name="Товар", db_index=True, unique=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Текущая цена")
    
    # Для восстановления цены
    pmax = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Pmax (максимальная цена)")
    pmin = models.DecimalField(max_digits=10, decimal_places=2, default=1, verbose_name="Pmin (минимальная цена)")
    n_for_drop = models.IntegerField(verbose_name="N для падения (через сколько единиц цена падает на 1)")
    t_recovery = models.IntegerField(verbose_name="T восстановления (секунд)")
    
    last_update = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")
    sales_count = models.IntegerField(default=0, verbose_name="Продаж с последнего восстановления")
    
    class Meta:
        verbose_name = "Динамическая цена"
        verbose_name_plural = "Динамические цены"
    
    def __str__(self):
        return f"{self.good_name}: {self.current_price} ₽"
    
    def get_price_for_quantity(self, quantity):
        """
        Возвращает цену для конкретного количества с учетом падения
        """
        if quantity <= 0:
            return 0
        
        total_cost = 0
        remaining = quantity
        current = float(self.current_price)
        
        # Пока есть товар для расчета
        while remaining > 0:
            # Сколько единиц можно купить по текущей цене до следующего падения
            units_at_current = min(remaining, self.n_for_drop)
            total_cost += current * units_at_current
            remaining -= units_at_current
            
            # Цена падает на 1, но не ниже минимума
            current = max(float(self.pmin), current - 1)
        
        return round(total_cost, 2)
    
    def record_sale(self, quantity):
        """
        Фиксация продажи для падения цены
        Возвращает новую цену после продажи
        """
        self.sales_count += quantity
        
        # Падение цены за каждые N единиц
        if self.n_for_drop > 0:
            price_drop = self.sales_count // self.n_for_drop
            new_price = float(self.pmax) - price_drop
            self.current_price = max(float(self.pmin), new_price)
        
        self.save()
        return float(self.current_price)
    
    def check_recovery(self):
        """
        Проверка восстановления цены
        Возвращает True, если цена восстановилась
        """
        seconds_since = (timezone.now() - self.last_update).total_seconds()
        
        # Если прошло достаточно времени и цена не максимальная
        if seconds_since >= self.t_recovery and float(self.current_price) < float(self.pmax):
            self.current_price = self.pmax
            self.sales_count = 0
            self.last_update = timezone.now()
            self.save()
            return True
        
        return False
    
    def get_price_breakdown(self, quantity):
        """
        Возвращает детализацию расчета цены для отображения
        """
        if quantity <= 0:
            return []
        
        breakdown = []
        remaining = quantity
        current = float(self.current_price)
        step = 1
        
        while remaining > 0:
            units = min(remaining, self.n_for_drop)
            breakdown.append({
                'step': step,
                'price': current,
                'units': units,
                'total': current * units
            })
            
            remaining -= units
            current = max(float(self.pmin), current - 1)
            step += 1
        
        return breakdown
    """Для динамических цен товаров (Великобритания, п. 2.1)"""
    good_name = models.CharField(max_length=100, verbose_name="Товар", db_index=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Текущая цена")
    
    # Для восстановления цены
    pmax = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Pmax")
    n_for_drop = models.IntegerField(verbose_name="N для падения")
    t_recovery = models.IntegerField(verbose_name="T восстановления (сек)")
    
    last_update = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")
    sales_count = models.IntegerField(default=0, verbose_name="Продаж с последнего восстановления")
    
    class Meta:
        verbose_name = "Динамическая цена"
        verbose_name_plural = "Динамические цены"
    
    def __str__(self):
        return f"{self.good_name}: {self.current_price}"
    
    def record_sale(self, quantity):
        """Фиксация продажи для падения цены"""
        self.sales_count += quantity
        # Падение цены за каждые N единиц
        if self.n_for_drop > 0:
            price_drop = self.sales_count // self.n_for_drop
            new_price = float(self.pmax) - price_drop
            self.current_price = max(0, new_price)
        self.save()
    
    def check_recovery(self):
        """Проверка восстановления цены"""
        seconds_since = (timezone.now() - self.last_update).total_seconds()
        if seconds_since >= self.t_recovery and self.current_price < self.pmax:
            self.current_price = self.pmax
            self.sales_count = 0
            self.save()

class Recipe(models.Model):
    """Модель для рецептов производства"""
    
    name = models.CharField(max_length=100, verbose_name="Название продукта")
    category = models.CharField(max_length=50, verbose_name="Категория", default="product")
    
    # Выход продукта
    output_quantity = models.IntegerField(default=1, verbose_name="Количество на выходе")
    
    # Время производства (в секундах)
    production_time = models.IntegerField(default=10, verbose_name="Время производства (сек)")
    
    # Ингредиенты (JSON поле для хранения списка)
    ingredients = models.JSONField(default=dict, verbose_name="Ингредиенты")
    
    # Цена продукта (базовая)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Базовая цена")
    
    description = models.TextField(blank=True, verbose_name="Описание")
    
    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
    
    def __str__(self):
        return f"{self.name}"
    
    def get_ingredients_display(self):
        """Возвращает строку с ингредиентами"""
        ingredients_list = []
        for ing_name, quantity in self.ingredients.items():
            ingredients_list.append(f"{ing_name}: {quantity}")
        return ", ".join(ingredients_list)