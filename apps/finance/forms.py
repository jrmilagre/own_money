from django import forms
from django.core.exceptions import ValidationError
from .models import Account, Transaction


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
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
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'institution': forms.TextInput(attrs={'class': 'form-control'}),
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'minimum_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'group': forms.TextInput(attrs={'class': 'form-control'}),
            'abbreviation': forms.TextInput(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_favorite': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_closed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'description',
            'account',
            'credit_card',
            'transaction_type',
            'operation_type',
            'value',
            'category',
            'beneficiary',
            'buy_date',
            'due_date',
            'pay_date',
            'status',
        ]
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'account': forms.Select(attrs={'class': 'form-control'}),
            'credit_card': forms.Select(attrs={'class': 'form-control'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'operation_type': forms.Select(attrs={'class': 'form-control'}),
            'value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'beneficiary': forms.Select(attrs={'class': 'form-control'}),
            'buy_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'pay_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class TransferTransactionForm(forms.Form):
    """Formulário específico para transferências entre contas."""
    source_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_closed=False),
        label='Conta de origem',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    destination_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_closed=False),
        label='Conta de destino',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    value = forms.DecimalField(
        label='Valor',
        max_digits=15,
        decimal_places=2,
        min_value=0.01,
        help_text='Valor sempre positivo',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    description = forms.CharField(
        label='Descrição',
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição opcional'})
    )
    buy_date = forms.DateField(
        label='Data da operação',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    pay_date = forms.DateField(
        label='Data do pagamento efetivo',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        source_account = cleaned_data.get('source_account')
        destination_account = cleaned_data.get('destination_account')
        
        if source_account and destination_account:
            if source_account == destination_account:
                raise ValidationError({
                    'destination_account': ['A conta de destino deve ser diferente da conta de origem.']
                })
        
        return cleaned_data

