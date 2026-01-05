from django.db import models
from dateutil.relativedelta import relativedelta
from datetime import timedelta
import re

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
        ('CARD', 'Cartão'),
    ]

    BRAND_CHOICES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('elo', 'Elo'),
        ('hipercard', 'Hipercard'),
        ('other', 'Outro'),
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
    
    # Campos de cartão de crédito
    cardholder = models.CharField('Titular', max_length=200, blank=True)
    card_number = models.CharField(
        'Número do cartão',
        max_length=19,
        blank=True,
        help_text='Formato: XXXX XXXX XXXX XXXX'
    )
    expiration_date = models.DateField('Data de vencimento', null=True, blank=True)
    cvv = models.CharField('CVV', max_length=4, blank=True)
    brand = models.CharField(
        'Bandeira',
        max_length=20,
        choices=BRAND_CHOICES,
        default='other',
        blank=True
    )

    class Meta:
        verbose_name = 'Conta'
        verbose_name_plural = 'Contas'

    def __str__(self):
        return self.name


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
        ('registrado', 'Registrado'),
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
    recurrence_interrupted = models.BooleanField(
        'Recorrência interrompida',
        default=False,
        help_text='Se marcado, a recorrência não gerará mais parcelas automaticamente'
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
    
    def has_next_recurring_installment(self):
        """Verifica se existe próxima parcela recorrente gerada."""
        return self.child_transactions.filter(parent_type='recurring').exists()
    
    def get_next_pending_installment(self):
        """Retorna a próxima parcela pendente (sem pay_date), se existir."""
        return self.child_transactions.filter(
            parent_type='recurring',
            pay_date__isnull=True
        ).first()
    
    def get_pending_children(self):
        """Retorna todas as parcelas filhas pendentes (sem pay_date)."""
        return self.child_transactions.filter(
            parent_type='recurring',
            pay_date__isnull=True
        )
    
    def get_registered_children(self):
        """Retorna todas as parcelas filhas registradas (com pay_date)."""
        return self.child_transactions.filter(
            parent_type='recurring',
            pay_date__isnull=False
        )
    
    def get_all_pending_installments(self):
        """
        Retorna todas as parcelas pendentes da recorrência (não apenas filhas diretas).
        Busca recursivamente todas as parcelas da recorrência que são pendentes.
        """
        parent = self.get_recurring_parent()
        
        # Lista para armazenar todas as parcelas pendentes
        pending_list = []
        
        # Se a raiz é pendente, adiciona
        if not parent.pay_date:
            pending_list.append(parent)
        
        # Busca recursivamente todas as filhas pendentes
        def get_all_children(transaction):
            children = transaction.child_transactions.filter(
                parent_type='recurring'
            )
            for child in children:
                if not child.pay_date:
                    pending_list.append(child)
                get_all_children(child)
        
        get_all_children(parent)
        
        # Retorna um queryset ordenado por recurrence_sequence
        if pending_list:
            ids = [t.id for t in pending_list]
            return Transaction.objects.filter(id__in=ids).order_by('recurrence_sequence')
        return Transaction.objects.none()
    
    def is_next_pending_installment(self):
        """
        Verifica se esta transação é a próxima parcela pendente da recorrência.
        Retorna True se:
        - É pendente (sem pay_date) e é a primeira pendente na sequência, OU
        - É a raiz e não tem parcelas pendentes, OU
        - É a última registrada e não há parcelas pendentes (será a próxima a gerar)
        """
        if not self.is_recurring:
            return False
        
        parent = self.get_recurring_parent()
        
        # Busca todas as parcelas pendentes da recorrência (não apenas filhas diretas)
        all_pending = parent.get_all_pending_installments()
        has_pending = all_pending.exists()
        
        # Se há parcelas pendentes, prioriza elas
        if has_pending:
            # Se a transação é registrada (tem pay_date), não é a próxima pendente
            if self.pay_date:
                return False
            
            # Se a transação é pendente, verifica se é a primeira pendente na sequência
            first_pending = all_pending.first()
            return self.id == first_pending.id
        
        # Se não há parcelas pendentes
        # Se a transação é pendente e é a raiz, é a próxima
        if not self.pay_date:
            if self.parent_type != 'recurring':
                return True
            return False
        
        # Se a transação é registrada e não há parcelas pendentes
        # Verifica se é a última registrada
        if self.pay_date:
            # Busca todas as parcelas registradas da recorrência
            registered_list = []
            if parent.pay_date:
                registered_list.append(parent)
            
            def get_all_registered_children(transaction):
                children = transaction.child_transactions.filter(
                    parent_type='recurring'
                )
                for child in children:
                    if child.pay_date:
                        registered_list.append(child)
                    get_all_registered_children(child)
            
            get_all_registered_children(parent)
            
            if registered_list:
                # Ordena por recurrence_sequence e pega a última
                registered_list.sort(key=lambda t: t.get_current_installment(), reverse=True)
                last_registered = registered_list[0]
                return self.id == last_registered.id
            # Se não há parcelas registradas, a raiz é a última
            if self.parent_type != 'recurring':
                return True
        
        return False
    
    def get_subsequent_installments(self):
        """Retorna todas as parcelas subsequentes (com sequence maior que a atual)."""
        current_sequence = self.get_current_installment()
        parent = self.get_recurring_parent()
        
        # Busca todas as parcelas filhas do parent com sequence maior
        return parent.child_transactions.filter(
            parent_type='recurring',
            recurrence_sequence__gt=current_sequence
        ).order_by('recurrence_sequence')
    
    def reorganize_sequences(self):
        """Reorganiza as sequências das parcelas filhas para manter continuidade."""
        if not self.is_recurring:
            return
        
        parent = self.get_recurring_parent()
        children = parent.child_transactions.filter(
            parent_type='recurring'
        ).order_by('recurrence_sequence', 'id')
        
        # A primeira parcela é o pai (sequence 1 ou None), então as filhas começam em 2
        sequence = 2
        for child in children:
            if child.recurrence_sequence != sequence:
                child.recurrence_sequence = sequence
                # Atualiza descrição também
                base_description = parent.get_base_description()
                total = parent.get_total_installments()
                if total:
                    child.description = f"{base_description} - {sequence:02d}/{total:02d}"
                else:
                    child.description = f"{base_description} - {sequence}"
                child.save(update_fields=['recurrence_sequence', 'description'])
            sequence += 1
    
    def get_recurring_parent(self):
        """Retorna a transação pai da recorrência (primeira parcela)."""
        # Se não tem parent_transaction ou parent_type não é 'recurring', é a própria raiz
        if not self.parent_transaction or self.parent_type != 'recurring':
            return self
        # Segue a cadeia de parent_transaction
        return self.parent_transaction.get_recurring_parent()
    
    def promote_first_child_to_root(self):
        """
        Promove a primeira parcela filha a raiz da recorrência.
        Remove parent_transaction da primeira parcela e atualiza outras para referenciarem ela.
        Retorna a primeira parcela promovida ou None se não houver filhas.
        """
        if not self.is_recurring:
            return None
        
        # Busca todas as parcelas filhas
        children = self.child_transactions.filter(
            parent_type='recurring'
        ).order_by('recurrence_sequence', 'id')
        
        if not children.exists():
            return None
        
        # Identifica a primeira parcela filha (menor recurrence_sequence)
        first_child = children.first()
        
        # Remove parent_transaction e parent_type da primeira parcela
        first_child.parent_transaction = None
        first_child.parent_type = None
        first_child.save(update_fields=['parent_transaction', 'parent_type'])
        
        # Atualiza todas as outras parcelas filhas para referenciarem a primeira
        other_children = children.exclude(id=first_child.id)
        for child in other_children:
            child.parent_transaction = first_child
            child.parent_type = 'recurring'
            child.save(update_fields=['parent_transaction', 'parent_type'])
        
        return first_child
    
    def get_total_installments(self):
        """Retorna o total de parcelas se finita, ou None se infinita."""
        parent = self.get_recurring_parent()
        if parent.recurrence_end_type == 'after_count':
            return parent.recurrence_end_count
        return None
    
    def get_current_installment(self):
        """Retorna o número da parcela atual."""
        if self.recurrence_sequence:
            return self.recurrence_sequence
        # Se não tem sequence, é a primeira parcela (pai)
        return 1
    
    def can_generate_next(self):
        """Verifica se pode gerar próxima parcela."""
        if not self.is_recurring:
            return False
        
        parent = self.get_recurring_parent()
        
        # Se a recorrência está interrompida, não pode gerar
        if parent.recurrence_interrupted:
            return False
        
        # Recorrência infinita: sempre pode gerar (se não estiver interrompida)
        if parent.recurrence_end_type == 'never':
            return True
        
        # Recorrência finita: verifica se ainda há parcelas restantes
        if parent.recurrence_end_type == 'after_count':
            current = self.get_current_installment()
            total = parent.recurrence_end_count
            return current < total
        
        return False
    
    def get_next_due_date(self):
        """Calcula a próxima data de vencimento baseado no tipo de recorrência e interval."""
        if not self.is_recurring or not self.recurrence_type:
            return None
        
        # Usa due_date atual ou pay_date como base
        base_date = self.due_date or self.pay_date or self.buy_date
        if not base_date:
            return None
        
        parent = self.get_recurring_parent()
        interval = parent.recurrence_interval or 1
        
        if parent.recurrence_type == 'weekly':
            return base_date + timedelta(weeks=interval)
        elif parent.recurrence_type == 'monthly':
            return base_date + relativedelta(months=interval)
        elif parent.recurrence_type == 'yearly':
            return base_date + relativedelta(years=interval)
        elif parent.recurrence_type == 'daily':
            return base_date + timedelta(days=interval)
        
        return None
    
    def get_base_description(self):
        """Retorna a descrição base sem sufixo de parcela."""
        parent = self.get_recurring_parent()
        base_description = parent.description or f"Transação #{parent.id}"
        
        # Remove sufixo de parcela se já existir (formato: " - XX/YY" ou " - XX")
        if ' - ' in base_description:
            parts = base_description.rsplit(' - ', 1)
            if len(parts) == 2:
                last_part = parts[-1]
                # Verifica se é formato de parcela (XX/YY ou apenas número)
                if '/' in last_part:
                    # Formato XX/YY
                    try:
                        parts_num = last_part.split('/')
                        if len(parts_num) == 2 and parts_num[0].isdigit() and parts_num[1].isdigit():
                            base_description = parts[0]
                    except:
                        pass
                elif last_part.isdigit():
                    # Apenas número
                    base_description = parts[0]
        
        return base_description
    
    def get_description_with_installment(self):
        """Retorna a descrição com informação da parcela."""
        base_description = self.get_base_description()
        current = self.get_current_installment()
        total = self.get_total_installments()
        
        if total:
            return f"{base_description} - {current:02d}/{total:02d}"
        else:
            return f"{base_description} - {current}"
    
    def generate_next_installment(self):
        """Gera a próxima parcela da recorrência."""
        if not self.can_generate_next():
            return None
        
        parent = self.get_recurring_parent()
        next_due_date = self.get_next_due_date()
        
        if not next_due_date:
            return None
        
        current_sequence = self.get_current_installment()
        next_sequence = current_sequence + 1
        
        # Obtém descrição base do parent
        base_description = parent.get_base_description()
        total = self.get_total_installments()
        
        # Monta descrição com número da parcela
        if total:
            next_description = f"{base_description} - {next_sequence:02d}/{total:02d}"
        else:
            next_description = f"{base_description} - {next_sequence}"
        
        # Cria nova transação filha
        next_transaction = Transaction.objects.create(
            parent_transaction=self,
            parent_type='recurring',
            is_recurring=True,
            recurrence_type=parent.recurrence_type,
            recurrence_interval=parent.recurrence_interval,
            recurrence_start_date=parent.recurrence_start_date,
            recurrence_end_type=parent.recurrence_end_type,
            recurrence_end_count=parent.recurrence_end_count,
            recurrence_sequence=next_sequence,
            account=self.account,
            beneficiary=self.beneficiary,
            category=self.category,
            transaction_type=self.transaction_type,
            operation_type=self.operation_type,
            value=self.value,
            buy_date=self.buy_date,
            due_date=next_due_date,
            pay_date=None,
            status='pendente',
            description=next_description,
        )
        
        return next_transaction
    
    def save(self, *args, **kwargs):
        # Define status automaticamente baseado em pay_date
        old_pay_date = None
        if self.pk:
            try:
                old_instance = Transaction.objects.get(pk=self.pk)
                old_pay_date = old_instance.pay_date
            except Transaction.DoesNotExist:
                pass
        
        if self.pay_date:
            self.status = 'registrado'
        else:
            self.status = 'pendente'
        
        # Salva a transação primeiro
        super().save(*args, **kwargs)
        
        # Se pay_date está preenchido e é uma transação recorrente, verifica se precisa gerar próxima parcela
        if self.is_recurring and self.pay_date:
            # Verifica se já existe próxima parcela gerada
            existing_next = self.child_transactions.filter(
                parent_type='recurring'
            ).first()
            
            # Gera próxima parcela se:
            # 1. Não existe próxima parcela gerada
            # 2. Pode gerar próxima (não está interrompida, não excedeu limite, etc)
            # 3. pay_date foi preenchido (seja pela primeira vez ou alterado)
            if not existing_next and self.can_generate_next():
                self.generate_next_installment()
        
        # Atualiza descrição com número da parcela se necessário (apenas na primeira vez)
        # Evita atualizar se já foi atualizado ou se está sendo atualizado via update_fields
        if self.is_recurring and not kwargs.get('update_fields') and self.pk:
            new_description = self.get_description_with_installment()
            # Só atualiza se a descrição atual não tem o formato de parcela
            current_desc = self.description or ""
            # Verifica se já tem formato de parcela (contém " - " seguido de número)
            has_installment_pattern = re.search(r' - \d+(\/\d+)?$', current_desc)
            
            if not has_installment_pattern:
                # Atualiza usando update para evitar recursão
                Transaction.objects.filter(pk=self.pk).update(description=new_description)
                # Atualiza o objeto em memória
                self.description = new_description
