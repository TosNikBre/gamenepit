# models.py
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

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


class PriceList(models.Model):
    """Таблица цен (для всех ресурсов, товаров, зданий)"""
    CATEGORY_CHOICES = [
        ('resource', 'Ресурс (Остров)'),
        ('building', 'Здание'),
        ('processing', 'Обработка'),
        ('goods', 'Товар (Великобритания)'),
        ('ship', 'Корабль'),
        ('gear', 'Шестерня'),
        ('fine', 'Штраф'),
        ('other', 'Прочее'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Наименование", unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Категория", db_index=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Базовая цена", default=0)
    
    # Для товаров с динамической ценой (Великобритания)
    pmax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Pmax (стартовая цена)")
    n_for_drop = models.IntegerField(null=True, blank=True, verbose_name="N (кол-во для падения цены на 1)")
    t_recovery = models.IntegerField(null=True, blank=True, verbose_name="T (секунд для восстановления)")
    
    description = models.TextField(blank=True, verbose_name="Описание")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")
    
    class Meta:
        verbose_name = "Прайс-лист"
        verbose_name_plural = "Прайс-листы"
    
    def __str__(self):
        return f"{self.name} - {self.base_price}"


class Convict(models.Model):
    """Таблица каторжников (п. 2.9)"""
    player_id = models.CharField(max_length=50, unique=True, verbose_name="Номер игрока", db_index=True)
    player_name = models.CharField(max_length=200, blank=True, verbose_name="ФИО игрока")
    crime_description = models.TextField(verbose_name="Описание преступления")
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма штрафа")
    confiscation = models.BooleanField(default=False, verbose_name="Конфискация имущества")
    sentence_years = models.IntegerField(verbose_name="Срок каторги (лет)", validators=[MinValueValidator(1), MaxValueValidator(5)])
    
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
        """Расчет накопленной прибыли для бизнеса"""
        if self.building_type != 'business':
            return 0
        
        time_diff = timezone.now() - self.last_profit_collected
        minutes = time_diff.total_seconds() / 60
        profit = minutes * float(self.income_per_minute)
        return max(0, round(profit, 2))
    
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
    
    def tenure(self):
        """Выслуга (время с последнего платежа)"""
        return timezone.now() - self.last_payment_at
    
    def make_payment(self):
        """Внесение платежа"""
        self.last_payment_at = timezone.now()
        self.save(update_fields=['last_payment_at'])
    
    def add_complaint(self, value):
        """Добавление жалобы (может быть отрицательной)"""
        self.complaints += value
        self.save(update_fields=['complaints'])


class DynamicPrice(models.Model):
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