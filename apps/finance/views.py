from django import forms
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from decimal import Decimal
from .models import Account, Transaction, CreditCard, Beneficiary, Category
from .forms import AccountForm, TransactionForm, TransferTransactionForm, CompositeTransactionForm


def finance_home(request):
    """
    Página inicial da aplicação finance com visão geral.
    """
    accounts = Account.objects.filter(is_closed=False).order_by('-is_favorite', 'name')
    total_accounts = accounts.count()
    total_transactions = Transaction.objects.count()
    
    context = {
        'accounts': accounts,
        'total_accounts': total_accounts,
        'total_transactions': total_transactions,
    }
    
    return render(request, 'finance/finance_home.html', context)


def accounts_list(request):
    """
    Lista todas as contas.
    """
    accounts = Account.objects.all().order_by('-is_favorite', 'name')
    
    context = {
        'accounts': accounts,
    }
    
    return render(request, 'finance/accounts_list.html', context)


def account_create(request):
    """
    Cria uma nova conta.
    """
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta criada com sucesso!')
            return redirect('finance:accounts_list')
    else:
        form = AccountForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'finance/account_form.html', context)


def account_update(request, account_id):
    """
    Atualiza uma conta existente.
    """
    account = get_object_or_404(Account, id=account_id)
    
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta atualizada com sucesso!')
            return redirect('finance:accounts_list')
    else:
        form = AccountForm(instance=account)
    
    context = {
        'form': form,
        'account': account,
    }
    
    return render(request, 'finance/account_form.html', context)


def account_delete(request, account_id):
    """
    Deleta uma conta.
    """
    account = get_object_or_404(Account, id=account_id)
    
    if request.method == 'POST':
        account.delete()
        messages.success(request, 'Conta deletada com sucesso!')
        return redirect('finance:accounts_list')
    
    context = {
        'account': account,
    }
    
    return render(request, 'finance/account_delete.html', context)


def credit_cards_list(request):
    """
    Lista todos os cartões de crédito.
    """
    credit_cards = CreditCard.objects.filter(is_active=True).order_by('account', 'cardholder')
    
    context = {
        'credit_cards': credit_cards,
    }
    
    return render(request, 'finance/credit_cards_list.html', context)


def beneficiaries_list(request):
    """
    Lista todos os beneficiários.
    """
    beneficiaries = Beneficiary.objects.all().order_by('full_name')
    
    context = {
        'beneficiaries': beneficiaries,
    }
    
    return render(request, 'finance/beneficiaries_list.html', context)


def categories_list(request):
    """
    Lista todas as categorias.
    """
    categories = Category.objects.all().order_by('category', 'subcategory')
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'finance/categories_list.html', context)


def transactions_list(request):
    """
    Lista todas as transações.
    """
    transactions = Transaction.objects.all().order_by('-buy_date', '-created_at')
    
    context = {
        'transactions': transactions,
    }
    
    return render(request, 'finance/transactions_list.html', context)


def transaction_type_select(request):
    """
    Wizard inicial para seleção do tipo de transação.
    """
    return render(request, 'finance/transaction_type_select.html')


def transaction_create(request):
    """
    Cria uma nova transação simples.
    """
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            # Define operation_type como 'simple' para transações simples
            transaction = form.save(commit=False)
            transaction.operation_type = 'simple'
            transaction.save()
            messages.success(request, 'Transação criada com sucesso!')
            return redirect('finance:transactions_list')
    else:
        form = TransactionForm()
        # Define operation_type como 'simple' no formulário inicial
        form.fields['operation_type'].initial = 'simple'
        # Esconder o campo operation_type do formulário
        form.fields['operation_type'].widget = forms.HiddenInput()
    
    context = {
        'form': form,
    }
    
    return render(request, 'finance/transaction_form.html', context)


def transfer_create(request):
    """
    Cria uma transferência entre contas, gerando automaticamente o par de transações.
    """
    if request.method == 'POST':
        form = TransferTransactionForm(request.POST)
        if form.is_valid():
            source_account = form.cleaned_data['source_account']
            destination_account = form.cleaned_data['destination_account']
            value = form.cleaned_data['value']
            description = form.cleaned_data.get('description', '')
            buy_date = form.cleaned_data['buy_date']
            pay_date = form.cleaned_data.get('pay_date')
            
            # Determina status baseado em pay_date
            status = 'pago' if pay_date else 'pendente'
            
            # Cria a transação de débito (origem)
            debit_transaction = Transaction.objects.create(
                account=source_account,
                destination_account=destination_account,
                transaction_type='DB',
                operation_type='transfer',
                value=value,
                description=description or f'Transferência para {destination_account.name}',
                buy_date=buy_date,
                pay_date=pay_date,
                status=status
            )
            
            # Cria a transação de crédito (destino)
            credit_transaction = Transaction.objects.create(
                account=destination_account,
                destination_account=source_account,
                transaction_type='CR',
                operation_type='transfer',
                value=value,
                description=description or f'Transferência de {source_account.name}',
                buy_date=buy_date,
                pay_date=pay_date,
                status=status,
                parent_transaction=debit_transaction,
                parent_type='transfer_pair'
            )
            
            messages.success(
                request, 
                f'Transferência de R$ {value:.2f} de {source_account.name} para {destination_account.name} criada com sucesso!'
            )
            return redirect('finance:transactions_list')
    else:
        form = TransferTransactionForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'finance/transfer_form.html', context)


def transfer_update(request, transaction_id):
    """
    Edita uma transferência entre contas, atualizando ambas as transações do par.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    # Identifica qual transação foi clicada e busca o par completo
    if transaction.operation_type == 'transfer' and transaction.parent_transaction is None:
        # É a transação de débito (origem)
        debit_transaction = transaction
        credit_transaction = transaction.child_transactions.filter(parent_type='transfer_pair').first()
    elif transaction.parent_type == 'transfer_pair':
        # É a transação de crédito (destino)
        credit_transaction = transaction
        debit_transaction = transaction.parent_transaction
    else:
        messages.error(request, 'Transação não é uma transferência válida.')
        return redirect('finance:transactions_list')
    
    if request.method == 'POST':
        form = TransferTransactionForm(request.POST)
        if form.is_valid():
            source_account = form.cleaned_data['source_account']
            destination_account = form.cleaned_data['destination_account']
            value = form.cleaned_data['value']
            description = form.cleaned_data.get('description', '')
            buy_date = form.cleaned_data['buy_date']
            pay_date = form.cleaned_data.get('pay_date')
            
            # Determina status baseado em pay_date
            status = 'pago' if pay_date else 'pendente'
            
            # Atualiza a transação de débito (origem)
            debit_transaction.account = source_account
            debit_transaction.destination_account = destination_account
            debit_transaction.value = value
            debit_transaction.description = description or f'Transferência para {destination_account.name}'
            debit_transaction.buy_date = buy_date
            debit_transaction.pay_date = pay_date
            debit_transaction.status = status
            debit_transaction.save()
            
            # Atualiza a transação de crédito (destino)
            if credit_transaction:
                credit_transaction.account = destination_account
                credit_transaction.destination_account = source_account
                credit_transaction.value = value
                credit_transaction.description = description or f'Transferência de {source_account.name}'
                credit_transaction.buy_date = buy_date
                credit_transaction.pay_date = pay_date
                credit_transaction.status = status
                credit_transaction.save()
            
            messages.success(
                request, 
                f'Transferência de R$ {value:.2f} de {source_account.name} para {destination_account.name} atualizada com sucesso!'
            )
            return redirect('finance:transactions_list')
    else:
        # Preenche o formulário com os dados atuais da transferência
        # Remove o prefixo automático da descrição se existir
        description = debit_transaction.description or ''
        if description.startswith('Transferência para ') or description.startswith('Transferência de '):
            # Mantém apenas a descrição do usuário se houver algo além do prefixo
            parts = description.split(' - ', 1)
            if len(parts) > 1:
                description = parts[1]
            else:
                description = ''
        
        initial_data = {
            'source_account': debit_transaction.account,
            'destination_account': debit_transaction.destination_account,
            'value': debit_transaction.value,
            'description': description,
            'buy_date': debit_transaction.buy_date,
            'pay_date': debit_transaction.pay_date,
        }
        form = TransferTransactionForm(initial=initial_data)
    
    context = {
        'form': form,
        'transaction': debit_transaction,
        'is_edit': True,
    }
    
    return render(request, 'finance/transfer_form.html', context)


def transfer_delete(request, transaction_id):
    """
    Deleta uma transferência, removendo ambas as transações do par.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    # Identifica qual transação foi clicada e busca o par completo
    if transaction.operation_type == 'transfer' and transaction.parent_transaction is None:
        # É a transação de débito (origem) - deletar ela vai cascatear a de crédito
        debit_transaction = transaction
        credit_transaction = transaction.child_transactions.filter(parent_type='transfer_pair').first()
        source_account = transaction.account
        destination_account = transaction.destination_account
        value = transaction.value
    elif transaction.parent_type == 'transfer_pair':
        # É a transação de crédito (destino) - deletar a pai (débito)
        credit_transaction = transaction
        debit_transaction = transaction.parent_transaction
        source_account = debit_transaction.account
        destination_account = debit_transaction.destination_account
        value = debit_transaction.value
    else:
        messages.error(request, 'Transação não é uma transferência válida.')
        return redirect('finance:transactions_list')
    
    if request.method == 'POST':
        # Deleta a transação de débito (que vai cascatear a de crédito via CASCADE)
        debit_transaction.delete()
        messages.success(
            request, 
            f'Transferência de R$ {value:.2f} de {source_account.name} para {destination_account.name} deletada com sucesso!'
        )
        return redirect('finance:transactions_list')
    
    context = {
        'transaction': debit_transaction,
        'source_account': source_account,
        'destination_account': destination_account,
        'value': value,
    }
    
    return render(request, 'finance/transfer_delete.html', context)


def transaction_update(request, transaction_id):
    """
    Atualiza uma transação existente.
    Redireciona para transfer_update se for uma transferência.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    # Se for uma transferência, redireciona para o formulário específico
    if transaction.operation_type == 'transfer' or transaction.parent_type == 'transfer_pair':
        return redirect('finance:transfer_update', transaction_id=transaction_id)
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transação atualizada com sucesso!')
            return redirect('finance:transactions_list')
    else:
        form = TransactionForm(instance=transaction)
    
    context = {
        'form': form,
        'transaction': transaction,
    }
    
    return render(request, 'finance/transaction_form.html', context)


def transaction_delete(request, transaction_id):
    """
    Deleta uma transação.
    Redireciona para transfer_delete se for uma transferência.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    # Se for uma transferência, redireciona para o handler específico
    if transaction.operation_type == 'transfer' or transaction.parent_type == 'transfer_pair':
        return redirect('finance:transfer_delete', transaction_id=transaction_id)
    
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transação deletada com sucesso!')
        return redirect('finance:transactions_list')
    
    context = {
        'transaction': transaction,
    }
    
    return render(request, 'finance/transaction_delete.html', context)


def account_statement(request, account_id):
    """
    Exibe o extrato de uma conta.
    
    Filtros disponíveis via query parameter:
    - status: 'executado' ou 'pendente' (opcional)
    """
    account = get_object_or_404(Account, id=account_id)
    
    # Obtém o filtro de status da query string
    status_filter = request.GET.get('status', None)
    
    # Query base para transações da conta
    transactions = Transaction.objects.filter(account=account)
    
    # Aplica filtro de status se fornecido
    if status_filter == 'executado':
        # Transações pagas (com pay_date preenchido)
        transactions = transactions.filter(pay_date__isnull=False)
    elif status_filter == 'pendente':
        # Transações pendentes (sem pay_date)
        transactions = transactions.filter(pay_date__isnull=True)
    
    # Separa transações pagas e pendentes
    paid_transactions = transactions.filter(pay_date__isnull=False).order_by('pay_date')
    pending_transactions = transactions.filter(pay_date__isnull=True).order_by('due_date')
    
    # Se houver filtro, mostra apenas o tipo filtrado
    if status_filter == 'executado':
        pending_transactions = Transaction.objects.none()
    elif status_filter == 'pendente':
        paid_transactions = Transaction.objects.none()
    
    # Calcula o saldo acumulado para transações executadas
    current_balance = account.opening_balance
    paid_transactions_with_balance = []
    
    for transaction in paid_transactions:
        # Atualiza o saldo baseado no tipo de transação
        if transaction.transaction_type == 'CR':
            current_balance += transaction.value
        else:  # Débito
            current_balance -= transaction.value
        
        # Adiciona a transação com seu saldo acumulado
        paid_transactions_with_balance.append({
            'transaction': transaction,
            'balance': current_balance
        })
    
    # Calcula o saldo final (último saldo calculado)
    final_balance = current_balance
    
    context = {
        'account': account,
        'opening_balance': account.opening_balance,
        'paid_transactions_with_balance': paid_transactions_with_balance,
        'pending_transactions': pending_transactions,
        'final_balance': final_balance,
        'status_filter': status_filter,
    }
    
    return render(request, 'finance/account_statement.html', context)


def composite_transaction_create(request):
    """
    Cria uma transação composta com múltiplas linhas.
    A primeira transação será a "pai" e as demais serão filhas com parent_type='composite'.
    """
    if request.method == 'POST':
        form = CompositeTransactionForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            buy_date = form.cleaned_data['buy_date']
            pay_date = form.cleaned_data.get('pay_date')
            lines = form.cleaned_data['lines']
            
            # Determina status baseado em pay_date
            status = 'pago' if pay_date else 'pendente'
            
            # Cria a primeira transação como "pai"
            parent_transaction = None
            transaction_count = 0
            
            for i, line in enumerate(lines):
                # Determina operation_type baseado no tipo de linha
                if line['line_type'] == 'transfer':
                    operation_type = 'transfer'
                    # Para transferências, sempre cria débito na conta principal
                    transaction_type = 'DB'
                else:
                    operation_type = 'simple'
                    transaction_type = line['transaction_type']
                
                # Cria a transação principal (débito ou crédito na conta compartilhada)
                transaction = Transaction.objects.create(
                    account=account,
                    destination_account=line['destination_account'],
                    transaction_type=transaction_type,
                    operation_type=operation_type,
                    value=Decimal(str(line['value'])),
                    category=line['category'],
                    description=line['description'],
                    buy_date=buy_date,
                    pay_date=pay_date,
                    status=status
                )
                
                # Primeira transação é a pai, demais são filhas
                if transaction_count == 0:
                    parent_transaction = transaction
                else:
                    transaction.parent_transaction = parent_transaction
                    transaction.parent_type = 'composite'
                    transaction.save()
                
                transaction_count += 1
                
                # Se for transferência, cria também a transação de crédito na conta de destino
                if line['line_type'] == 'transfer' and line['destination_account']:
                    destination_account = line['destination_account']
                    credit_description = line['description'] or f'Transferência de {account.name}'
                    
                    credit_transaction = Transaction.objects.create(
                        account=destination_account,
                        destination_account=account,
                        transaction_type='CR',
                        operation_type='transfer',
                        value=Decimal(str(line['value'])),
                        category=None,
                        description=credit_description,
                        buy_date=buy_date,
                        pay_date=pay_date,
                        status=status,
                        parent_transaction=parent_transaction,
                        parent_type='composite'
                    )
                    transaction_count += 1
            
            messages.success(
                request,
                f'Transação composta com {transaction_count} transação(ões) criada(s) com sucesso!'
            )
            return redirect('finance:transactions_list')
    else:
        form = CompositeTransactionForm()
    
    # Prepara dados para o template (categorias e contas para os selects)
    categories = Category.objects.all().order_by('category', 'subcategory')
    accounts = Account.objects.filter(is_closed=False).order_by('name')
    
    context = {
        'form': form,
        'categories': categories,
        'accounts': accounts,
    }
    
    return render(request, 'finance/composite_transaction_form.html', context)
