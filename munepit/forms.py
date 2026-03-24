# munepit/forms.py
from django import forms
from django.db.models import Q
from .models import *

class UserLoginForm(forms.Form):
    """Форма авторизации за столом"""
    username = forms.CharField(
        max_length=100,
        label="Имя пользователя",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваше имя',
            'autofocus': True
        })
    )
    table = forms.ChoiceField(
        choices=[('island', 'Остров'), ('britain', 'Великобритания')],
        label="Выберите стол",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )


class DealForm(forms.Form):
    """Форма сделки между игроками"""
    player_a = forms.CharField(
        max_length=50,
        label="Игрок A",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока A'
        })
    )
    player_b = forms.CharField(
        max_length=50,
        label="Игрок B",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока B'
        })
    )
    description = forms.CharField(
        label="Описание сделки",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Опишите условия сделки'
        })
    )


class CourtForm(forms.ModelForm):
    """Форма суда"""

    money_input = forms.DecimalField(
        label='Внесено денег',
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    class Meta:
        model = Convict
        fields = ['player_id', 'player_name', 'crime_description', 'fine_amount', 'confiscation', 'sentence_years']
        labels = {
            'player_id': 'Номер подсудимого',
            'player_name': 'ФИО игрока',
            'crime_description': 'Описание преступления',
            'fine_amount': 'Сумма штрафа',
            'confiscation': 'Конфискация имущества',
            'sentence_years': 'Срок каторги (лет)',
        }
        widgets = {
            'player_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: 12345'
            }),
            'player_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ФИО игрока (необязательно)'
            }),
            'crime_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Опишите преступление'
            }),
            'fine_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'confiscation': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'sentence_years': forms.Select(attrs={
                'class': 'form-control'
            }, choices=[(0, '0 лет'), (1, '1 год'), (2, '2 года'), (3, '3 года'), (4, '4 года'), (5, '5 лет')]),
        }


class ConvictReleaseForm(forms.Form):
    """Форма выхода с каторги"""
    
    player = forms.ModelChoiceField(
        queryset=Convict.objects.all(),
        label="Выберите игрока",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите каторжника ---------",
        required=True,
        error_messages={
            'required': 'Пожалуйста, выберите игрока',
            'invalid_choice': 'Выбран некорректный игрок'
        }
    )
    
    early_release = forms.ChoiceField(
        choices=[('True', 'Да'), ('False', 'Нет')],
        label="Досрочное освобождение",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='False',
        required=True
    )
    
    time_served = forms.CharField(
        required=False,
        label="Время на каторге",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'id': 'time_served_display'
        })
    )
    
    def clean_early_release(self):
        """Преобразуем строковое значение в булево"""
        value = self.cleaned_data.get('early_release')
        return value == 'True'

class ResourcePurchaseForm(forms.Form):
    """Покупка ресурса"""
    
    resource = forms.ModelChoiceField(
        queryset=PriceList.objects.filter(category='resource'),
        label="Выберите ресурс",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите ресурс ---------",
        required=True
    )
    
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        }),
        required=True
    )
    
    quantity = forms.IntegerField(
        label="Количество",
        min_value=1,
        max_value=1000,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '1000'
        }),
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Обновляем queryset при инициализации
        self.fields['resource'].queryset = PriceList.objects.filter(category='resource').order_by('name')


class ResourceProcessingForm(forms.Form):
    """Обработка ресурса на фабрике"""
    
    factory = forms.ModelChoiceField(
        queryset=ConstructedBuilding.objects.filter(
            Q(building_type='factory') |
            Q(building_type='фабрика') |
            Q(building_name__icontains='фабрика')
        ).order_by('building_name'),
        label="Выберите фабрику",
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'}),
        empty_label="--------- Выберите фабрику ---------",
        required=True
    )
    
    quantity = forms.IntegerField(
        label="Количество ресурса",
        min_value=1,
        max_value=1000,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'min': '1',
            'max': '1000',
            'id': 'quantity_input'
        }),
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Обновляем queryset при инициализации
        self.fields['factory'].queryset = ConstructedBuilding.objects.filter(
            Q(building_type='factory') |
            Q(building_type='фабрика') |
            Q(building_name__icontains='фабрика')
        ).order_by('building_name')





class BuildingForm(forms.Form):
    """Форма постройки здания"""
    
    building = forms.ModelChoiceField(
        queryset=PriceList.objects.filter(
            Q(category='building') | 
            Q(category='factory') | 
            Q(category='business')
        ).order_by('base_price'),
        label="Выберите здание",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите здание ---------",
        required=True,
        error_messages={
            'required': 'Пожалуйста, выберите здание',
            'invalid_choice': 'Выбрано некорректное здание'
        }
    )
    
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока (владелец)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        }),
        required=True,
        error_messages={
            'required': 'Пожалуйста, введите номер игрока'
        }
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Обновляем queryset при инициализации
        self.fields['building'].queryset = PriceList.objects.filter(
            Q(category='building') | 
            Q(category='factory') | 
            Q(category='business')
        ).order_by('base_price')


class QuestForm(forms.Form):
    """Форма для работы с заданиями каперов"""
    
    MODE_CHOICES = [
        ('issue', '📢 Выдать задание (всем)'),
        ('assign', '🎯 Назначить конкретному каперу'),
        ('complete', '✅ Отметить выполнение'),
    ]
    
    mode = forms.ChoiceField(
        choices=MODE_CHOICES,
        label="Режим работы",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='issue'
    )
    
    # Для выдачи всем или конкретному каперу
    privateer = forms.ModelChoiceField(
        queryset=Privateer.objects.filter(is_active=True),
        label="Выберите капера",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Для публичного задания
    is_public = forms.BooleanField(
        required=False,
        label="Сделать публичным (видят все каперы)",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        initial=True
    )
    
    # Для выдачи задания
    reward = forms.DecimalField(
        label="Сумма награды",
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    description = forms.CharField(
        label="Описание задания",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Опишите задание...'
        })
    )
    
    # Для выполнения задания
    quest = forms.ModelChoiceField(
        queryset=Quest.objects.filter(is_active=True),
        label="Выберите задание",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Кто выполняет
    completer = forms.ModelChoiceField(
        queryset=Privateer.objects.filter(is_active=True),
        label="Кто выполняет",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('mode')
        
        if mode == 'issue':
            if not cleaned_data.get('reward'):
                self.add_error('reward', 'Укажите сумму награды')
            if not cleaned_data.get('description'):
                self.add_error('description', 'Опишите задание')
                
        elif mode == 'assign':
            if not cleaned_data.get('privateer'):
                self.add_error('privateer', 'Выберите капера')
            if not cleaned_data.get('reward'):
                self.add_error('reward', 'Укажите сумму награды')
            if not cleaned_data.get('description'):
                self.add_error('description', 'Опишите задание')
                
        elif mode == 'complete':
            if not cleaned_data.get('quest'):
                self.add_error('quest', 'Выберите задание')
            if not cleaned_data.get('completer'):
                self.add_error('completer', 'Укажите, кто выполняет')
        
        return cleaned_data





class BusinessProfitForm(forms.Form):
    """Получение прибыли от бизнеса/фабрики"""
    business = forms.ModelChoiceField(
        queryset=ConstructedBuilding.objects.filter(
            Q(building_type='business') |
            Q(building_type='factory') |
            Q(building_type='other', building_name__iregex=r'(магазин|ресторан|таверн|гостиниц|рынок|бизнес|фабрик|ферм|плантац|завод)')
        ),
        label="Выберите объект (бизнес/фабрика)",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите объект ---------"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Принудительно обновляем queryset
        self.fields['business'].queryset = ConstructedBuilding.objects.filter(
            Q(building_type='business') |
            Q(building_type='factory') |
            Q(building_type='other', building_name__iregex=r'(магазин|ресторан|таверн|гостиниц|рынок|бизнес|фабрик|ферм|плантац|завод)')
        )
        print(f"BusinessProfitForm инициализирована. Объектов: {self.fields['business'].queryset.count()}")


class BuildingDemolitionForm(forms.Form):
    """Снос здания"""
    building = forms.ModelChoiceField(
        queryset=ConstructedBuilding.objects.all(),
        label="Выберите здание для сноса",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите здание ---------"
    )
    demolisher_id = forms.CharField(
        max_length=50,
        label="Номер игрока (кто сносит)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        })
    )


# Формы для стола "Великобритания"
class GoodsSaleForm(forms.Form):
    """Продажа товара с динамической ценой"""
    
    good = forms.ModelChoiceField(
        queryset=PriceList.objects.filter(
            Q(category='goods') | Q(category='resource')
        ).order_by('category', 'name'),
        label="Выберите товар",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите товар ---------",
        required=True
    )
    
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        }),
        required=True
    )
    
    quantity = forms.IntegerField(
        label="Количество",
        min_value=1,
        max_value=1000,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '1000'
        }),
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Обновляем queryset при инициализации
        self.fields['good'].queryset = PriceList.objects.filter(
            Q(category='goods') | Q(category='resource')
        ).order_by('category', 'name')


class ShipDealForm(forms.Form):
    """Сделка с кораблем"""
    
    ship = forms.ModelChoiceField(
        queryset=PriceList.objects.filter(category='ship').order_by('base_price'),
        label="Выберите корабль",
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'}),
        empty_label="--------- Выберите корабль ---------",
        required=True
    )
    
    DEAL_TYPES = [
        ('buy', 'Покупка'),
        ('sell', 'Продажа'),
    ]
    
    deal_type = forms.ChoiceField(
        choices=DEAL_TYPES,
        label="Тип сделки",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='buy',
        required=True
    )
    
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Введите номер игрока'
        }),
        required=True
    )
    
    money_input = forms.DecimalField(
        label="Внесено денег",
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        deal_type = cleaned_data.get('deal_type')
        money_input = cleaned_data.get('money_input')
        
        if deal_type == 'buy' and (not money_input or money_input <= 0):
            self.add_error('money_input', 'Для покупки необходимо указать сумму больше 0')
        
        return cleaned_data

class BrickWorkForm(forms.Form):
    """Работа на заводе - производство кирпичей"""
    
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        })
    )
    
    quantity = forms.IntegerField(
        label="Количество кирпичей",
        min_value=1,
        max_value=1000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '1000',
            'value': '1'
        })
    )



class FactoryWorkForm(forms.Form):
    """Работа на заводе - упрощенная форма"""
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Введите номер игрока'
        })
    )
    quantity = forms.IntegerField(
        label="Количество шестерен",
        min_value=1,
        max_value=1000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'min': '1',
            'max': '1000',
            'value': '1'
        })
    )

class CreditIssueForm(forms.Form):
    """Выдача кредита"""
    TERM_CHOICES = [(i, f'{i} платежей') for i in range(2, 7)]
    
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        })
    )
    credit_amount = forms.DecimalField(
        label="Сумма кредита",
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    term = forms.ChoiceField(
        choices=TERM_CHOICES,
        label="Срок кредита",
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class CreditPaymentForm(forms.Form):
    """Внесение платежа по кредиту"""
    debtor = forms.ModelChoiceField(
        queryset=Credit.objects.all(),
        label="Выберите должника",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите должника ---------"
    )
    payment_amount = forms.DecimalField(
        label="Сумма взноса",
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )




class CoalPurchaseForm(forms.Form):
    """Покупка угля (без внесения денег)"""
    
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        })
    )
    
    quantity = forms.IntegerField(
        label="Количество тонн",
        min_value=1,
        max_value=10000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '10000',
            'value': '1'
        })
    )


class PrivateerLicenseForm(forms.Form):
    """Выдача/разжалование капера"""
    ACTION_CHOICES = [
        ('issue', 'Выдать лицензию'),
        ('dismiss', 'Разжаловать'),
    ]
    SHIP_CHOICES = [
        ('frigate', 'Фрегат'),
        ('battleship', 'Линкор'),
        ('steam_frigate', 'Паровой фрегат'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        label="Действие",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        })
    )
    ship_type = forms.ChoiceField(
        choices=SHIP_CHOICES,
        label="Тип корабля",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class PrivateerChangeShipForm(forms.Form):
    """Смена корабля капера"""
    SHIP_CHOICES = [
        ('frigate', 'Фрегат'),
        ('battleship', 'Линкор'),
        ('steam_frigate', 'Паровой фрегат'),
    ]
    
    privateer = forms.ModelChoiceField(
        queryset=Privateer.objects.filter(is_active=True),
        label="Выберите капера",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите капера ---------"
    )
    new_ship = forms.ChoiceField(
        choices=SHIP_CHOICES,
        label="Новый корабль",
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class PrivateerComplaintForm(forms.Form):
    """Подача жалобы на капера"""
    privateer = forms.ModelChoiceField(
        queryset=Privateer.objects.filter(is_active=True),
        label="Выберите капера",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите капера ---------"
    )
    complaint_value = forms.IntegerField(
        label="Значение жалобы (можно отрицательное)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите число'
        })
    )


class PrivateerPaymentForm(forms.Form):
    """Внесение платежа капером"""
    privateer = forms.ModelChoiceField(
        queryset=Privateer.objects.filter(is_active=True),
        label="Выберите капера",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите капера ---------"
    )


class QuestForm(forms.Form):
    """Форма для работы с заданиями"""
    
    MODE_CHOICES = [
        ('issue', '📢 Выдать задание (всем)'),
        ('assign', '🎯 Назначить конкретному каперу'),
        ('complete', '✅ Отметить выполнение'),
    ]
    
    mode = forms.ChoiceField(
        choices=MODE_CHOICES,
        label="Режим работы",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    # Для выдачи всем или конкретному каперу
    privateer = forms.ModelChoiceField(
        queryset=Privateer.objects.filter(is_active=True),
        label="Выберите капера",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Для публичного задания
    is_public = forms.BooleanField(
        required=False,
        label="Сделать публичным (видят все каперы)",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Для выдачи задания
    reward = forms.DecimalField(
        label="Сумма награды",
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    description = forms.CharField(
        label="Описание задания",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Опишите задание...'
        })
    )
    
    # Для выполнения задания
    quest = forms.ModelChoiceField(
        queryset=Quest.objects.filter(is_active=True),
        label="Выберите задание",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Кто выполняет
    completer = forms.ModelChoiceField(
        queryset=Privateer.objects.filter(is_active=True),
        label="Кто выполняет",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('mode')
        
        if mode == 'issue':
            if not cleaned_data.get('reward'):
                raise forms.ValidationError("Укажите сумму награды")
            if not cleaned_data.get('description'):
                raise forms.ValidationError("Опишите задание")
                
        elif mode == 'assign':
            if not cleaned_data.get('privateer'):
                raise forms.ValidationError("Выберите капера")
            if not cleaned_data.get('reward'):
                raise forms.ValidationError("Укажите сумму награды")
            if not cleaned_data.get('description'):
                raise forms.ValidationError("Опишите задание")
                
        elif mode == 'complete':
            if not cleaned_data.get('quest'):
                raise forms.ValidationError("Выберите задание")
            if not cleaned_data.get('completer'):
                raise forms.ValidationError("Укажите, кто выполняет")
        
        return cleaned_data