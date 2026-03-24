
from django.contrib import admin
from .models import (
    UserSession, LogEntry, PriceList, Convict, 
    ConstructedBuilding, Credit, Privateer, DynamicPrice,
    Quest
)

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['username', 'table', 'created_at', 'is_active']
    list_filter = ['table', 'is_active']
    search_fields = ['username', 'session_id']
    readonly_fields = ['session_id', 'created_at']

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'author', 'table', 'action_type', 'player_id']
    list_filter = ['table', 'action_type', 'timestamp']
    search_fields = ['author', 'player_id']
    readonly_fields = ['timestamp', 'details']
    date_hierarchy = 'timestamp'

@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'base_price', 'updated_at']
    list_filter = ['category']
    search_fields = ['name']
    list_editable = ['base_price']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'category', 'base_price', 'description')
        }),
        ('Динамические цены (для товаров)', {
            'fields': ('pmax', 'n_for_drop', 't_recovery'),
            'classes': ('collapse',),
            'description': 'Заполняется только для товаров с динамической ценой'
        }),
    )

@admin.register(Convict)
class ConvictAdmin(admin.ModelAdmin):
    list_display = ['player_id', 'player_name', 'sentence_years', 'fine_amount', 'confiscation', 'sentenced_at']
    list_filter = ['sentence_years', 'confiscation', 'sentenced_at']
    search_fields = ['player_id', 'player_name', 'crime_description']
    readonly_fields = ['sentenced_at']
    date_hierarchy = 'sentenced_at'

@admin.register(ConstructedBuilding)
class ConstructedBuildingAdmin(admin.ModelAdmin):
    list_display = ['building_name', 'building_type', 'owner_id', 'built_by', 'built_at', 'cost']
    list_filter = ['building_type', 'built_at']
    search_fields = ['building_name', 'owner_id', 'built_by']
    readonly_fields = ['built_at']
    date_hierarchy = 'built_at'

@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    list_display = ['player_id', 'credit_amount', 'monthly_payment', 'remaining_payments', 'issued_at']
    list_filter = ['term_months', 'issued_at']
    search_fields = ['player_id', 'issued_by']
    readonly_fields = ['issued_at', 'last_payment_at']

@admin.register(Privateer)
class PrivateerAdmin(admin.ModelAdmin):
    list_display = ['player_id', 'ship_type', 'complaints', 'is_active', 'licensed_at']
    list_filter = ['ship_type', 'is_active', 'licensed_at']
    search_fields = ['player_id', 'licensed_by']
    readonly_fields = ['licensed_at', 'last_payment_at']

@admin.register(DynamicPrice)
class DynamicPriceAdmin(admin.ModelAdmin):
    list_display = ['good_name', 'current_price', 'pmax', 'pmin', 'sales_count', 'last_update']
    list_filter = ['good_name']
    search_fields = ['good_name']
    readonly_fields = ['last_update']
    list_editable = ['current_price']

@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = ['id', 'player_id', 'reward', 'is_active', 'is_public', 'issued_at']
    list_filter = ['is_active', 'is_public', 'issued_at']
    search_fields = ['player_id', 'description', 'issued_by']
    readonly_fields = ['issued_at', 'completed_at']
    date_hierarchy = 'issued_at'