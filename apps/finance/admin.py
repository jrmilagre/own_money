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
    search_fields = ('name', 'institution', 'number', 'abbreviation', 'cardholder', 'card_number')
    list_filter = ('account_type', 'is_favorite', 'is_closed', 'brand')
    ordering = ('name',)
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'name',
                'institution',
                'number',
                'account_type',
                'currency',
                'opening_balance',
                'minimum_balance',
                'group',
                'abbreviation',
                'comment',
                'is_favorite',
                'is_closed',
            )
        }),
        ('Informações de Cartão de Crédito', {
            'fields': (
                'cardholder',
                'card_number',
                'expiration_date',
                'cvv',
                'brand',
            ),
            'classes': ('collapse',),
        }),
    )


@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'created_at', 'updated_at')
    search_fields = ('full_name',)
    ordering = ('full_name',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        'category',
        'subcategory',
        'default_transaction_type',
        'created_at',
        'updated_at',
    )
    search_fields = ('category', 'subcategory')
    list_filter = ('default_transaction_type', 'created_at')
    ordering = ('category', 'subcategory')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'description',
        'account',
        'transaction_type',
        'value',
        'buy_date',
        'pay_date',
        'status',
        'category',
        'operation_type',
        'is_recurring',
    )
    list_display_links = ('id',)
    list_editable = ('status', 'pay_date')
    search_fields = (
        'description',
        'account__name',
        'beneficiary__full_name',
        'category__category',
        'category__subcategory',
    )
    list_filter = (
        'status',
        'transaction_type',
        'operation_type',
        'account',
        'category',
        'buy_date',
        'is_recurring',
        'recurrence_type',
        'recurrence_end_type',
        'is_split',
        'is_split_parent',
    )
    date_hierarchy = 'buy_date'
    ordering = ('-buy_date', '-created_at')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'description',
                'account',
                'transaction_type',
                'operation_type',
                'value',
                'category',
                'beneficiary',
            )
        }),
        ('Datas', {
            'fields': (
                'buy_date',
                'due_date',
                'pay_date',
                'status',
            )
        }),
        ('Estrutura Hierárquica', {
            'fields': (
                'parent_transaction',
                'parent_type',
                'is_split',
                'is_split_parent',
                'split_sequence',
            ),
            'classes': ('collapse',),
        }),
        ('Transferências', {
            'fields': ('destination_account',),
            'classes': ('collapse',),
        }),
        ('Recorrência', {
            'fields': (
                'is_recurring',
                'recurrence_type',
                'recurrence_interval',
                'recurrence_weekdays',
                'recurrence_start_date',
                'recurrence_end_type',
                'recurrence_end_date',
                'recurrence_end_count',
                'recurrence_sequence',
                'recurrence_monthly_day',
            ),
            'classes': ('collapse',),
        }),
        ('Auditoria', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def get_queryset(self, request):
        """Otimiza as consultas com select_related"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'account',
            'destination_account',
            'beneficiary',
            'category',
            'parent_transaction',
        )