# munepit/forms.py
from django import forms
from .models import Convict, ConstructedBuilding, Credit, Privateer, PriceList  # Добавлен PriceList

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
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    early_release = forms.ChoiceField(
        choices=[(True, 'Да'), (False, 'Нет')],
        label="Досрочное освобождение",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    time_served = forms.CharField(
        required=False,
        label="Время на каторге",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )


class ResourcePurchaseForm(forms.Form):
    """Покупка ресурса"""
    RESOURCE_CHOICES = [
        ('coffee', 'Кофейные зерна'),
        ('cocoa', 'Какао бобы'),
        ('tobacco', 'Табак'),
        ('sugar_cane', 'Тростник'),
    ]
    
    resource = forms.ChoiceField(
        choices=RESOURCE_CHOICES,
        label="Выберите ресурс",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        })
    )
    quantity = forms.IntegerField(
        label="Количество",
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'value': '1'
        })
    )


class BuildingForm(forms.Form):
    """Постройка здания"""
    building = forms.ModelChoiceField(
        queryset=PriceList.objects.filter(category='building'),
        label="Выберите здание",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите здание ---------"
    )
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока (владелец)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        })
    )


class ResourceProcessingForm(forms.Form):
    """Обработка ресурса"""
    factory = forms.ModelChoiceField(
        queryset=ConstructedBuilding.objects.filter(building_type='factory'),
        label="Выберите фабрику",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите фабрику ---------"
    )
    quantity = forms.IntegerField(
        label="Количество ресурса",
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'value': '1'
        })
    )


class BusinessProfitForm(forms.Form):
    """Получение прибыли от бизнеса"""
    business = forms.ModelChoiceField(
        queryset=ConstructedBuilding.objects.filter(building_type='business'),
        label="Выберите бизнес",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите бизнес ---------"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Принудительно обновляем queryset
        self.fields['business'].queryset = ConstructedBuilding.objects.filter(building_type='business')
        print(f"BusinessProfitForm инициализирована. Бизнесов: {self.fields['business'].queryset.count()}")


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
    """Продажа товара"""
    GOODS_CHOICES = [
        ('textile', 'Ткань'),
        ('rum', 'Ром'),
        ('tools', 'Инструменты'),
        ('weapons', 'Оружие'),
    ]
    
    good = forms.ChoiceField(
        choices=GOODS_CHOICES,
        label="Выберите товар",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        })
    )
    quantity = forms.IntegerField(
        label="Количество",
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'value': '1'
        })
    )
    money_input = forms.DecimalField(
        label="Внесено денег",
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )


class ShipDealForm(forms.Form):
    """Сделка с кораблем"""
    SHIP_CHOICES = [
        ('schooner', 'Шхуна'),
        ('brig', 'Бриг'),
        ('frigate', 'Фрегат'),
        ('battleship', 'Линкор'),
        ('steam_frigate', 'Паровой фрегат'),
    ]
    DEAL_TYPES = [
        ('buy', 'Покупка'),
        ('sell', 'Продажа'),
    ]
    
    ship = forms.ChoiceField(
        choices=SHIP_CHOICES,
        label="Выберите корабль",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    deal_type = forms.ChoiceField(
        choices=DEAL_TYPES,
        label="Тип сделки",
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
    money_input = forms.DecimalField(
        label="Внесено денег",
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )


class FactoryWorkForm(forms.Form):
    """Работа на заводе"""
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        })
    )
    quantity = forms.IntegerField(
        label="Количество шестерен",
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'value': '1'
        })
    )
    money_input = forms.DecimalField(
        label="Внесено денег",
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
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
    """Покупка угля"""
    player_id = forms.CharField(
        max_length=50,
        label="Номер игрока",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номер игрока'
        })
    )
    amount = forms.DecimalField(
        label="Сумма сделки",
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    money_input = forms.DecimalField(
        label="Внесено денег",
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
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


class QuestAcceptForm(forms.Form):
    """Принятие задания"""
    privateer = forms.ModelChoiceField(
        queryset=Privateer.objects.filter(is_active=True),
        label="Выберите капера",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--------- Выберите капера ---------"
    )
    reward = forms.DecimalField(
        label="Сумма выплаты",
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    description = forms.CharField(
        label="Суть задания",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Опишите задание'
        })
    )