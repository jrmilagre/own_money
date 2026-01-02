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


@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'created_at', 'updated_at')
    search_fields = ('full_name',)
    ordering = ('full_name',)