# munepit/management/commands/init_prices.py
from django.core.management.base import BaseCommand
from munepit.models import PriceList

class Command(BaseCommand):
    help = 'Инициализация прайс-листа со всеми товарами, зданиями и ресурсами'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить существующие записи перед созданием',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Очистка существующих записей...'))
            PriceList.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Все записи удалены'))

        # === СЫРЬЕ (ресурсы) ===
        recipes = [
            # === ПОЛУФАБРИКАТЫ ===
            {
                'name': 'Какао-порошок',
                'category': 'intermediate',
                'output_quantity': 1,
                'production_time': 6,
                'ingredients': {'Какао-бобы': 8},
                'base_price': 15,
                'description': 'Перемолотые какао-бобы. Основа для шоколада.'
            },
            {
                'name': 'Молотый кофе',
                'category': 'intermediate',
                'output_quantity': 1,
                'production_time': 6,
                'ingredients': {'Кофейные зерна': 8},
                'base_price': 17,
                'description': 'Перемолотые кофейные зерна. Основа для напитков.'
            },
            {
                'name': 'Хлеб',
                'category': 'intermediate',
                'output_quantity': 1,
                'production_time': 8,
                'ingredients': {'Пшеница': 4},
                'base_price': 22,
                'description': 'Выпекается из муки. Базовый продукт питания.'
            },
            {
                'name': 'Сахар',
                'category': 'intermediate',
                'output_quantity': 1,
                'production_time': 10,
                'ingredients': {'Тростник': 2},
                'base_price': 12,
                'description': 'Производится из тростника. Используется в кондитерском деле.'
            },
            {
                'name': 'Табак',
                'category': 'intermediate',
                'output_quantity': 1,
                'production_time': 8,
                'ingredients': {'Табачные листья': 8},
                'base_price': 30,
                'description': 'Обработанные табачные листья. Для производства сигар.'
            },
            {
                'name': 'Ткань',
                'category': 'intermediate',
                'output_quantity': 1,
                'production_time': 8,
                'ingredients': {'Хлопок': 10},
                'base_price': 18,
                'description': 'Производится из хлопка. Необходима для производства одежды.'
            },
            
            # === УПАКОВОЧНЫЙ ТОВАР ===
            {
                'name': 'Упаковочный товар',
                'category': 'intermediate',
                'output_quantity': 1,
                'production_time': 5,
                'ingredients': {'Ткань': 10},
                'base_price': 10,
                'description': 'Упаковка для товаров.'
            },
            
            # === ГОТОВАЯ ПРОДУКЦИЯ ===
            {
                'name': 'Сигары',
                'category': 'finished',
                'output_quantity': 1,
                'production_time': 10,
                'ingredients': {'Табак': 16},
                'base_price': 70,
                'description': 'Элитная продукция из табака.'
            },
            {
                'name': 'Шоколад',
                'category': 'finished',
                'output_quantity': 1,
                'production_time': 10,
                'ingredients': {
                    'Какао-порошок': 10,
                    'Сахар': 10
                },
                'base_price': 60,
                'description': 'Сладость из какао-порошка и сахара.'
            },
            {
                'name': 'Ром',
                'category': 'finished',
                'output_quantity': 1,
                'production_time': 10,
                'ingredients': {'Сахар': 16},
                'base_price': 46,
                'description': 'Крепкий напиток из тростника. Любим пиратами.'
            },
            {
                'name': 'Бисквит',
                'category': 'finished',
                'output_quantity': 1,
                'production_time': 10,
                'ingredients': {
                    'Хлеб': 16,
                    'Сахар': 16
                },
                'base_price': 54,
                'description': 'Кондитерское изделие из муки, сахара и яиц.'
            },
            
            # === ЭЛИТНАЯ ПРОДУКЦИЯ ===
            {
                'name': 'Кофейный ликёр',
                'category': 'elite',
                'output_quantity': 1,
                'production_time': 6,
                'ingredients': {
                    'Ром': 18,
                    'Молотый кофе': 18
                },
                'base_price': 94,
                'description': 'Благородный напиток на основе кофе. Элитный товар.'
            },
            {
                'name': 'Имперский десерт',
                'category': 'elite',
                'output_quantity': 1,
                'production_time': 6,
                'ingredients': {
                    'Бисквит': 20,
                    'Шоколад': 20
                },
                'base_price': 130,
                'description': 'Изысканный десерт для знати. Высочайшее качество.'
            },
        ]
        raw_materials = [
            {
                'name': 'Пшеница',
                'category': 'resource',
                'base_price': 4,
                'pmax': 4,
                'pmin': 1,
                'n_for_drop': 3,
                't_recovery': 10,
                'description': 'Основное сырье для производства муки и хлеба.'
            },
            {
                'name': 'Тростник',
                'category': 'resource',
                'base_price': 3,
                'pmax': 3,
                'pmin': 1,
                'n_for_drop': 3,
                't_recovery': 10,
                'description': 'Сырье для производства сахара и рома.'
            },
            {
                'name': 'Кофейные зерна',
                'category': 'resource',
                'base_price': 7,
                'pmax': 7,
                'pmin': 2,
                'n_for_drop': 3,
                't_recovery': 10,
                'description': 'Сырье для производства молотого кофе и кофейного ликера.'
            },
            {
                'name': 'Какао-бобы',
                'category': 'resource',
                'base_price':6,
                'pmax': 6,
                'pmin': 2,
                'n_for_drop': 3,
                't_recovery': 10,
                'description': 'Сырье для производства какао-порошка и шоколада.'
            },
            {
                'name': 'Табачные листья',
                'category': 'resource',
                'base_price': 8,
                'pmax': 8,
                'pmin': 3,
                'n_for_drop': 3,
                't_recovery': 10,
                'description': 'Сырье для производства табака и сигар.'
            },
            {
                'name': 'Хлопок',
                'category': 'resource',
                'base_price': 4,
                'pmax': 4,
                'pmin': 1,
                'n_for_drop': 3,
                't_recovery': 10,
                'description': 'Сырье для производства ткани.'
            },
        ]

        # === ПОЛУФАБРИКАТЫ ===
        intermediate_products = [
            {
                'name': 'Хлеб',
                'category': 'goods',
                'base_price': 22,
                'pmax': 22,
                'pmin': 10,
                'n_for_drop': 4,
                't_recovery': 8,
                'description': 'Выпекается из муки. Базовый продукт питания.'
            },
            {
                'name': 'Сахар',
                'category': 'goods',
                'base_price': 12,
                'pmax': 12,
                'pmin': 5,
                'n_for_drop': 3,
                't_recovery': 10,
                'description': 'Производится из тростника. Используется в кондитерском деле.'
            },
            {
                'name': 'Молотый кофе',
                'category': 'goods',
                'base_price': 17,
                'pmax': 17,
                'pmin': 8,
                'n_for_drop': 1,
                't_recovery': 6,
                'description': 'Перемолотые кофейные зерна. Основа для напитков.'
            },
            {
                'name': 'Какао-порошок',
                'category': 'goods',
                'base_price': 15,
                'pmax': 15,
                'pmin': 7,
                'n_for_drop': 1,
                't_recovery': 6,
                'description': 'Перемолотые какао-бобы. Основа для шоколада.'
            },
            {
                'name': 'Табак',
                'category': 'goods',
                'base_price': 30,
                'pmax': 30,
                'pmin': 15,
                'n_for_drop': 4,
                't_recovery': 8,
                'description': 'Обработанные табачные листья. Для производства сигар.'
            },
            {
                'name': 'Ткань',
                'category': 'goods',
                'base_price': 18,
                'pmax': 18,
                'pmin': 9,
                'n_for_drop': 4,
                't_recovery': 8,
                'description': 'Производится из хлопка. Необходима для производства одежды.'
            },
        ]

        # === ГОТОВАЯ ПРОДУКЦИЯ ===
        finished_products = [
            {
                'name': 'Бисквит',
                'category': 'goods',
                'base_price': 54,
                'pmax': 54,
                'pmin': 25,
                'n_for_drop': 3,
                't_recovery': 10,
                'description': 'Кондитерское изделие из муки, сахара и яиц.'
            },
            {
                'name': 'Ром',
                'category': 'goods',
                'base_price': 46,
                'pmax': 46,
                'pmin': 20,
                'n_for_drop': 3,
                't_recovery': 10,
                'description': 'Крепкий напиток из тростника. Любим пиратами.'
            },
            {
                'name': 'Шоколад',
                'category': 'goods',
                'base_price': 60,
                'pmax': 60,
                'pmin': 30,
                'n_for_drop': 3,
                't_recovery': 10,
                'description': 'Сладость из какао-порошка и сахара.'
            },
            {
                'name': 'Сигары',
                'category': 'goods',
                'base_price': 70,
                'pmax': 70,
                'pmin': 35,
                'n_for_drop': 3,
                't_recovery': 10,
                'description': 'Элитная продукция из табака.'
            },
        ]

        # === ЭЛИТНАЯ ПРОДУКЦИЯ ===
        elite_products = [
            {
                'name': 'Имперский десерт',
                'category': 'goods',
                'base_price': 130,
                'pmax': 130,
                'pmin': 65,
                'n_for_drop': 1,
                't_recovery': 6,
                'description': 'Изысканный десерт для знати. Высочайшее качество.'
            },
            {
                'name': 'Кофейный ликёр',
                'category': 'goods',
                'base_price': 94,
                'pmax': 94,
                'pmin': 47,
                'n_for_drop': 1,
                't_recovery': 6,
                'description': 'Благородный напиток на основе кофе. Элитный товар.'
            },
        ]

        # === НОВЫЕ ФАБРИКИ ===
        factories = [
            {
                'name': 'Мельница',
                'category': 'factory',
                'base_price': 200,
                'description': 'Перемалывает зерно в муку. Необходима для пекарни.'
            },
            {
                'name': 'Пекарня',
                'category': 'factory',
                'base_price': 500,
                'description': 'Выпекает хлеб из муки. Приносит стабильный доход.'
            },
            {
                'name': 'Сахароварня',
                'category': 'factory',
                'base_price': 300,
                'description': 'Производит сахар из тростника. Сырье для кондитерской.'
            },
            {
                'name': 'Ткацкая фабрика',
                'category': 'factory',
                'base_price': 300,
                'description': 'Производит ткань из хлопка. Основа текстильной промышленности.'
            },
            {
                'name': 'Сушильня',
                'category': 'factory',
                'base_price': 750,
                'description': 'Сушит табачные листья. Подготовка к производству сигар.'
            },
            {
                'name': 'Табачная мануфактура',
                'category': 'factory',
                'base_price': 1200,
                'description': 'Производит сигары высокого качества. Дорогой товар.'
            },
            {
                'name': 'Шоколадная фабрика',
                'category': 'factory',
                'base_price': 1000,
                'description': 'Производит шоколад из какао-бобов. Любимое лакомство.'
            },
            {
                'name': 'Ликероводочный завод',
                'category': 'factory',
                'base_price': 1500,
                'description': 'Производит крепкие напитки. Высокая прибыль.'
            },
            {
                'name': 'Кондитерская',
                'category': 'factory',
                'base_price': 2000,
                'description': 'Производит конфеты и десерты. Элитная продукция.'
            },
        ]

        # === БИЗНЕС ===
        businesses = [
            {
                'name': 'Таверна',
                'category': 'business',
                'base_price': 450,
                'description': 'Место отдыха моряков. Приносит стабильный небольшой доход.'
            },
            {
                'name': 'Постоялый двор',
                'category': 'business',
                'base_price': 800,
                'description': 'Гостиница для путешественников. Средний доход.'
            },
            {
                'name': 'Церковь',
                'category': 'business',
                'base_price': 2500,
                'description': 'Духовный центр. Приносит пожертвования и уважение.'
            },
             {
                'name': 'Ратуша',
                'category': 'business',
                'base_price': 5000,
                'description': 'ыыы'
            },

        ]


        # === КИРПИЧИ ===
        bricks = [
            {
                'name': 'Кирпич',
                'category': 'brick',
                'base_price': 0,
                'description': 'Строительный материал. Используется для получения стартового корабля.'
            },
            {
                'name': 'Кирпичи (стопка)',
                'category': 'brick',
                'base_price': 0,
                'description': 'Стопка из 10 кирпичей.'
            },
        ]

        # === СТАРТОВЫЕ КОРАБЛИ ===
        starter_ships = [
            {
                'name': 'Люггер (базовый) - стартовый',
                'category': 'starter_ship',
                'base_price': 0,
                'description': 'Стартовый корабль для новых игроков. Без орудий.'
            },
            {
                'name': 'Люггер (с орудиями) - стартовый',
                'category': 'starter_ship',
                'base_price': 0,
                'description': 'Стартовый корабль для новых игроков. С орудиями.'
            },
        ]

        # === КОРАБЛИ ===
        ships = [
             {
                'name': 'Шхуна',
                'category': 'ship',
                'base_price': 60,
                'description': 'Самый сильный базовый корабль. Является хорошей опцией на любом этапе игры при своем соотношении цена/качество.'
            },
            {
                'name': 'Барк',
                'category': 'ship',
                'base_price': 500,
                'description': 'Грузовой корабль первого тира. Хорош для торговли, дешев в постройке. Способен принять бой от шхун и Люггеров.'
            },
            {
                'name': 'Баркентина',
                'category': 'ship',
                'base_price': 450,
                'description': 'В отличие от барка, Баркентина меньше в размерах и имеет большую скорость против ветра, что позволяет уходить от военных кораблей первого тира и Галеона. В обмен на это имеет более низкий объем трюма.'
            },
            {
                'name': 'Бриг',
                'category': 'ship',
                'base_price': 600,
                'description': 'Военный корабль первого тира. Позволяет охотиться на Барки и Шхуны, а также уничтожать многие постройки.'
            },
            {
                'name': 'Бригантина',
                'category': 'ship',
                'base_price': 500,
                'description': 'Тот же смысл, что и у баркентины, но вместо объема трюма, снижается кол-во орудий.'
            },
            {
                'name': 'Флейт',
                'category': 'ship',
                'base_price': 800,
                'description': 'Огромный ящик на плаву. Флейт имеет наибольшую вместительность трюма среди всех кораблей, но уязвим к почти любым атакам.'
            },
            {
                'name': 'Клипер',
                'category': 'ship',
                'base_price': 850,
                'description': 'Сбалансированный торговый корабль. Имеет хорошую вместимость, но защищен от всех военных кораблей, кроме корвета.'
            },
            {
                'name': 'Галеон',
                'category': 'ship',
                'base_price': 1200,
                'description': 'Танк морских сражений. Может дать бой почти любому кораблю, но крайне медленный, не в силах навязывать или уходить от боев. Имеет хороший трюм, что добавляет универсальности.'
            },
            {
                'name': 'Корвет',
                'category': 'ship',
                'base_price': 900,
                'description': 'Идеальный корабль пирата или поддержки. Быстрый, хорошо оснащенный. Способен захватить любое торговое судно кроме индиамена, но терпит крах в осаде острова или крупных морских боях.'
            },
            {
                'name': 'Индиамен',
                'category': 'ship',
                'base_price': 1300,
                'description': 'Вершина инженерной мысли торговцев. Индиамен это большой, быстрый и хорошо вооруженный корабль, который способен справиться с любой задачей, будь то перевозка крупных партий грузов, сражение с пиратами или обстрел построек конкурентов.'
            },
            {
                'name': 'Фрегат',
                'category': 'ship',
                'base_price': 1500,
                'description': 'Основа любого флота. Имеет сбалансированные характеристики по части вооружения и скорости и даже неплохой трюм. Ни один корабль не может в одиночку потопить фрегат.'
            },
            {
                'name': 'Линейный корабль',
                'category': 'ship',
                'base_price': 2800,
                'description': 'Плавучая крепость. Линейный корабль имеет астрономически большое количество пушек но крайне посредственную скорость. Основное его назначение — осада фортов, но он способен быть угрозой на море, если снабдить его меньшими судами поддержки.'
            },
            {
                'name': 'Паровой Фрегат',
                'category': 'ship',
                'base_price': 2500,
                'description': 'Тот же фрегат, но с паровым двигателем, дополнительно ускоряющим его в любом направлении, что позволяет догонять и Клипперы, и Индиамены, и даже Корветы.'
            },
        ]

        # === ПЛАТЕЖИ И ШТРАФЫ ===
        payments = [
            # ... (ваши платежи)
        ]

        # Объединяем все
        all_items = (
            raw_materials + intermediate_products + finished_products + elite_products +
            factories + businesses + bricks + starter_ships + ships + payments
        )
        
        # Создаем записи
        created_count = 0
        updated_count = 0
        
        for item in all_items:
            obj, created = PriceList.objects.update_or_create(
                name=item['name'],
                defaults={
                    'category': item['category'],
                    'base_price': item['base_price'],
                    'pmax': item.get('pmax'),
                    'pmin': item.get('pmin'),
                    'n_for_drop': item.get('n_for_drop'),
                    't_recovery': item.get('t_recovery'),
                    'description': item.get('description', ''),
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Создано: {item["name"]}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'  ↻ Обновлено: {item["name"]}'))
        
        # Статистика
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'✅ Инициализация завершена!'))
        self.stdout.write(f'  Создано: {created_count}')
        self.stdout.write(f'  Обновлено: {updated_count}')