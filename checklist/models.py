from django.db import models
from django.utils.translation import gettext_lazy as _

from management.models import Company, Estate

# Create your models here


class Source(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, verbose_name="Construtora"
    )
    source = models.TextField(unique=True, verbose_name="Origem")
    description = models.TextField(default="", verbose_name="Descrição")


class CheckList(models.Model):
    class StatusCheck(models.TextChoices):
        PENDING = "PENDING", _("Pendente")
        UP_TO_DATE = "UP_TO_DATE", _("Atualizado")
        OUTDATED = "OUTDATED", _("Desatualizado")
        UNAVAILABLE = "UNAVAILABLE", _("Indisponível")

    estate = models.ForeignKey(
        Estate, on_delete=models.CASCADE, verbose_name="Residencial"
    )
    sources = models.ManyToManyField(Source, verbose_name="Origens")
    date = models.DateField(auto_now=True, verbose_name="Data")
    status = models.CharField(
        max_length=32,
        choices=StatusCheck,
        default=StatusCheck.PENDING,
        verbose_name="Situação",
    )
