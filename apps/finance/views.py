from django import forms
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from decimal import Decimal
import json
from .models import Account, Transaction, Beneficiary, Category
from .forms import AccountForm, TransactionForm, TransferTransactionForm, CompositeTransactionForm, RecurringTransactionForm, RecurringCompositeTransactionForm


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
    Cria uma nova transação simples ou recorrente.
    """
    if request.method == 'POST':
        # Usa RecurringTransactionForm para permitir recorrência
        form = RecurringTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.operation_type = 'simple'
            
            # Configura recorrência se marcada
            is_recurring = form.cleaned_data.get('is_recurring', False)
            if is_recurring:
                transaction.is_recurring = True
                transaction.recurrence_type = form.cleaned_data.get('recurrence_type')
                transaction.recurrence_interval = form.cleaned_data.get('recurrence_interval', 1)
                transaction.recurrence_start_date = form.cleaned_data.get('recurrence_start_date')
                transaction.recurrence_end_type = form.cleaned_data.get('recurrence_end_type', 'never')
                transaction.recurrence_end_count = form.cleaned_data.get('recurrence_end_count')
                # Define due_date como recurrence_start_date se não foi preenchido
                if not transaction.due_date and transaction.recurrence_start_date:
                    transaction.due_date = transaction.recurrence_start_date
                # Define recurrence_sequence como 1 para a primeira parcela
                transaction.recurrence_sequence = 1
                
                # Atualiza descrição com número da parcela
                base_description = transaction.description or f"Transação #{transaction.id}"
                if transaction.recurrence_end_type == 'after_count' and transaction.recurrence_end_count:
                    transaction.description = f"{base_description} - 01/{transaction.recurrence_end_count:02d}"
                else:
                    transaction.description = f"{base_description} - 1"
            else:
                transaction.is_recurring = False
            
            transaction.save()
            messages.success(request, 'Transação criada com sucesso!')
            return redirect('finance:transactions_list')
    else:
        form = RecurringTransactionForm()
    
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
            status = 'registrado' if pay_date else 'pendente'
            
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
            status = 'registrado' if pay_date else 'pendente'
            
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
    Redireciona para composite_transaction_update se for uma transação composta.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    # Se for uma transferência, redireciona para o formulário específico
    if transaction.operation_type == 'transfer' or transaction.parent_type == 'transfer_pair':
        return redirect('finance:transfer_update', transaction_id=transaction_id)
    
    # Se for uma transação composta, redireciona para o formulário específico
    # Verifica se é composta recorrente (raiz ou filha) ou se é pai de compostas ou filha de composta
    # is_composite_recurring() verifica se é recorrente E tem filhas compostas
    # is_composite_parent() verifica se tem filhas com parent_type='composite'
    # parent_type == 'composite' verifica se é filha de uma composta
    if transaction.parent_type == 'composite':
        # É uma linha filha, redireciona para o pai
        return redirect('finance:composite_transaction_update', transaction_id=transaction.parent_transaction.id)
    elif transaction.is_composite_recurring() or transaction.is_composite_parent():
        # É a composta pai (pode ser recorrente)
        return redirect('finance:composite_transaction_update', transaction_id=transaction_id)
    
    # Para transações recorrentes, usa RecurringTransactionForm
    # Mas não permite editar campos de recorrência se já houver parcelas geradas
    is_recurring = transaction.is_recurring
    has_children = transaction.child_transactions.filter(parent_type='recurring').exists()
    
    if request.method == 'POST':
        if is_recurring:
            form = RecurringTransactionForm(request.POST, instance=transaction)
        else:
            form = TransactionForm(request.POST, instance=transaction)
        
        if form.is_valid():
            transaction = form.save(commit=False)
            
            # Se for recorrente, atualiza campos de recorrência
            if is_recurring and isinstance(form, RecurringTransactionForm):
                parent = transaction.get_recurring_parent()
                
                # Não permite alterar recorrência se já houver parcelas geradas
                if has_children:
                    # Mantém valores originais de recorrência
                    transaction.recurrence_type = parent.recurrence_type
                    transaction.recurrence_interval = parent.recurrence_interval
                    transaction.recurrence_start_date = parent.recurrence_start_date
                    transaction.recurrence_end_type = parent.recurrence_end_type
                    transaction.recurrence_end_count = parent.recurrence_end_count
                else:
                    # Permite alterar se ainda não há parcelas geradas
                    transaction.is_recurring = form.cleaned_data.get('is_recurring', False)
                    if transaction.is_recurring:
                        transaction.recurrence_type = form.cleaned_data.get('recurrence_type')
                        transaction.recurrence_interval = form.cleaned_data.get('recurrence_interval', 1)
                        transaction.recurrence_start_date = form.cleaned_data.get('recurrence_start_date')
                        transaction.recurrence_end_type = form.cleaned_data.get('recurrence_end_type', 'never')
                        transaction.recurrence_end_count = form.cleaned_data.get('recurrence_end_count')
            
            transaction.save()
            messages.success(request, 'Transação atualizada com sucesso!')
            return redirect('finance:transactions_list')
    else:
        if is_recurring:
            form = RecurringTransactionForm(instance=transaction)
        else:
            form = TransactionForm(instance=transaction)
    
    context = {
        'form': form,
        'transaction': transaction,
        'is_recurring': is_recurring,
        'has_recurring_children': has_children,
    }
    
    return render(request, 'finance/transaction_form.html', context)


def transaction_delete(request, transaction_id):
    """
    Deleta uma transação.
    Redireciona para transfer_delete se for uma transferência.
    Redireciona para composite_transaction_delete se for uma transação composta.
    Para transações recorrentes, preserva as registradas e deleta apenas as pendentes.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    # Se for uma transferência, redireciona para o handler específico
    if transaction.operation_type == 'transfer' or transaction.parent_type == 'transfer_pair':
        return redirect('finance:transfer_delete', transaction_id=transaction_id)
    
    # Se for uma transação composta, redireciona para o handler específico
    # Verifica se é composta recorrente (raiz ou filha) ou se é pai de compostas ou filha de composta
    # is_composite_recurring() verifica se é recorrente E tem filhas compostas
    # is_composite_parent() verifica se tem filhas com parent_type='composite'
    # parent_type == 'composite' verifica se é filha de uma composta
    if transaction.parent_type == 'composite':
        # É uma linha filha, redireciona para o pai
        return redirect('finance:composite_transaction_delete', transaction_id=transaction.parent_transaction.id)
    elif transaction.is_composite_recurring() or transaction.is_composite_parent():
        # É a composta pai (pode ser recorrente)
        return redirect('finance:composite_transaction_delete', transaction_id=transaction_id)
    
    # Lógica especial para transações recorrentes
    if transaction.is_recurring:
        if transaction.parent_type == 'recurring':
            # É uma parcela filha recorrente
            if transaction.status == 'registrado' or transaction.pay_date:
                messages.error(request, 'Não é possível deletar uma parcela recorrente já registrada. Use a função "Desfazer Pagamento" se necessário.')
                return redirect('finance:transactions_list')
            else:
                # Parcela pendente - pode deletar
                if request.method == 'POST':
                    # Obtém a transação pai para reorganizar sequências depois
                    parent = transaction.get_recurring_parent()
                    
                    # Identifica todas as parcelas subsequentes (com sequence maior)
                    subsequent_installments = transaction.get_subsequent_installments()
                    
                    # Deleta apenas as parcelas subsequentes pendentes
                    pending_subsequent = subsequent_installments.filter(pay_date__isnull=True)
                    pending_count = pending_subsequent.count()
                    registered_subsequent = subsequent_installments.filter(pay_date__isnull=False)
                    registered_count = registered_subsequent.count()
                    
                    # Deleta a parcela atual e as subsequentes pendentes
                    transaction.delete()
                    pending_subsequent.delete()
                    
                    # Reorganiza as sequências das parcelas restantes
                    parent.reorganize_sequences()
                    
                    if pending_count > 0:
                        messages.success(request, f'Parcela recorrente e {pending_count} parcela(s) subsequente(s) pendente(s) deletada(s) com sucesso.')
                        if registered_count > 0:
                            messages.info(request, f'{registered_count} parcela(s) subsequente(s) registrada(s) foram preservada(s).')
                    else:
                        messages.success(request, 'Parcela recorrente pendente deletada com sucesso.')
                    
                    return redirect('finance:transactions_list')
                else:
                    # GET - mostra confirmação com detalhes sobre parcelas subsequentes
                    subsequent_installments = transaction.get_subsequent_installments()
                    pending_subsequent_count = subsequent_installments.filter(pay_date__isnull=True).count()
                    registered_subsequent_count = subsequent_installments.filter(pay_date__isnull=False).count()
                    
                    context = {
                        'transaction': transaction,
                        'pending_subsequent_count': pending_subsequent_count,
                        'registered_subsequent_count': registered_subsequent_count,
                        'is_recurring_child_delete': True,
                    }
                    return render(request, 'finance/transaction_delete.html', context)
        else:
            # É a transação pai recorrente
            if request.method == 'POST':
                # Verifica se há parcelas filhas (registradas ou pendentes)
                all_children = transaction.child_transactions.filter(parent_type='recurring')
                total_children_count = all_children.count()
                
                if total_children_count > 0:
                    # Conta parcelas antes da promoção
                    pending_before = transaction.get_pending_children().count()
                    registered_before = transaction.get_registered_children().count()
                    
                    # Promove a primeira parcela filha a raiz antes de deletar
                    first_child = transaction.promote_first_child_to_root()
                    
                    if first_child:
                        # Verifica quantas parcelas registradas e pendentes restam (agora referenciam first_child)
                        registered_children = first_child.get_registered_children()
                        registered_count = registered_children.count()
                        pending_children = first_child.get_pending_children()
                        pending_count = pending_children.count()
                        
                        # Deleta apenas a transação pai - preserva todas as parcelas filhas (registradas e pendentes)
                        transaction.delete()
                        
                        if registered_count > 0 and pending_count > 0:
                            messages.success(request, f'Transação pai deletada. A primeira parcela foi promovida a raiz. {registered_count} parcela(s) registrada(s) e {pending_count} parcela(s) pendente(s) foram preservadas e tornadas independentes.')
                        elif registered_count > 0:
                            messages.success(request, f'Transação pai deletada. A primeira parcela foi promovida a raiz. {registered_count} parcela(s) registrada(s) foram preservadas e tornadas independentes.')
                        elif pending_count > 0:
                            messages.success(request, f'Transação pai deletada. A primeira parcela foi promovida a raiz. {pending_count} parcela(s) pendente(s) foram preservadas e tornadas independentes.')
                        else:
                            messages.success(request, 'Transação pai deletada. A primeira parcela foi promovida a raiz.')
                    else:
                        # Fallback: se não conseguiu promover, deleta normalmente
                        pending_children = transaction.get_pending_children()
                        pending_count = pending_children.count()
                        pending_children.delete()
                        transaction.delete()
                        messages.success(request, f'Transação recorrente e {pending_count} parcela(s) pendente(s) deletada(s) com sucesso.')
                else:
                    # Não há parcelas filhas, pode deletar normalmente
                    transaction.delete()
                    messages.success(request, 'Transação recorrente deletada com sucesso.')
                
                return redirect('finance:transactions_list')
            else:
                # GET - mostra confirmação com detalhes
                registered_children_count = transaction.get_registered_children().count()
                pending_children_count = transaction.get_pending_children().count()
                
                context = {
                    'transaction': transaction,
                    'registered_children_count': registered_children_count,
                    'pending_children_count': pending_children_count,
                    'is_recurring_parent_delete': True,
                }
                return render(request, 'finance/transaction_delete.html', context)
    
    # Lógica padrão para transações não recorrentes
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
        form = RecurringCompositeTransactionForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            buy_date = form.cleaned_data['buy_date']
            pay_date = form.cleaned_data.get('pay_date')
            lines = form.cleaned_data['lines']
            is_recurring = form.cleaned_data.get('is_recurring', False)
            
            # Determina status baseado em pay_date
            status = 'registrado' if pay_date else 'pendente'
            
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
                    # Configura recorrência se marcada
                    if is_recurring:
                        parent_transaction.is_recurring = True
                        parent_transaction.recurrence_type = form.cleaned_data.get('recurrence_type')
                        parent_transaction.recurrence_interval = form.cleaned_data.get('recurrence_interval', 1)
                        parent_transaction.recurrence_start_date = form.cleaned_data.get('recurrence_start_date')
                        parent_transaction.recurrence_end_type = form.cleaned_data.get('recurrence_end_type', 'never')
                        parent_transaction.recurrence_end_count = form.cleaned_data.get('recurrence_end_count')
                        parent_transaction.recurrence_sequence = 1
                        # Define due_date como recurrence_start_date se não foi preenchido
                        if not parent_transaction.due_date and parent_transaction.recurrence_start_date:
                            parent_transaction.due_date = parent_transaction.recurrence_start_date
                        # Atualiza descrição com número da parcela
                        base_description = parent_transaction.description or f"Transação Composta #{parent_transaction.id}"
                        if parent_transaction.recurrence_end_type == 'after_count' and parent_transaction.recurrence_end_count:
                            parent_transaction.description = f"{base_description} - 01/{parent_transaction.recurrence_end_count:02d}"
                        else:
                            parent_transaction.description = f"{base_description} - 1"
                        parent_transaction.save()
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
        form = RecurringCompositeTransactionForm()
    
    # Prepara dados para o template (categorias e contas para os selects)
    categories = Category.objects.all().order_by('category', 'subcategory')
    accounts = Account.objects.filter(is_closed=False).order_by('name')
    
    context = {
        'form': form,
        'categories': categories,
        'accounts': accounts,
    }
    
    return render(request, 'finance/composite_transaction_form.html', context)


def composite_transaction_update(request, transaction_id):
    """
    Edita uma transação composta, atualizando todas as transações relacionadas.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    # Identifica a transação pai
    if transaction.parent_type == 'composite':
        # É uma transação filha, busca a pai
        parent_transaction = transaction.parent_transaction
    elif transaction.is_composite_parent():
        # É a transação pai (pode ser composta recorrente com parent_type='recurring')
        parent_transaction = transaction
    else:
        messages.error(request, 'Transação não é uma transação composta válida.')
        return redirect('finance:transactions_list')
    
    # Busca todas as transações filhas (excluindo transferências de crédito que são identificadas separadamente)
    child_transactions = parent_transaction.child_transactions.filter(parent_type='composite').order_by('id')
    
    lines_data_json = '[]'  # Inicializa como JSON vazio
    form = None
    
    if request.method == 'POST':
        form = CompositeTransactionForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            buy_date = form.cleaned_data['buy_date']
            pay_date = form.cleaned_data.get('pay_date')
            lines = form.cleaned_data['lines']
            
            # Determina status baseado em pay_date
            status = 'registrado' if pay_date else 'pendente'
            
            # Deleta todas as transações antigas (pai e filhas)
            # Primeiro deleta as filhas para evitar problemas de CASCADE
            for child in child_transactions:
                child.delete()
            parent_transaction.delete()
            
            # Cria novas transações seguindo a mesma lógica do create
            new_parent_transaction = None
            transaction_count = 0
            
            for i, line in enumerate(lines):
                # Determina operation_type baseado no tipo de linha
                if line['line_type'] == 'transfer':
                    operation_type = 'transfer'
                    transaction_type = 'DB'
                else:
                    operation_type = 'simple'
                    transaction_type = line['transaction_type']
                
                # Cria a transação principal
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
                    new_parent_transaction = transaction
                else:
                    transaction.parent_transaction = new_parent_transaction
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
                        parent_transaction=new_parent_transaction,
                        parent_type='composite'
                    )
                    transaction_count += 1
            
            messages.success(
                request,
                f'Transação composta com {transaction_count} transação(ões) atualizada(s) com sucesso!'
            )
            return redirect('finance:transactions_list')
    
    if form is None or not form.is_valid():
        # GET ou POST com form inválido - preenche com dados existentes
        # Preenche o formulário com os dados existentes
        # Agrupa transações: filhas diretas + transferências de crédito relacionadas
        lines_data = []
        
        # Processa transações filhas diretas (não são transferências de crédito)
        for child in child_transactions:
            # Ignora transações de crédito de transferências (serão processadas junto com a débito)
            if child.operation_type == 'transfer' and child.transaction_type == 'CR':
                continue
            
            # Determina o tipo de linha
            if child.operation_type == 'transfer':
                line_type = 'transfer'
            else:
                line_type = 'normal'
            
            lines_data.append({
                'value': float(child.value),
                'transaction_type': child.transaction_type,
                'line_type': line_type,
                'category': child.category,
                'destination_account': child.destination_account,
                'description': child.description or '',
            })
        
        # Adiciona a transação pai como primeira linha
        if parent_transaction.operation_type == 'transfer':
            line_type = 'transfer'
        else:
            line_type = 'normal'
        
        parent_line = {
            'value': float(parent_transaction.value),
            'transaction_type': parent_transaction.transaction_type,
            'line_type': line_type,
            'category': parent_transaction.category,
            'destination_account': parent_transaction.destination_account,
            'description': parent_transaction.description or '',
        }
        lines_data.insert(0, parent_line)
        
        # Serializa os dados para JSON (converte objetos para IDs)
        lines_data_json = []
        for line in lines_data:
            lines_data_json.append({
                'value': line['value'],
                'transaction_type': line['transaction_type'],
                'line_type': line['line_type'],
                'category_id': line['category'].id if line['category'] else None,
                'destination_account_id': line['destination_account'].id if line['destination_account'] else None,
                'description': line['description'],
            })
        
        initial_data = {
            'account': parent_transaction.account,
            'buy_date': parent_transaction.buy_date,
            'pay_date': parent_transaction.pay_date,
        }
        form = CompositeTransactionForm(initial=initial_data)
        # Converte para JSON string - será usado diretamente no template JavaScript
        lines_data_json = json.dumps(lines_data_json, ensure_ascii=False)
    
    # Prepara dados para o template
    categories = Category.objects.all().order_by('category', 'subcategory')
    accounts = Account.objects.filter(is_closed=False).order_by('name')
    
    context = {
        'form': form,
        'categories': categories,
        'accounts': accounts,
        'transaction': parent_transaction if request.method == 'GET' else None,
        'is_edit': True,
        'existing_lines_json': lines_data_json,
    }
    
    return render(request, 'finance/composite_transaction_form.html', context)


def composite_transaction_delete(request, transaction_id):
    """
    Deleta uma transação composta, removendo todas as transações relacionadas.
    Para transações compostas recorrentes, preserva parcelas registradas e permite promover primeira filha a raiz.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    # Identifica a transação pai
    if transaction.parent_type == 'composite':
        # É uma transação filha, busca a pai
        parent_transaction = transaction.parent_transaction
    elif transaction.is_composite_parent():
        # É a transação pai (pode ser composta recorrente com parent_type='recurring')
        parent_transaction = transaction
    else:
        messages.error(request, 'Transação não é uma transação composta válida.')
        return redirect('finance:transactions_list')
    
    # Verifica se é transação composta recorrente
    is_recurring = parent_transaction.is_recurring
    
    # Lógica especial para transações compostas recorrentes
    if is_recurring:
        if parent_transaction.parent_type == 'recurring':
            # É uma parcela filha recorrente
            if parent_transaction.status == 'registrado' or parent_transaction.pay_date:
                messages.error(request, 'Não é possível deletar uma parcela composta recorrente já registrada.')
                return redirect('finance:transactions_list')
            else:
                # Parcela pendente - pode deletar
                if request.method == 'POST':
                    # Obtém a transação pai da recorrência para reorganizar sequências depois
                    recurring_parent = parent_transaction.get_recurring_parent()
                    
                    # Identifica todas as parcelas subsequentes (com sequence maior)
                    subsequent_installments = parent_transaction.get_subsequent_installments()
                    
                    # Deleta apenas as parcelas subsequentes pendentes
                    pending_subsequent = [s for s in subsequent_installments if not s.pay_date]
                    pending_count = len(pending_subsequent)
                    
                    # Deleta a parcela atual e todas as suas transações (pai + filhas compostas)
                    # Primeiro deleta as filhas compostas
                    composite_children = parent_transaction.child_transactions.filter(parent_type='composite')
                    composite_children.delete()
                    # Deleta transações de crédito de transferências
                    for child in composite_children:
                        if child.operation_type == 'transfer' and child.destination_account:
                            Transaction.objects.filter(
                                account=child.destination_account,
                                destination_account=parent_transaction.account,
                                operation_type='transfer',
                                transaction_type='CR',
                                buy_date=parent_transaction.buy_date
                            ).delete()
                    # Deleta a parcela atual
                    parent_transaction.delete()
                    
                    # Deleta parcelas subsequentes pendentes
                    for subsequent in pending_subsequent:
                        # Deleta todas as transações da composta subsequente
                        composite_children_sub = subsequent.child_transactions.filter(parent_type='composite')
                        composite_children_sub.delete()
                        subsequent.delete()
                    
                    # Reorganiza as sequências das parcelas restantes
                    recurring_parent.reorganize_sequences()
                    
                    messages.success(request, f'Parcela composta deletada. {pending_count} parcela(s) subsequente(s) pendente(s) também foram deletada(s).')
                    return redirect('finance:transactions_list')
        else:
            # É a transação pai recorrente (raiz)
            if request.method == 'POST':
                # Verifica se há parcelas filhas (registradas ou pendentes)
                all_children = parent_transaction.child_transactions.filter(parent_type='recurring')
                total_children_count = all_children.count()
                
                if total_children_count > 0:
                    # Conta parcelas antes da promoção
                    pending_before = [c for c in all_children if not c.pay_date]
                    registered_before = [c for c in all_children if c.pay_date]
                    
                    # Promove a primeira parcela filha a raiz antes de deletar
                    first_child = parent_transaction.promote_first_child_to_root()
                    
                    if first_child:
                        # Deleta apenas a transação pai original
                        # Todas as filhas compostas já foram preservadas na primeira filha
                        parent_transaction.delete()
                        
                        messages.success(
                            request,
                            f'Transação composta pai deletada. {len(registered_before)} parcela(s) registrada(s) e {len(pending_before)} parcela(s) pendente(s) foram preservadas. A primeira parcela filha foi promovida a raiz.'
                        )
                    else:
                        messages.error(request, 'Erro ao promover primeira parcela filha.')
                    return redirect('finance:transactions_list')
                else:
                    # Não há parcelas filhas, pode deletar normalmente
                    composite_children = parent_transaction.child_transactions.filter(parent_type='composite')
                    composite_children.delete()
                    parent_transaction.delete()
                    messages.success(request, 'Transação composta deletada com sucesso!')
                    return redirect('finance:transactions_list')
    
    # Lógica normal para transações compostas não recorrentes
    # Conta quantas transações serão deletadas
    child_count = parent_transaction.child_transactions.filter(parent_type='composite').count()
    total_count = child_count + 1  # +1 para a transação pai
    
    # Calcula o saldo líquido
    net_balance = Decimal('0')
    if parent_transaction.transaction_type == 'CR':
        net_balance += parent_transaction.value
    else:
        net_balance -= parent_transaction.value
    
    for child in parent_transaction.child_transactions.filter(parent_type='composite'):
        if child.transaction_type == 'CR':
            net_balance += child.value
        else:
            net_balance -= child.value
    
    if request.method == 'POST':
        # Deleta a transação pai (que vai cascatear as filhas via CASCADE)
        parent_transaction.delete()
        messages.success(
            request,
            f'Transação composta com {total_count} transação(ões) deletada(s) com sucesso!'
        )
        return redirect('finance:transactions_list')
    
    context = {
        'transaction': parent_transaction,
        'account': parent_transaction.account,
        'buy_date': parent_transaction.buy_date,
        'total_count': total_count,
        'net_balance': net_balance,
        'net_balance_abs': abs(net_balance),  # Valor absoluto para exibição
    }
    
    return render(request, 'finance/composite_transaction_delete.html', context)


def composite_transaction_skip(request, transaction_id):
    """
    Salta uma parcela pendente de transação composta recorrente infinita,
    deletando a parcela atual e gerando automaticamente a próxima.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    # Validações
    if not transaction.is_composite_parent():
        messages.error(request, 'Esta transação não é uma transação composta.')
        return redirect('finance:transactions_list')
    
    if not transaction.is_recurring:
        messages.error(request, 'Esta transação não é recorrente.')
        return redirect('finance:transactions_list')
    
    # Verifica se é recorrência infinita
    parent = transaction.get_recurring_parent()
    if parent.recurrence_end_type != 'never':
        messages.error(request, 'A funcionalidade "Saltar" está disponível apenas para transações com recorrência infinita.')
        return redirect('finance:transactions_list')
    
    # Verifica se está interrompida
    if parent.recurrence_interrupted:
        messages.error(request, 'Esta recorrência está interrompida e não pode gerar novas parcelas.')
        return redirect('finance:transactions_list')
    
    # Verifica se é parcela pendente
    if transaction.pay_date:
        messages.error(request, 'Apenas parcelas pendentes podem ser saltadas.')
        return redirect('finance:transactions_list')
    
    # Verifica se é parcela filha (não raiz)
    if transaction.parent_type != 'recurring':
        messages.error(request, 'A funcionalidade "Saltar" está disponível apenas para parcelas filhas.')
        return redirect('finance:transactions_list')
    
    if request.method == 'POST':
        # Obtém a parcela anterior na recorrência
        current_sequence = transaction.get_current_installment()
        recurring_parent = transaction.get_recurring_parent()
        
        # Busca a parcela anterior (sequence menor)
        previous_installment = None
        if current_sequence > 1:
            # Busca a parcela com sequence = current_sequence - 1
            # Se current_sequence == 2, a anterior é a raiz (sequence 1)
            if current_sequence == 2:
                previous_installment = recurring_parent
            else:
                previous_installment = recurring_parent.child_transactions.filter(
                    parent_type='recurring',
                    recurrence_sequence=current_sequence - 1
                ).first()
        
        # Gera a próxima parcela composta usando a parcela anterior ANTES de deletar
        # Isso garante que a nova parcela seja gerada com a sequência correta
        new_installment_generated = False
        if previous_installment:
            # Verifica se a parcela anterior pode gerar próxima
            if previous_installment.can_generate_next():
                # Verifica se não existe próxima parcela já gerada
                # A próxima parcela seria a que estamos deletando, então não deve existir outra
                existing_next = previous_installment.child_transactions.filter(
                    parent_type='recurring'
                ).exclude(id=transaction.id).first()
                
                if not existing_next:
                    previous_installment.generate_next_composite_installment()
                    new_installment_generated = True
        
        # Deleta a parcela atual e todas as suas filhas compostas
        # Primeiro deleta as filhas compostas
        composite_children = transaction.child_transactions.filter(parent_type='composite')
        
        # Deleta transações de crédito de transferências relacionadas
        for child in composite_children:
            if child.operation_type == 'transfer' and child.destination_account:
                Transaction.objects.filter(
                    account=child.destination_account,
                    destination_account=transaction.account,
                    operation_type='transfer',
                    transaction_type='CR',
                    buy_date=transaction.buy_date
                ).delete()
        
        composite_children.delete()
        
        # Deleta a parcela atual
        transaction.delete()
        
        # Reorganiza as sequências das parcelas restantes
        recurring_parent.reorganize_sequences()
        
        # Mensagem de sucesso
        if new_installment_generated:
            messages.success(request, 'Parcela saltada e próxima parcela gerada automaticamente.')
        elif previous_installment:
            if previous_installment.can_generate_next():
                messages.success(request, 'Parcela saltada. A próxima parcela já existe.')
            else:
                messages.success(request, 'Parcela saltada. Não foi possível gerar próxima parcela (recorrência interrompida ou limite atingido).')
        else:
            messages.success(request, 'Parcela saltada.')
        
        return redirect('finance:transactions_list')
    
    # GET - mostra confirmação
    context = {
        'transaction': transaction,
        'parent': parent,
        'current_sequence': transaction.get_current_installment(),
    }
    
    return render(request, 'finance/composite_transaction_skip.html', context)


def recurring_transaction_undo_payment(request, transaction_id):
    """
    Desfaz o pagamento de uma transação recorrente, removendo pay_date
    e deletando a próxima parcela gerada (se existir).
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    if not transaction.is_recurring:
        messages.error(request, 'Esta transação não é recorrente.')
        return redirect('finance:transactions_list')
    
    if not transaction.pay_date:
        messages.warning(request, 'Esta transação não está paga.')
        return redirect('finance:transactions_list')
    
    # Verifica se é recorrência finita (apenas finitas podem desfazer pagamento)
    parent = transaction.get_recurring_parent()
    if parent.recurrence_end_type != 'after_count':
        messages.error(request, 'A funcionalidade "Desfazer Pagamento" está disponível apenas para transações com recorrência finita.')
        return redirect('finance:transactions_list')
    
    if request.method == 'POST':
        # Busca próxima parcela gerada
        next_installment = transaction.child_transactions.filter(
            parent_type='recurring'
        ).first()
        
        if next_installment:
            next_installment.delete()
            messages.success(request, 'Pagamento desfeito e próxima parcela removida.')
        else:
            messages.success(request, 'Pagamento desfeito.')
        
        # Remove pay_date e atualiza status
        transaction.pay_date = None
        transaction.status = 'pendente'
        transaction.save()
        
        return redirect('finance:transactions_list')
    
    # GET - mostra confirmação
    next_installment = transaction.child_transactions.filter(
        parent_type='recurring'
    ).first()
    
    context = {
        'transaction': transaction,
        'next_installment': next_installment,
    }
    
    return render(request, 'finance/recurring_transaction_undo_payment.html', context)


def recurring_transaction_interrupt(request, transaction_id):
    """
    Interrompe definitivamente uma recorrência infinita, impedindo geração de novas parcelas.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    if not transaction.is_recurring:
        messages.error(request, 'Esta transação não é recorrente.')
        return redirect('finance:transactions_list')
    
    # Obtém a raiz da recorrência (pode ser chamada de qualquer parcela)
    parent = transaction.get_recurring_parent()
    
    # Verifica se é recorrência infinita
    if parent.recurrence_end_type != 'never':
        messages.error(request, 'A funcionalidade "Interromper Recorrência" está disponível apenas para transações com recorrência infinita.')
        return redirect('finance:transactions_list')
    
    # Verifica se já está interrompida
    if parent.recurrence_interrupted:
        messages.warning(request, 'Esta recorrência já está interrompida.')
        return redirect('finance:transactions_list')
    
    if request.method == 'POST':
        # Marca a raiz como interrompida
        parent.recurrence_interrupted = True
        parent.save(update_fields=['recurrence_interrupted'])
        
        # Conta parcelas existentes
        registered_count = parent.get_registered_children().count()
        pending_count = parent.get_pending_children().count()
        
        messages.success(request, f'Recorrência interrompida com sucesso. {registered_count} parcela(s) registrada(s) e {pending_count} parcela(s) pendente(s) foram preservadas. Nenhuma nova parcela será gerada automaticamente.')
        return redirect('finance:transactions_list')
    
    # GET - mostra confirmação
    registered_count = parent.get_registered_children().count()
    pending_count = parent.get_pending_children().count()
    
    context = {
        'transaction': transaction,
        'parent': parent,
        'registered_count': registered_count,
        'pending_count': pending_count,
    }
    
    return render(request, 'finance/recurring_transaction_interrupt.html', context)


def transaction_register(request, transaction_id):
    """
    Registra o pagamento de uma transação, permitindo editar campos e preenchendo pay_date com due_date.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            transaction = form.save(commit=False)
            # Se pay_date foi preenchido no formulário, usa esse valor
            # Se não foi preenchido e due_date existe, usa due_date
            pay_date_from_form = form.cleaned_data.get('pay_date')
            if not pay_date_from_form and transaction.due_date:
                transaction.pay_date = transaction.due_date
            elif pay_date_from_form:
                transaction.pay_date = pay_date_from_form
            
            # Salva todos os campos editáveis (já estão no form.cleaned_data)
            transaction.save()
            
            # Sempre retorna JSON para facilitar o tratamento no frontend
            from django.http import JsonResponse
            return JsonResponse({
                'success': True,
                'message': 'Transação registrada com sucesso!',
                'status': transaction.get_status_display(),
            })
        else:
            # Se o formulário não é válido, retorna erros em JSON
            from django.http import JsonResponse
            from django.forms.utils import ErrorDict
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            
            return JsonResponse({
                'success': False,
                'message': 'Erro de validação',
                'errors': errors
            }, status=400)
    else:
        # GET - pré-preenche pay_date com due_date se não estiver preenchido
        initial_data = {}
        if transaction.due_date and not transaction.pay_date:
            initial_data['pay_date'] = transaction.due_date
        
        form = TransactionForm(instance=transaction, initial=initial_data)
        # Esconde campos que não devem ser editados no modal de registro
        if 'operation_type' in form.fields:
            form.fields['operation_type'].widget = forms.HiddenInput()
        if 'buy_date' in form.fields:
            form.fields['buy_date'].widget = forms.HiddenInput()
        if 'due_date' in form.fields:
            form.fields['due_date'].widget = forms.HiddenInput()
    
    context = {
        'form': form,
        'transaction': transaction,
    }
    
    return render(request, 'finance/transaction_register_modal.html', context)


def composite_transaction_register(request, transaction_id):
    """
    Registra o pagamento de uma transação composta, permitindo editar account, beneficiary, pay_date e linhas.
    Aplica pay_date a todas as transações da composta (pai + filhas).
    """
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    # Verifica se é transação composta pai
    if not transaction.is_composite_parent():
        messages.error(request, 'Esta não é uma transação composta válida.')
        return redirect('finance:transactions_list')
    
    # Busca todas as transações filhas
    child_transactions = transaction.child_transactions.filter(parent_type='composite').order_by('id')
    
    if request.method == 'POST':
        # Processa dados do formulário
        account_id = request.POST.get('account')
        beneficiary_id = request.POST.get('beneficiary')
        pay_date_str = request.POST.get('pay_date')
        
        # Valida conta
        try:
            account = Account.objects.get(id=account_id)
        except (Account.DoesNotExist, ValueError, TypeError):
            from django.http import JsonResponse
            return JsonResponse({
                'success': False,
                'message': 'Conta inválida.',
                'errors': {'account': ['Conta é obrigatória.']}
            }, status=400)
        
        # Processa beneficiário (opcional)
        beneficiary = None
        if beneficiary_id:
            try:
                beneficiary = Beneficiary.objects.get(id=beneficiary_id)
            except (Beneficiary.DoesNotExist, ValueError, TypeError):
                pass
        
        # Processa pay_date
        pay_date = None
        if pay_date_str:
            try:
                from datetime import datetime
                pay_date = datetime.strptime(pay_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass
        
        # Se pay_date não foi preenchido e due_date existe, usa due_date
        if not pay_date and transaction.due_date:
            pay_date = transaction.due_date
        
        # Determina status baseado em pay_date
        status = 'registrado' if pay_date else 'pendente'
        
        # Processa linhas do formulário
        lines = []
        line_count = 0
        
        # Conta quantas linhas foram enviadas
        while True:
            value_key = f'line_{line_count}_value'
            if value_key not in request.POST:
                break
            line_count += 1
        
        if line_count == 0:
            from django.http import JsonResponse
            return JsonResponse({
                'success': False,
                'message': 'Adicione pelo menos uma linha de transação.',
                'errors': {}
            }, status=400)
        
        # Valida e processa cada linha
        line_errors = []
        for i in range(line_count):
            value = request.POST.get(f'line_{i}_value')
            transaction_type = request.POST.get(f'line_{i}_transaction_type')
            is_transfer = request.POST.get(f'line_{i}_is_transfer') == 'on'
            line_type = 'transfer' if is_transfer else 'normal'
            category_id = request.POST.get(f'line_{i}_category')
            destination_account_id = request.POST.get(f'line_{i}_destination_account')
            description = request.POST.get(f'line_{i}_description', '')
            
            # Valida valor
            try:
                value = float(value) if value else None
                if value is None or value <= 0:
                    line_errors.append(f'Linha {i+1}: Valor deve ser maior que zero.')
                    continue
            except (ValueError, TypeError):
                line_errors.append(f'Linha {i+1}: Valor inválido.')
                continue
            
            # Para transferências, sempre força DB
            if line_type == 'transfer':
                transaction_type = 'DB'
            
            # Valida tipo de transação
            if transaction_type not in ['CR', 'DB']:
                line_errors.append(f'Linha {i+1}: Tipo de transação inválido.')
                continue
            
            # Validação específica por tipo de linha
            if line_type == 'transfer':
                if not destination_account_id:
                    line_errors.append(f'Linha {i+1}: Conta de destino é obrigatória para transferências.')
                    continue
                try:
                    destination_account = Account.objects.get(id=destination_account_id)
                    if destination_account == account:
                        line_errors.append(f'Linha {i+1}: A conta de destino deve ser diferente da conta principal.')
                        continue
                except Account.DoesNotExist:
                    line_errors.append(f'Linha {i+1}: Conta de destino inválida.')
                    continue
                category = None
            else:
                if not category_id:
                    line_errors.append(f'Linha {i+1}: Categoria é obrigatória para transações normais.')
                    continue
                try:
                    category = Category.objects.get(id=category_id)
                except Category.DoesNotExist:
                    line_errors.append(f'Linha {i+1}: Categoria inválida.')
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
        
        if line_errors:
            from django.http import JsonResponse
            return JsonResponse({
                'success': False,
                'message': 'Erros de validação nas linhas.',
                'errors': {'lines': line_errors}
            }, status=400)
        
        # Deleta todas as transações antigas (pai e filhas)
        # Primeiro deleta as filhas para evitar problemas de CASCADE
        for child in child_transactions:
            # Deleta também transações de crédito de transferências
            if child.operation_type == 'transfer' and child.destination_account:
                Transaction.objects.filter(
                    account=child.destination_account,
                    destination_account=transaction.account,
                    operation_type='transfer',
                    transaction_type='CR',
                    buy_date=transaction.buy_date
                ).delete()
            child.delete()
        
        # Cria novas transações seguindo a mesma lógica do create
        new_parent_transaction = None
        transaction_count = 0
        
        for i, line in enumerate(lines):
            # Determina operation_type baseado no tipo de linha
            if line['line_type'] == 'transfer':
                operation_type = 'transfer'
                line_transaction_type = 'DB'
            else:
                operation_type = 'simple'
                line_transaction_type = line['transaction_type']
            
            # Prepara campos de recorrência ANTES de criar a transação
            recurrence_fields = {}
            if transaction.is_recurring:
                recurrence_fields = {
                    'is_recurring': True,
                    'recurrence_type': transaction.recurrence_type,
                    'recurrence_interval': transaction.recurrence_interval,
                    'recurrence_start_date': transaction.recurrence_start_date,
                    'recurrence_end_type': transaction.recurrence_end_type,
                    'recurrence_end_count': transaction.recurrence_end_count,
                    'recurrence_sequence': transaction.recurrence_sequence,
                    'recurrence_interrupted': transaction.recurrence_interrupted,
                }
                # Preserva parent_type e parent_transaction da recorrência se for parcela filha
                if transaction.parent_type == 'recurring' and transaction.parent_transaction:
                    recurrence_fields['parent_type'] = 'recurring'
                    recurrence_fields['parent_transaction'] = transaction.parent_transaction
            
            # Cria a transação principal com todos os campos de recorrência já definidos
            # Para a primeira transação (pai), cria SEM pay_date primeiro para evitar geração prematura
            # O pay_date será atualizado depois que todas as filhas compostas forem criadas
            create_pay_date = None if i == 0 else pay_date  # Primeira linha (pai) sem pay_date inicialmente
            create_status = 'pendente' if i == 0 else status  # Primeira linha (pai) pendente inicialmente
            
            new_transaction = Transaction.objects.create(
                account=account,
                destination_account=line['destination_account'],
                transaction_type=line_transaction_type,
                operation_type=operation_type,
                value=Decimal(str(line['value'])),
                category=line['category'],
                description=line['description'],
                buy_date=transaction.buy_date,
                due_date=transaction.due_date,
                pay_date=create_pay_date,
                status=create_status,
                beneficiary=beneficiary if i == 0 else None,  # Beneficiário apenas na primeira linha (pai)
                **recurrence_fields  # Inclui todos os campos de recorrência
            )
            
            # Primeira transação é a pai, demais são filhas
            if transaction_count == 0:
                new_parent_transaction = new_transaction
            else:
                new_transaction.parent_transaction = new_parent_transaction
                new_transaction.parent_type = 'composite'
                new_transaction.save()
            
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
                    buy_date=transaction.buy_date,
                    due_date=transaction.due_date,
                    pay_date=pay_date,
                    status=status,
                    parent_transaction=new_parent_transaction,
                    parent_type='composite'
                )
                transaction_count += 1
        
        # Deleta a transação pai antiga ANTES de atualizar pay_date
        # Isso evita conflitos na estrutura de recorrência
        old_transaction_id = transaction.id
        transaction.delete()
        
        # Agora atualiza pay_date e status da transação pai usando update() para evitar chamar save()
        # Isso evita que o método save() tente gerar próxima parcela antes de todas as filhas estarem prontas
        if pay_date:
            Transaction.objects.filter(id=new_parent_transaction.id).update(
                pay_date=pay_date,
                status='registrado'
            )
            # Recarrega a transação do banco para ter os valores atualizados
            new_parent_transaction.refresh_from_db()
        
        # Se a transação é recorrente e tem pay_date, verifica se precisa gerar próxima parcela
        # Isso só acontece após todas as filhas compostas serem criadas e a transação antiga deletada
        if new_parent_transaction.is_recurring and pay_date:
            # Verifica se já existe próxima parcela gerada
            existing_next = new_parent_transaction.child_transactions.filter(
                parent_type='recurring'
            ).first()
            
            # Gera próxima parcela se não existe e pode gerar
            if not existing_next and new_parent_transaction.can_generate_next():
                if new_parent_transaction.is_composite_recurring():
                    new_parent_transaction.generate_next_composite_installment()
                else:
                    new_parent_transaction.generate_next_installment()
        
        # Sempre retorna JSON para facilitar o tratamento no frontend
        from django.http import JsonResponse
        return JsonResponse({
            'success': True,
            'message': 'Transação composta registrada com sucesso!',
            'status': new_parent_transaction.get_status_display(),
        })
    else:
        # GET - prepara dados para exibição
        # Preenche o formulário com os dados existentes
        lines_data = []
        
        # Processa transações filhas diretas (não são transferências de crédito)
        for child in child_transactions:
            # Ignora transações de crédito de transferências (serão processadas junto com a débito)
            if child.operation_type == 'transfer' and child.transaction_type == 'CR':
                continue
            
            # Determina o tipo de linha
            if child.operation_type == 'transfer':
                line_type = 'transfer'
            else:
                line_type = 'normal'
            
            lines_data.append({
                'value': float(child.value),
                'transaction_type': child.transaction_type,
                'line_type': line_type,
                'category': child.category,
                'destination_account': child.destination_account,
                'description': child.description or '',
            })
        
        # Adiciona a transação pai como primeira linha
        if transaction.operation_type == 'transfer':
            line_type = 'transfer'
        else:
            line_type = 'normal'
        
        parent_line = {
            'value': float(transaction.value),
            'transaction_type': transaction.transaction_type,
            'line_type': line_type,
            'category': transaction.category,
            'destination_account': transaction.destination_account,
            'description': transaction.description or '',
        }
        lines_data.insert(0, parent_line)
        
        # Serializa os dados para JSON (converte objetos para IDs)
        lines_data_json = []
        for line in lines_data:
            lines_data_json.append({
                'value': line['value'],
                'transaction_type': line['transaction_type'],
                'line_type': line['line_type'],
                'category_id': line['category'].id if line['category'] else None,
                'destination_account_id': line['destination_account'].id if line['destination_account'] else None,
                'description': line['description'],
            })
        
        # Pré-preenche pay_date com due_date se não estiver preenchido
        initial_pay_date = None
        if transaction.due_date and not transaction.pay_date:
            initial_pay_date = transaction.due_date
        elif transaction.pay_date:
            initial_pay_date = transaction.pay_date
        
        # Prepara dados para o template
        categories = Category.objects.all().order_by('category', 'subcategory')
        accounts = Account.objects.filter(is_closed=False).order_by('name')
        beneficiaries = Beneficiary.objects.all().order_by('full_name')
        
        context = {
            'transaction': transaction,
            'account': transaction.account,
            'beneficiary': transaction.beneficiary,
            'pay_date': initial_pay_date,
            'lines_data_json': json.dumps(lines_data_json, ensure_ascii=False),
            'categories': categories,
            'accounts': accounts,
            'beneficiaries': beneficiaries,
        }
        
        return render(request, 'finance/composite_transaction_register_modal.html', context)

