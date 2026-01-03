from django.shortcuts import render, get_object_or_404
from .models import Account, Transaction


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
