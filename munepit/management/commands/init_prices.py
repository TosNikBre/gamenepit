# munepit/management/commands/init_prices.py
from django.core.management.base import BaseCommand
from munepit.models import PriceList
from django.utils import timezone

class Command(BaseCommand):
    help = 'Инициализация прайс-листа со всеми товарами, зданиями и ресурсами'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить существующие записи перед созданием',
        )

    def handle(self, *args, **options):
        # Очистка существующих записей если указан флаг --clear
        if options['clear']:
            self.stdout.write(self.style.WARNING('Очистка существующих записей...'))
            PriceList.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Все записи удалены'))

        # === ЗДАНИЯ ДЛЯ ОСТРОВА ===
        buildings = [
            # Фабрики (производственные здания)
            {
                'name': 'Маленькая фабрика',
                'category': 'building',
                'base_price': 500,
                'description': 'Небольшое производственное помещение. Позволяет обрабатывать ресурсы.'
            },
            {
                'name': 'Средняя фабрика',
                'category': 'building',
                'base_price': 1000,
                'description': 'Среднее производственное помещение. Увеличенная скорость обработки.'
            },
            {
                'name': 'Большая фабрика',
                'category': 'building',
                'base_price': 2000,
                'description': 'Крупное производственное помещение. Высокая производительность.'
            },
            {
                'name': 'Гигантская фабрика',
                'category': 'building',
                'base_price': 5000,
                'description': 'Огромный промышленный комплекс. Максимальная производительность.'
            },
            
            # Бизнесы (приносят пассивный доход)
            {
                'name': 'Маленький магазин',
                'category': 'building',
                'base_price': 300,
                'description': 'Небольшая торговая лавка. Приносит 2 ₽/минуту.'
            },
            {
                'name': 'Ресторан',
                'category': 'building',
                'base_price': 800,
                'description': 'Уютное заведение с вкусной едой. Приносит 5 ₽/минуту.'
            },
            {
                'name': 'Таверна',
                'category': 'building',
                'base_price': 600,
                'description': 'Популярное место отдыха моряков. Приносит 4 ₽/минуту.'
            },
            {
                'name': 'Гостиница',
                'category': 'building',
                'base_price': 1200,
                'description': 'Комфортабельный отель для путешественников. Приносит 8 ₽/минуту.'
            },
            {
                'name': 'Рынок',
                'category': 'building',
                'base_price': 1500,
                'description': 'Центр торговли. Приносит 10 ₽/минуту.'
            },
            
            # Жилые дома (увеличивают население)
            {
                'name': 'Маленький дом',
                'category': 'building',
                'base_price': 200,
                'description': 'Небольшой дом для одной семьи. +5 жителей.'
            },
            {
                'name': 'Большой дом',
                'category': 'building',
                'base_price': 400,
                'description': 'Просторный дом для нескольких семей. +10 жителей.'
            },
            {
                'name': 'Особняк',
                'category': 'building',
                'base_price': 1000,
                'description': 'Роскошный особняк для знати. +25 жителей.'
            },
            {
                'name': 'Доходный дом',
                'category': 'building',
                'base_price': 600,
                'description': 'Многоквартирный дом. +15 жителей.'
            },
            
            # Склады (увеличивают вместимость)
            {
                'name': 'Маленький склад',
                'category': 'building',
                'base_price': 250,
                'description': 'Небольшое хранилище. +100 ед. вместимости.'
            },
            {
                'name': 'Большой склад',
                'category': 'building',
                'base_price': 600,
                'description': 'Вместительное хранилище. +250 ед. вместимости.'
            },
            {
                'name': 'Портовый склад',
                'category': 'building',
                'base_price': 1200,
                'description': 'Огромный склад в порту. +500 ед. вместимости.'
            },
            
            # Фермы (производят ресурсы)
            {
                'name': 'Небольшая ферма',
                'category': 'building',
                'base_price': 400,
                'description': 'Производит 5 ед. продуктов в час.'
            },
            {
                'name': 'Плантация',
                'category': 'building',
                'base_price': 900,
                'description': 'Производит 12 ед. продуктов в час.'
            },
            {
                'name': 'Животноводческая ферма',
                'category': 'building',
                'base_price': 700,
                'description': 'Производит 8 ед. мяса в час.'
            },
        ]

        # === РЕСУРСЫ ДЛЯ ОСТРОВА ===
        resources = [
            {
                'name': 'Кофейные зерна',
                'category': 'resource',
                'base_price': 10,
                'description': 'Ароматные зерна для приготовления кофе.'
            },
            {
                'name': 'Какао бобы',
                'category': 'resource',
                'base_price': 12,
                'description': 'Сырье для производства шоколада.'
            },
            {
                'name': 'Табак',
                'category': 'resource',
                'base_price': 15,
                'description': 'Листья табака для производства сигар.'
            },
            {
                'name': 'Тростник',
                'category': 'resource',
                'base_price': 8,
                'description': 'Сладкий тростник для производства сахара и рома.'
            },
            {
                'name': 'Древесина',
                'category': 'resource',
                'base_price': 5,
                'description': 'Строительный материал из деревьев.'
            },
            {
                'name': 'Камень',
                'category': 'resource',
                'base_price': 7,
                'description': 'Прочный материал для строительства.'
            },
            {
                'name': 'Железная руда',
                'category': 'resource',
                'base_price': 20,
                'description': 'Сырье для производства металла.'
            },
            {
                'name': 'Уголь',
                'category': 'resource',
                'base_price': 15,
                'description': 'Топливо для заводов и паровых машин.'
            },
            {
                'name': 'Хлопок',
                'category': 'resource',
                'base_price': 6,
                'description': 'Сырье для производства ткани.'
            },
        ]

        # === ТОВАРЫ ДЛЯ ВЕЛИКОБРИТАНИИ (с динамической ценой) ===
        goods = [
            {
                'name': 'Ткань',
                'category': 'goods',
                'base_price': 20,
                'pmax': 20,
                'n_for_drop': 5,
                't_recovery': 300,
                'description': 'Качественная ткань для пошива одежды.'
            },
            {
                'name': 'Ром',
                'category': 'goods',
                'base_price': 15,
                'pmax': 15,
                'n_for_drop': 5,
                't_recovery': 300,
                'description': 'Крепкий напиток, любимый моряками.'
            },
            {
                'name': 'Инструменты',
                'category': 'goods',
                'base_price': 25,
                'pmax': 25,
                'n_for_drop': 5,
                't_recovery': 300,
                'description': 'Качественные инструменты для работы.'
            },
            {
                'name': 'Оружие',
                'category': 'goods',
                'base_price': 30,
                'pmax': 30,
                'n_for_drop': 5,
                't_recovery': 300,
                'description': 'Надежное оружие для защиты и нападения.'
            },
            {
                'name': 'Предметы роскоши',
                'category': 'goods',
                'base_price': 50,
                'pmax': 50,
                'n_for_drop': 3,
                't_recovery': 600,
                'description': 'Дорогие товары для знати.'
            },
            {
                'name': 'Пряности',
                'category': 'goods',
                'base_price': 40,
                'pmax': 40,
                'n_for_drop': 4,
                't_recovery': 450,
                'description': 'Экзотические специи из колоний.'
            },
        ]

        # === КОРАБЛИ ===
        ships = [
            {
                'name': 'Шхуна',
                'category': 'ship',
                'base_price': 500,
                'description': 'Небольшое быстрое судно для торговли.'
            },
            {
                'name': 'Бриг',
                'category': 'ship',
                'base_price': 1000,
                'description': 'Среднее торговое судно.'
            },
            {
                'name': 'Фрегат',
                'category': 'ship',
                'base_price': 2000,
                'description': 'Боевой корабль с хорошей скоростью.'
            },
            {
                'name': 'Линкор',
                'category': 'ship',
                'base_price': 5000,
                'description': 'Мощный военный корабль.'
            },
            {
                'name': 'Паровой фрегат',
                'category': 'ship',
                'base_price': 8000,
                'description': 'Современный корабль с паровым двигателем.'
            },
            {
                'name': 'Торговое судно',
                'category': 'ship',
                'base_price': 3000,
                'description': 'Большое грузовое судно.'
            },
        ]

        # === ШЕСТЕРНИ (для завода) ===
        gears = [
            {
                'name': 'Шестерня',
                'category': 'gear',
                'base_price': 2,
                'description': 'Деталь для механизмов и заводов.'
            },
            {
                'name': 'Крупная шестерня',
                'category': 'gear',
                'base_price': 5,
                'description': 'Усиленная шестерня для тяжелых механизмов.'
            },
        ]

        # === ПЛАТЕЖИ И ШТРАФЫ ===
        payments = [
            {
                'name': 'Каперский платеж',
                'category': 'other',
                'base_price': 50,
                'description': 'Ежемесячный платеж за каперскую лицензию.'
            },
            {
                'name': 'Штраф за нарушение',
                'category': 'fine',
                'base_price': 100,
                'description': 'Стандартный штраф за нарушение правил.'
            },
            {
                'name': 'Судебная пошлина',
                'category': 'fine',
                'base_price': 50,
                'description': 'Платеж за рассмотрение дела в суде.'
            },
            {
                'name': 'Обработка ресурса',
                'category': 'processing',
                'base_price': 5,
                'description': 'Стоимость обработки единицы ресурса на фабрике.'
            },
        ]

        # Объединяем все
        all_items = buildings + resources + goods + ships + gears + payments
        
        # Создаем записи
        created_count = 0
        updated_count = 0
        existing_count = 0
        
        self.stdout.write(self.style.NOTICE('Начинаем инициализацию прайс-листа...'))
        
        for item in all_items:
            obj, created = PriceList.objects.update_or_create(
                name=item['name'],
                defaults={
                    'category': item['category'],
                    'base_price': item['base_price'],
                    'pmax': item.get('pmax', None),
                    'n_for_drop': item.get('n_for_drop', None),
                    't_recovery': item.get('t_recovery', None),
                    'description': item.get('description', ''),
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Создано: {item["name"]}'))
            else:
                # Проверяем, было ли обновление
                if (obj.category != item['category'] or 
                    obj.base_price != item['base_price']):
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'  ↻ Обновлено: {item["name"]}'))
                else:
                    existing_count += 1
        
        # Выводим статистику
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Инициализация завершена!'))
        self.stdout.write(f'  Создано новых записей: {created_count}')
        self.stdout.write(f'  Обновлено записей: {updated_count}')
        self.stdout.write(f'  Существовало без изменений: {existing_count}')
        self.stdout.write(f'  Всего записей в прайс-листе: {PriceList.objects.count()}')
        
        # Показываем распределение по категориям
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.NOTICE('Распределение по категориям:'))
        for category_code, category_name in PriceList.CATEGORY_CHOICES:
            count = PriceList.objects.filter(category=category_code).count()
            if count > 0:
                self.stdout.write(f'  {category_name}: {count}')