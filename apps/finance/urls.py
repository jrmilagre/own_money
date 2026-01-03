from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('account/<int:account_id>/statement/', views.account_statement, name='account_statement'),
]

