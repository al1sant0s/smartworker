import json
from pathlib import Path

from django.db import migrations, models

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
        ("management", "0004_tracking_event_order_by_pk"),
    ]

    operations = [
        migrations.CreateModel(
            name="City",
            fields=[
                (
                    "ibge_code",
                    models.PositiveIntegerField(
                        primary_key=True, serialize=False, verbose_name="Código IBGE"
                    ),
                ),
                ("name", models.CharField(max_length=64, verbose_name="Nome")),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("AC", "Acre"),
                            ("AL", "Alagoas"),
                            ("AP", "Amapá"),
                            ("AM", "Amazonas"),
                            ("BA", "Bahia"),
                            ("CE", "Ceará"),
                            ("DF", "Distrito Federal"),
                            ("ES", "Espírito Santo"),
                            ("GO", "Goiás"),
                            ("MA", "Maranhão"),
                            ("MT", "Mato Grosso"),
                            ("MS", "Mato Grosso do Sul"),
                            ("MG", "Minas Gerais"),
                            ("PA", "Pará"),
                            ("PB", "Paraíba"),
                            ("PR", "Paraná"),
                            ("PE", "Pernambuco"),
                            ("PI", "Piauí"),
                            ("RJ", "Rio de Janeiro"),
                            ("RN", "Rio Grande do Norte"),
                            ("RS", "Rio Grande do Sul"),
                            ("RO", "Rondônia"),
                            ("RR", "Roraima"),
                            ("SC", "Santa Catarina"),
                            ("SP", "São Paulo"),
                            ("SE", "Sergipe"),
                            ("TO", "Tocantins"),
                        ],
                        max_length=2,
                        verbose_name="UF",
                    ),
                ),
            ],
            options={
                "verbose_name": "Município",
                "verbose_name_plural": "Municípios",
                "ordering": ["name"],
                "indexes": [
                    models.Index(fields=["state", "name"], name="management__state_66b1c6_idx")
                ],
            },
        ),
        migrations.RunPython(load_cities, unload_cities),
    ]
