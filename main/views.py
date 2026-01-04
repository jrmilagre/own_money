from django.shortcuts import render


def home(request):
    """
    Página inicial com links para as aplicações do sistema.
    """
    # Lista de aplicações disponíveis
    # Futuramente, isso pode ser dinâmico ou vir de configuração
    applications = [
        {
            'name': 'Finance',
            'display_name': 'Finanças',
            'url': 'finance:finance_home',
            'description': 'Gerencie suas contas, transações e extratos financeiros.',
        },
        # Adicione outras aplicações aqui no futuro
    ]
    
    context = {
        'applications': applications,
    }
    
    return render(request, 'main/home.html', context)

