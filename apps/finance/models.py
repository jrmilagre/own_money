from django.db import models

# Create your models here.
class BaseModel(models.Model):
    # Allow nulls to avoid default prompts when adding the base fields
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True
        
class Account(BaseModel):
    ACCOUNT_TYPE_CHOICES = [
        ('CASH', 'Dinheiro'),
        ('BANK', 'Banco'),
        ('INVEST', 'Investimento'),
    ]

    name = models.CharField('Nome da conta', max_length=100)
    institution = models.CharField('Instituição financeira', max_length=100, blank=True)
    number = models.CharField('Número da conta', max_length=50, blank=True)
    account_type = models.CharField(
        'Tipo',
        max_length=10,
        choices=ACCOUNT_TYPE_CHOICES,
        default='BANK',
    )
    currency = models.CharField('Unidade monetária', max_length=30, default='Real brasileiro')
    opening_balance = models.DecimalField('Saldo de abertura', max_digits=12, decimal_places=2, default=0)
    minimum_balance = models.DecimalField('Saldo mínimo', max_digits=12, decimal_places=2, default=0)
    group = models.CharField('Grupo de contas', max_length=100, blank=True)
    abbreviation = models.CharField('Abreviação', max_length=20, blank=True)
    comment = models.TextField('Comentário', blank=True)
    is_favorite = models.BooleanField('Conta favorita', default=False)
    is_closed = models.BooleanField('A conta está encerrada', default=False)

    class Meta:
        verbose_name = 'Conta'
        verbose_name_plural = 'Contas'

    def __str__(self):
        return self.name


class CreditCard(BaseModel):
    CARD_TYPE_CHOICES = [
        ('credit', 'Crédito'),
        ('debit', 'Débito'),
        ('VA', 'Vale Alimentação'),
        ('VR', 'Vale Refeição'),
        ('both', 'Crédito e Débito'),
    ]
    
    BRAND_CHOICES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('elo', 'Elo'),
        ('hipercard', 'Hipercard'),
        ('other', 'Outro'),
    ]

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='credit_cards',
        verbose_name='Conta'
    )
    card_number = models.CharField(
        'Número do cartão',
        max_length=19,
        help_text='Formato: XXXX XXXX XXXX XXXX'
    )
    cardholder = models.CharField('Titular', max_length=200)
    expiration_date = models.DateField('Data de vencimento')
    cvv = models.CharField('CVV', max_length=4)
    brand = models.CharField(
        'Bandeira',
        max_length=20,
        choices=BRAND_CHOICES,
        default='other'
    )
    card_type = models.CharField(
        'Tipo',
        max_length=10,
        choices=CARD_TYPE_CHOICES,
        default='credit'
    )
    is_active = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Cartão de Crédito'
        verbose_name_plural = 'Cartões de Crédito'
        ordering = ('account', 'cardholder', 'card_number')

    def __str__(self):
        # Mostra apenas os últimos 4 dígitos por segurança
        last_four = self.card_number.replace(' ', '')[-4:] if len(self.card_number.replace(' ', '')) >= 4 else '****'
        return f"{self.get_brand_display()} - **** **** **** {last_four} ({self.account.name})"


class Beneficiary(BaseModel):
    full_name = models.CharField('Nome completo', max_length=200)

    class Meta:
        verbose_name = 'Beneficiário'
        verbose_name_plural = 'Beneficiários'

    def __str__(self):
        return self.full_name


class Category(BaseModel):
    TRANSACTION_TYPE_CHOICES = [
        ('CR', 'Crédito'),
        ('DB', 'Débito'),
    ]

    category = models.CharField('Categoria', max_length=200)
    subcategory = models.CharField('Subcategoria', max_length=200)
    default_transaction_type = models.CharField(
        'Tipo de transação padrão',
        max_length=2,
        choices=TRANSACTION_TYPE_CHOICES,
        default='DB',
    )

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ('category', 'subcategory')

    def __str__(self):
        return f"{self.category} - {self.subcategory}"


class Transaction(BaseModel):
    # Campos de estrutura hierárquica
    PARENT_TYPE_CHOICES = [
        ('split', 'Rateio'),
        ('recurring', 'Recorrência'),
        ('transfer_pair', 'Par de transferência'),
        ('composite', 'Transação composta'),
    ]
    
    parent_transaction = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_transactions',
        verbose_name='Transação pai'
    )
    parent_type = models.CharField(
        'Tipo de relacionamento com o pai',
        max_length=20,
        choices=PARENT_TYPE_CHOICES,
        blank=True,
        null=True
    )
    is_split = models.BooleanField('Faz parte de um rateio', default=False)
    is_split_parent = models.BooleanField('É a transação principal de um rateio', default=False)
    split_sequence = models.IntegerField('Ordem do item no rateio', null=True, blank=True)
    
    # Campos principais
    OPERATION_TYPE_CHOICES = [
        ('simple', 'Simples'),
        ('split', 'Rateio'),
        ('transfer', 'Transferência'),
    ]
    
    TRANSACTION_TYPE_CHOICES = [
        ('CR', 'Crédito'),
        ('DB', 'Débito'),
    ]
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
    ]
    
    operation_type = models.CharField(
        'Tipo de operação',
        max_length=10,
        choices=OPERATION_TYPE_CHOICES,
        default='simple'
    )
    transaction_type = models.CharField(
        'Tipo da transação',
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES,
        default='debito'
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Conta'
    )
    credit_card = models.ForeignKey(
        'CreditCard',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Cartão de Crédito'
    )    
    destination_account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='incoming_transfers',
        null=True,
        blank=True,
        verbose_name='Conta de destino'
    )
    beneficiary = models.ForeignKey(
        Beneficiary,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Beneficiário'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Categoria'
    )
    description = models.CharField('Descrição', max_length=500, blank=True)
    value = models.DecimalField(
        'Valor',
        max_digits=15,
        decimal_places=2,
        help_text='Valor sempre positivo'
    )
    buy_date = models.DateField('Data da operação')
    pay_date = models.DateField('Data do pagamento efetivo', null=True, blank=True)
    due_date = models.DateField('Data de vencimento', null=True, blank=True)
    status = models.CharField(
        'Status',
        max_length=10,
        choices=STATUS_CHOICES,
        default='pendente'
    )
    
    # Campos de recorrência
    RECURRENCE_TYPE_CHOICES = [
        ('daily', 'Diária'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensal'),
        ('yearly', 'Anual'),
    ]
    
    RECURRENCE_END_TYPE_CHOICES = [
        ('never', 'Nunca'),
        ('on_date', 'Em uma data'),
        ('after_count', 'Após quantidade'),
    ]
    
    is_recurring = models.BooleanField('É recorrente', default=False)
    recurrence_type = models.CharField(
        'Tipo de recorrência',
        max_length=10,
        choices=RECURRENCE_TYPE_CHOICES,
        blank=True,
        null=True
    )
    recurrence_interval = models.IntegerField(
        'Intervalo entre recorrências',
        default=1,
        help_text='Ex: a cada 2 semanas'
    )
    recurrence_weekdays = models.CharField(
        'Dias da semana para recorrência semanal',
        max_length=20,
        blank=True,
        help_text='Ex: 1,3,5 para segunda, quarta, sexta'
    )
    recurrence_monthly_day = models.IntegerField(
        'Dia específico do mês (DEPRECATED)',
        null=True,
        blank=True,
        help_text='DEPRECATED: usar recurrence_start_date'
    )
    recurrence_start_date = models.DateField(
        'Data da primeira parcela recorrente',
        null=True,
        blank=True
    )
    recurrence_end_type = models.CharField(
        'Como a recorrência termina',
        max_length=15,
        choices=RECURRENCE_END_TYPE_CHOICES,
        default='never',
        blank=True
    )
    recurrence_end_date = models.DateField(
        'Data em que a recorrência deve parar',
        null=True,
        blank=True
    )
    recurrence_end_count = models.IntegerField(
        'Quantas vezes a transação deve se repetir',
        null=True,
        blank=True
    )
    recurrence_sequence = models.IntegerField(
        'Número da sequência na recorrência',
        null=True,
        blank=True,
        help_text='1, 2, 3... para transações filhas geradas'
    )
    
    class Meta:
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'
        ordering = ('-buy_date', '-created_at')
    
    def __str__(self):
        desc = self.description or f"Transação #{self.id}"
        return f"{desc} - {self.value} ({self.get_transaction_type_display()})"
    
    def is_composite_parent(self):
        """Verifica se esta transação é pai de uma transação composta."""
        return self.child_transactions.filter(parent_type='composite').exists()
    
    def save(self, *args, **kwargs):
        # Define status automaticamente baseado em pay_date
        if self.pay_date:
            self.status = 'pago'
        else:
            self.status = 'pendente'
        super().save(*args, **kwargs)        
