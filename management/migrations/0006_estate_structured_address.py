from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Troca o endereço em texto livre por campos separados e as coordenadas.

    Não havia empreendimentos cadastrados; os defaults abaixo só existem para a
    migração (preserve_default=False) e não ficam no modelo.
    """

    dependencies = [
        ("management", "0005_city"),
    ]

    operations = [
        migrations.RemoveField(model_name="estate", name="address"),
        migrations.RemoveField(model_name="estate", name="sea_distance"),
        migrations.AddField(
            model_name="estate",
            name="cep",
            field=models.CharField(
                default="",
                help_text="Com ou sem traço (ex: 88015-200)",
                max_length=9,
                verbose_name="CEP",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="estate",
            name="street",
            field=models.CharField(default="", max_length=128, verbose_name="Logradouro"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="estate",
            name="number",
            field=models.CharField(
                default="",
                help_text="Use “s/n” se não houver",
                max_length=16,
                verbose_name="Número",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="estate",
            name="complement",
            field=models.CharField(
                blank=True, default="", max_length=64, verbose_name="Complemento"
            ),
        ),
        migrations.AddField(
            model_name="estate",
            name="district",
            field=models.CharField(default="", max_length=64, verbose_name="Bairro"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="estate",
            name="city",
            field=models.ForeignKey(
                default=4205407,  # Florianópolis; só para a migração
                on_delete=django.db.models.deletion.PROTECT,
                related_name="estates",
                to="management.city",
                verbose_name="Município",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="estate",
            name="latitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(Decimal("-90")),
                    django.core.validators.MaxValueValidator(Decimal("90")),
                ],
                verbose_name="Latitude",
            ),
        ),
        migrations.AddField(
            model_name="estate",
            name="longitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(Decimal("-180")),
                    django.core.validators.MaxValueValidator(Decimal("180")),
                ],
                verbose_name="Longitude",
            ),
        ),
    ]
