from django.db import migrations


def delete_facilities(apps, schema_editor):
    """Estruturas de teste no formato antigo; nenhuma estava em uso por empreendimentos."""
    apps.get_model("management", "Facility").objects.all().delete()


class Migration(migrations.Migration):
    """Separada da 0009: no PostgreSQL não dá para apagar linhas e alterar a
    tabela na mesma transação (restrições de chave estrangeira pendentes)."""

    dependencies = [
        ("management", "0007_estate_facility_floor_integer"),
    ]

    operations = [
        migrations.RunPython(delete_facilities, migrations.RunPython.noop),
    ]
