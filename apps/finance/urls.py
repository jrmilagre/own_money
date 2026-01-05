from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.finance_home, name='finance_home'),
    path('accounts/', views.accounts_list, name='accounts_list'),
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/<int:account_id>/update/', views.account_update, name='account_update'),
    path('accounts/<int:account_id>/delete/', views.account_delete, name='account_delete'),
    path('credit-cards/', views.credit_cards_list, name='credit_cards_list'),
    path('beneficiaries/', views.beneficiaries_list, name='beneficiaries_list'),
    path('categories/', views.categories_list, name='categories_list'),
    path('transactions/', views.transactions_list, name='transactions_list'),
    path('transactions/create/', views.transaction_type_select, name='transaction_type_select'),
    path('transactions/create/simple/', views.transaction_create, name='transaction_create'),
    path('transactions/create/transfer/', views.transfer_create, name='transfer_create'),
    path('transactions/create/composite/', views.composite_transaction_create, name='composite_transaction_create'),
    path('transactions/<int:transaction_id>/update/', views.transaction_update, name='transaction_update'),
    path('transactions/<int:transaction_id>/update/transfer/', views.transfer_update, name='transfer_update'),
    path('transactions/<int:transaction_id>/update/composite/', views.composite_transaction_update, name='composite_transaction_update'),
    path('transactions/<int:transaction_id>/delete/', views.transaction_delete, name='transaction_delete'),
    path('transactions/<int:transaction_id>/delete/transfer/', views.transfer_delete, name='transfer_delete'),
    path('transactions/<int:transaction_id>/delete/composite/', views.composite_transaction_delete, name='composite_transaction_delete'),
    path('account/<int:account_id>/statement/', views.account_statement, name='account_statement'),
]

