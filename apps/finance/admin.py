from django.contrib import admin
from .models import *

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'institution',
        'account_type',
        'is_favorite',
        'is_closed',
    )
    search_fields = ('name', 'institution', 'number', 'abbreviation')
    list_filter = ('account_type', 'is_favorite', 'is_closed')
    ordering = ('name',)
