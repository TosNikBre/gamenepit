# urls.py
from django.urls import path
from munepit import views

urlpatterns = [
    # Авторизация
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction_detail'),
    path('statistics/', views.statistics, name='statistics'),
    path('statistics/<str:table>/', views.statistics, name='statistics_table'),
    
    # Поиск игрока
    path('player/search/', views.player_search, name='player_search'),
    path('player/<str:player_id>/', views.player_detail, name='player_detail'),
    # Стол "Остров"
    path('island/', views.island_dashboard, name='island_dashboard'),
    path('island/deal/', views.island_deal, name='island_deal'),
    path('island/deal/confirm/', views.island_deal_confirm, name='island_deal_confirm'),
    path('island/court/', views.island_court, name='island_court'),
    path('island/court/confirm/', views.island_court_confirm, name='island_court_confirm'),
    path('island/release/', views.island_release, name='island_release'),
    path('island/purchase/', views.island_purchase_resource, name='island_purchase_resource'),
    path('island/purchase/confirm/', views.island_purchase_confirm, name='island_purchase_confirm'),
    path('island/build/', views.island_build, name='island_build'),
    path('island/build/confirm/', views.island_build_confirm, name='island_build_confirm'),
    path('island/process/', views.island_process_resource, name='island_process_resource'),
    path('island/process/confirm/', views.island_process_confirm, name='island_process_confirm'),
    path('island/profit/', views.island_profit, name='island_profit'),
    path('island/demolish/', views.island_demolish, name='island_demolish'),
    path('island/demolish/confirm/', views.island_demolish_confirm, name='island_demolish_confirm'),
    
    # Стол "Великобритания"
    path('britain/', views.britain_dashboard, name='britain_dashboard'),
    path('britain/sale/', views.britain_sale, name='britain_sale'),
    path('britain/ship-deal/', views.britain_ship_deal, name='britain_ship_deal'),
    path('britain/factory-work/', views.britain_factory_work, name='britain_factory_work'),
    path('britain/credits/', views.britain_credits, name='britain_credits'),
    path('britain/credit-issue/', views.britain_credit_issue, name='britain_credit_issue'),
    path('britain/credit-confirm/', views.britain_credit_confirm, name='britain_credit_confirm'),
    path('britain/credit-payment/', views.britain_credit_payment, name='britain_credit_payment'),
    path('britain/coal/', views.britain_coal, name='britain_coal'),
    path('britain/privateers/', views.britain_privateers, name='britain_privateers'),
    path('britain/privateer-license/', views.britain_privateer_license, name='britain_privateer_license'),
    path('britain/privateer-change-ship/', views.britain_privateer_change_ship, name='britain_privateer_change_ship'),
    path('britain/privateer-complaint/', views.britain_privateer_complaint, name='britain_privateer_complaint'),
    path('britain/privateer-payment/', views.britain_privateer_payment, name='britain_privateer_payment'),
    path('britain/quest/', views.britain_quest, name='britain_quest'),
    
    # API endpoints
    path('api/building-profit/', views.api_get_building_profit, name='api_building_profit'),
    path('api/convict-time/', views.api_get_convict_time, name='api_convict_time'),
    path('api/dynamic-price/', views.api_get_dynamic_price, name='api_dynamic_price'),
]