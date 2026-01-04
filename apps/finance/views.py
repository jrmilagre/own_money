from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Account, Transaction, CreditCard, Beneficiary, Category
from .forms import AccountForm, TransactionForm


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


def transaction_create(request):
    """
    Cria uma nova transação.
    """
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transação criada com sucesso!')
            return redirect('finance:transactions_list')
    else:
        form = TransactionForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'finance/transaction_form.html', context)


def transaction_update(request, transaction_id):
    """
    Atualiza uma transação existente.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
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
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
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
