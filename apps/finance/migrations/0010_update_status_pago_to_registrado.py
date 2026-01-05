# Generated migration to update status values

from django.db import migrations


def update_status_pago_to_registrado(apps, schema_editor):
    Transaction = apps.get_model('finance', 'Transaction')
    Transaction.objects.filter(status='pago').update(status='registrado')


def reverse_update_status(apps, schema_editor):
    Transaction = apps.get_model('finance', 'Transaction')
    Transaction.objects.filter(status='registrado').update(status='pago')


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0009_alter_transaction_status'),
    ]

    operations = [
        migrations.RunPython(update_status_pago_to_registrado, reverse_update_status),
    ]

