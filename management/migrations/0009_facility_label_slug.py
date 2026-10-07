from django.db import migrations, models


class Migration(migrations.Migration):
    """Troca o nome em snake_case por label padronizado + slug ASCII único."""

    dependencies = [
        ("management", "0008_delete_facilities"),
    ]

    operations = [
        migrations.RemoveField(model_name="facility", name="name"),
        migrations.AddField(
            model_name="facility",
            name="label",
            field=models.CharField(default="", max_length=64, verbose_name="Nome"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="facility",
            name="slug",
            field=models.CharField(
                default="",
                editable=False,
                max_length=64,
                unique=True,
                verbose_name="Identificador",
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="facility",
            options={
                "ordering": ["label"],
                "verbose_name": "Estrutura / Comodidade",
                "verbose_name_plural": "Estruturas / Comodidades",
            },
        ),
    ]
