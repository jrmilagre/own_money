from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.finance_home, name='finance_home'),
    path('accounts/', views.accounts_list, name='accounts_list'),
    path('credit-cards/', views.credit_cards_list, name='credit_cards_list'),
    path('beneficiaries/', views.beneficiaries_list, name='beneficiaries_list'),
    path('categories/', views.categories_list, name='categories_list'),
    path('transactions/', views.transactions_list, name='transactions_list'),
    path('account/<int:account_id>/statement/', views.account_statement, name='account_statement'),
]

