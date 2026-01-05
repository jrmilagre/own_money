from django import forms
from django.core.exceptions import ValidationError
from .models import Account, Transaction, Category


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
            'cardholder',
            'card_number',
            'expiration_date',
            'cvv',
            'brand',
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
            'cardholder': forms.TextInput(attrs={'class': 'form-control'}),
            'card_number': forms.TextInput(attrs={'class': 'form-control'}),
            'expiration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'cvv': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornar campos de cartão opcionais
        self.fields['cardholder'].required = False
        self.fields['card_number'].required = False
        self.fields['expiration_date'].required = False
        self.fields['cvv'].required = False
        self.fields['brand'].required = False


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'description',
            'account',
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


class CompositeTransactionForm(forms.Form):
    """Formulário para transações compostas com múltiplas linhas."""
    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_closed=False),
        label='Conta',
        widget=forms.Select(attrs={'class': 'form-control'})
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Campos dinâmicos serão processados no clean()
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Se houver erros nos campos base, não valida as linhas
        if self.errors:
            return cleaned_data
        
        # Processa linhas dinâmicas do formulário
        lines = []
        line_count = 0
        
        # Conta quantas linhas foram enviadas
        while True:
            value_key = f'line_{line_count}_value'
            if value_key not in self.data:
                break
            line_count += 1
        
        if line_count == 0:
            raise ValidationError('Adicione pelo menos uma linha de transação.')
        
        # Valida cada linha
        line_error_messages = []
        for i in range(line_count):
            value = self.data.get(f'line_{i}_value')
            # Busca o tipo de transação (pode vir de um input hidden se o select estiver disabled)
            transaction_type = self.data.get(f'line_{i}_transaction_type')
            # Se não encontrou, tenta buscar de uma lista (pode haver hidden + disabled select)
            if not transaction_type:
                transaction_type_list = self.data.getlist(f'line_{i}_transaction_type')
                if transaction_type_list:
                    transaction_type = transaction_type_list[0] if transaction_type_list else ''
            # Verifica se é transferência via checkbox
            is_transfer = self.data.get(f'line_{i}_is_transfer') == 'on'
            line_type = 'transfer' if is_transfer else 'normal'
            category_id = self.data.get(f'line_{i}_category')
            destination_account_id = self.data.get(f'line_{i}_destination_account')
            description = self.data.get(f'line_{i}_description', '')
            
            # Valida valor
            try:
                value = float(value) if value else None
                if value is None or value <= 0:
                    line_error_messages.append(f'Linha {i+1}: Valor deve ser maior que zero.')
                    continue
            except (ValueError, TypeError):
                line_error_messages.append(f'Linha {i+1}: Valor inválido.')
                continue
            
            # Valida tipo de linha primeiro
            if line_type not in ['normal', 'transfer']:
                line_error_messages.append(f'Linha {i+1}: Tipo de linha inválido.')
                continue
            
            # Para transferências, sempre força DB (débito na conta principal)
            if line_type == 'transfer':
                transaction_type = 'DB'
            
            # Valida tipo de transação
            if transaction_type not in ['CR', 'DB']:
                line_error_messages.append(f'Linha {i+1}: Tipo de transação inválido.')
                continue
            
            # Validação específica por tipo de linha
            if line_type == 'transfer':
                # Transferência: deve ter destination_account, não deve ter category
                if not destination_account_id:
                    line_error_messages.append(f'Linha {i+1}: Conta de destino é obrigatória para transferências.')
                    continue
                try:
                    destination_account = Account.objects.get(id=destination_account_id)
                    main_account = cleaned_data.get('account')
                    if main_account and destination_account == main_account:
                        line_error_messages.append(f'Linha {i+1}: A conta de destino deve ser diferente da conta principal.')
                        continue
                except Account.DoesNotExist:
                    line_error_messages.append(f'Linha {i+1}: Conta de destino inválida.')
                    continue
                if category_id:
                    line_error_messages.append(f'Linha {i+1}: Transferências não devem ter categoria.')
                    continue
                category = None
            else:
                # Normal: deve ter category, não deve ter destination_account
                if not category_id:
                    line_error_messages.append(f'Linha {i+1}: Categoria é obrigatória para transações normais.')
                    continue
                try:
                    category = Category.objects.get(id=category_id)
                except Category.DoesNotExist:
                    line_error_messages.append(f'Linha {i+1}: Categoria inválida.')
                    continue
                if destination_account_id:
                    line_error_messages.append(f'Linha {i+1}: Transações normais não devem ter conta de destino.')
                    continue
                destination_account = None
            
            lines.append({
                'value': value,
                'transaction_type': transaction_type,
                'line_type': line_type,
                'category': category,
                'destination_account': destination_account,
                'description': description,
            })
        
        if line_error_messages:
            # Adiciona erros como erros não-campo (None) para que sejam exibidos no template
            for error_msg in line_error_messages:
                self.add_error(None, error_msg)
        
        cleaned_data['lines'] = lines
        return cleaned_data

