import json
from pathlib import Path

from django.db import migrations

MUNICIPIOS = Path(__file__).resolve().parent.parent / "data" / "municipios.json"


def load_cities(apps, schema_editor):
    """Carrega os municípios do IBGE (lista em management/data/municipios.json)."""
    City = apps.get_model("management", "City")
    rows = json.loads(MUNICIPIOS.read_text(encoding="utf-8"))
    City.objects.bulk_create(
        City(ibge_code=code, name=name, state=state) for code, name, state in rows
    )


def unload_cities(apps, schema_editor):
    apps.get_model("management", "City").objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ("management", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(load_cities, unload_cities),
    ]
